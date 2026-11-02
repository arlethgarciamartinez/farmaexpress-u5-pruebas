from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .base import RaizDeAgregado
from .eventos import SustitucionAceptada, VentaCobrada, VentaRechazada, VentaRetenidaPorAutorizacion
from .excepciones import (
    AutorizacionRequerida,
    RecetaIncompleta,
    RecetaRequerida,
    RecetaVencida,
    SustitutoNoEquivalente,
    VentaNoModificable,
    VentaSinProductos,
)
from .producto import Producto
from .valores import (
    Autorizacion,
    Dinero,
    LimitesDeVentaControlada,
    NumeroDeLote,
    Receta,
    Sku,
    Ticket,
    TipoDeAutorizacion,
)


class EstadoDeVenta(Enum):
    EN_CAPTURA = "En captura"
    PENDIENTE_DE_AUTORIZACION = "Pendiente de autorización"
    COBRADA = "Cobrada"
    RECHAZADA = "Rechazada"


@dataclass
class LineaDeVenta:
    """Entidad interna del Aggregate Venta (identidad local: número de línea)."""

    numero: int
    sku: Sku
    nombre: str
    numero_lote: NumeroDeLote
    cantidad: int
    precio_unitario: Dinero
    es_controlado: bool
    sustituye_a: Sku | None = None

    def subtotal(self) -> Dinero:
        return self.precio_unitario.por(self.cantidad)


class Venta(RaizDeAgregado):
    """Aggregate raíz Venta (venta en mostrador).

    Invariantes que protege:
      I1. Ninguna venta de medicamento controlado se cobra sin Receta completa
          y vigente (BN-01, restricción BRD, US-02/US-03).
      I2. Una venta de controlados que excede el límite no se cobra sin
          Autorizacion del Responsable de farmacia (US-04, BN-10).
      I3. La sustitución de un controlado exige Autorizacion (US-06).
      I4. Una venta COBRADA o RECHAZADA ya no se modifica.
    """

    def __init__(self, id: int, sucursal_id: str, cajero: str, fecha: date):
        super().__init__()
        self.id = id
        self.sucursal_id = sucursal_id
        self.cajero = cajero
        self.fecha = fecha
        self.estado = EstadoDeVenta.EN_CAPTURA
        self.lineas: list[LineaDeVenta] = []
        self.receta: Receta | None = None
        self.autorizaciones: list[Autorizacion] = []
        self.ticket: Ticket | None = None
        self.motivo_de_rechazo: str | None = None

    # ---- captura ---------------------------------------------------------
    def _asegurar_modificable(self) -> None:
        if self.estado in (EstadoDeVenta.COBRADA, EstadoDeVenta.RECHAZADA):
            raise VentaNoModificable(
                f"La venta {self.id} está {self.estado.value.lower()} y no admite cambios")

    def agregar_producto(self, producto: Producto, numero_lote: NumeroDeLote,
                         cantidad: int, sustituye_a: Sku | None = None) -> None:
        self._asegurar_modificable()
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva")
        self.lineas.append(LineaDeVenta(
            numero=len(self.lineas) + 1, sku=producto.sku, nombre=producto.nombre,
            numero_lote=numero_lote, cantidad=cantidad,
            precio_unitario=producto.precio, es_controlado=producto.es_controlado,
            sustituye_a=sustituye_a))

    def agregar_sustituto(self, solicitado: Producto, sustituto: Producto,
                          numero_lote: NumeroDeLote, cantidad: int,
                          autorizacion: Autorizacion | None = None) -> None:
        """US-05 / US-06: el sustituto debe ser equivalente; si el solicitado
        es controlado, requiere Autorizacion explícita del Responsable."""
        self._asegurar_modificable()
        if not solicitado.admite_como_sustituto(sustituto.sku):
            raise SustitutoNoEquivalente(
                f"{sustituto.nombre} no es equivalente de {solicitado.nombre}")
        if solicitado.es_controlado:
            if (autorizacion is None or
                    autorizacion.tipo is not TipoDeAutorizacion.SUSTITUCION_DE_CONTROLADO):
                raise AutorizacionRequerida(
                    "La sustitución de un medicamento controlado requiere "
                    "autorización del Responsable de farmacia")
            self.autorizaciones.append(autorizacion)
        self.agregar_producto(sustituto, numero_lote, cantidad, sustituye_a=solicitado.sku)
        self.registrar_evento(SustitucionAceptada(self.id, solicitado.sku, sustituto.sku))

    def registrar_receta(self, receta: Receta) -> None:
        self._asegurar_modificable()
        self.receta = receta

    def otorgar_autorizacion(self, autorizacion: Autorizacion) -> None:
        self._asegurar_modificable()
        self.autorizaciones.append(autorizacion)
        if (autorizacion.tipo is TipoDeAutorizacion.VENTA_CONTROLADA_EXCEDE_LIMITE
                and self.estado is EstadoDeVenta.PENDIENTE_DE_AUTORIZACION):
            self.estado = EstadoDeVenta.EN_CAPTURA

    # ---- consultas internas ---------------------------------------------
    def tiene_controlados(self) -> bool:
        return any(l.es_controlado for l in self.lineas)

    def piezas_controladas(self) -> int:
        return sum(l.cantidad for l in self.lineas if l.es_controlado)

    def monto_controlado(self) -> Dinero:
        total = Dinero.mxn(0)
        for l in self.lineas:
            if l.es_controlado:
                total = total + l.subtotal()
        return total

    def total(self) -> Dinero:
        total = Dinero.mxn(0)
        for l in self.lineas:
            total = total + l.subtotal()
        return total

    def _tiene_autorizacion(self, tipo: TipoDeAutorizacion) -> bool:
        return any(a.tipo is tipo for a in self.autorizaciones)

    # ---- cobro -----------------------------------------------------------
    def confirmar_cobro(self, hoy: date, limites: LimitesDeVentaControlada) -> Ticket | None:
        """Valida las invariantes y cobra. Devuelve el Ticket, o None si la
        venta quedó retenida esperando autorización (US-04). Lanza un
        ErrorDeDominio si se viola una regla (receta, venta vacía...)."""
        self._asegurar_modificable()
        if not self.lineas:
            raise VentaSinProductos("La venta no tiene productos")

        if self.tiene_controlados():                      # I1
            if self.receta is None:
                raise RecetaRequerida("El medicamento controlado requiere receta médica")
            faltantes = self.receta.faltantes()
            if faltantes:
                raise RecetaIncompleta("Receta incompleta, falta: " + ", ".join(faltantes))
            if not self.receta.esta_vigente(hoy):
                raise RecetaVencida(
                    f"Receta vencida: supera {Receta.VIGENCIA_EN_DIAS} días de vigencia")

            if (limites.excede(self.piezas_controladas(), self.monto_controlado())  # I2
                    and not self._tiene_autorizacion(
                        TipoDeAutorizacion.VENTA_CONTROLADA_EXCEDE_LIMITE)):
                self.estado = EstadoDeVenta.PENDIENTE_DE_AUTORIZACION
                self.registrar_evento(VentaRetenidaPorAutorizacion(
                    self.id, "Excede límite de piezas o monto de controlados"))
                return None

        self.estado = EstadoDeVenta.COBRADA
        self.ticket = Ticket(folio=f"T-{self.sucursal_id}-{self.id:06d}",
                             total=self.total(), fecha=hoy)
        self.registrar_evento(VentaCobrada(
            self.id, self.sucursal_id, str(self.ticket.total.monto), hoy))
        return self.ticket

    def rechazar(self, motivo: str, hoy: date) -> None:
        """Fin por excepción del BPMN (venta rechazada / no completada)."""
        self._asegurar_modificable()
        self.estado = EstadoDeVenta.RECHAZADA
        self.motivo_de_rechazo = motivo
        self.registrar_evento(VentaRechazada(self.id, motivo, hoy))
