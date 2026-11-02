"""Service Layer: Application Services. Cada método = un caso de uso completo.
COORDINAN (cargan Aggregates, invocan comportamiento del dominio, piden
persistencia, definen la transacción). NO contienen reglas del negocio."""
from __future__ import annotations

from typing import Callable

from ..dominio.eventos import ExistenciaBajoMinimo, LoteRetirado
from ..dominio.excepciones import ErrorDeDominio, ExistenciaInsuficiente, LoteCaducado
from ..dominio.orden_de_compra import AlertaDeResurtido, OrdenDeCompra
from ..dominio.seleccion_de_lote import SeleccionDeLote
from ..dominio.valores import (
    Autorizacion,
    LimitesDeVentaControlada,
    NumeroDeLote,
    Receta,
    Rol,
    TipoDeAutorizacion,
)
from ..dominio.venta import Venta
from .comandos import (
    AceptarSustituto,
    AgregarProductoALaVenta,
    ConfirmarCobro,
    GenerarOrdenDeCompra,
    IniciarVenta,
    OtorgarAutorizacionDeVenta,
    RegistrarRecetaEnVenta,
    RegistrarRetiroDeLote,
)
from .puertos import NotificadorDeAlmacen, Reloj, UnidadDeTrabajo
from .resultados import Resultado

FabricaDeUoW = Callable[[], UnidadDeTrabajo]


class VentaMostradorService:
    """Proceso principal del BPMN: venta en mostrador (CU-01, CU-02, CU-03)."""

    def __init__(self, uow: FabricaDeUoW, seleccion: SeleccionDeLote,
                 limites: LimitesDeVentaControlada, reloj: Reloj):
        self._uow, self._seleccion, self._limites, self._reloj = uow, seleccion, limites, reloj

    def iniciar_venta(self, cmd: IniciarVenta) -> Resultado:
        with self._uow() as uow:
            venta = Venta(uow.ventas.siguiente_id(), cmd.sucursal_id, cmd.cajero,
                          self._reloj.hoy())
            uow.ventas.agregar(venta)
            uow.confirmar()
            return Resultado.ok(venta_id=venta.id)

    def agregar_producto(self, cmd: AgregarProductoALaVenta) -> Resultado:
        hoy = self._reloj.hoy()
        with self._uow() as uow:
            venta = uow.ventas.obtener(cmd.venta_id)
            producto = uow.productos.obtener(cmd.sku)
            inventario = uow.inventarios.obtener(venta.sucursal_id, cmd.sku)
            lotes = {l.numero: l for l in uow.lotes.de_producto(cmd.sku)}
            try:
                numero = self._seleccion.seleccionar(inventario, lotes, cmd.cantidad, hoy)
            except LoteCaducado as e:                       # US-07: marcar no disponible
                lotes[e.numero_lote].marcar_caducado(hoy)
                uow.confirmar()
                return Resultado.rechazo(e)
            except ExistenciaInsuficiente as e:             # BPMN: ¿Hay existencia? = No
                return Resultado.rechazo(
                    e, sustitutos_sugeridos=[s.valor for s in producto.sustitutos])
            except ErrorDeDominio as e:
                return Resultado.rechazo(e)
            venta.agregar_producto(producto, numero, cmd.cantidad)
            uow.confirmar()
            return Resultado.ok(requiere_receta=producto.es_controlado,
                                numero_lote=numero.valor)

    def aceptar_sustituto(self, cmd: AceptarSustituto) -> Resultado:
        hoy = self._reloj.hoy()
        with self._uow() as uow:
            try:
                venta = uow.ventas.obtener(cmd.venta_id)
                solicitado = uow.productos.obtener(cmd.sku_solicitado)
                sustituto = uow.productos.obtener(cmd.sku_sustituto)
                inventario = uow.inventarios.obtener(venta.sucursal_id, cmd.sku_sustituto)
                lotes = {l.numero: l for l in uow.lotes.de_producto(cmd.sku_sustituto)}
                numero = self._seleccion.seleccionar(inventario, lotes, cmd.cantidad, hoy)
                autorizacion = None
                if cmd.autorizado_por and cmd.rol_autorizador:
                    autorizacion = Autorizacion(
                        TipoDeAutorizacion.SUSTITUCION_DE_CONTROLADO,
                        cmd.autorizado_por, cmd.rol_autorizador, hoy)
                venta.agregar_sustituto(solicitado, sustituto, numero, cmd.cantidad, autorizacion)
            except ErrorDeDominio as e:
                return Resultado.rechazo(e)
            uow.confirmar()
            return Resultado.ok(numero_lote=numero.valor)

    def registrar_receta(self, cmd: RegistrarRecetaEnVenta) -> Resultado:
        with self._uow() as uow:
            venta = uow.ventas.obtener(cmd.venta_id)
            try:
                venta.registrar_receta(Receta(cmd.paciente, cmd.medico,
                                              cmd.cedula_profesional, cmd.fecha_emision))
            except ErrorDeDominio as e:
                return Resultado.rechazo(e)
            uow.confirmar()
            return Resultado.ok()

    def confirmar_cobro(self, cmd: ConfirmarCobro) -> Resultado:
        """Transacción única: Venta + InventarioDeProducto (ADR-003)."""
        hoy = self._reloj.hoy()
        with self._uow() as uow:
            venta = uow.ventas.obtener(cmd.venta_id)
            try:
                for linea in venta.lineas:      # BPMN: verificar lote y caducidad antes de cobrar
                    uow.lotes.obtener(linea.sku, linea.numero_lote).verificar_vendible(hoy)
                ticket = venta.confirmar_cobro(hoy, self._limites)
            except ErrorDeDominio as e:         # fin por excepción: se conserva el rechazo
                venta.rechazar(e.mensaje, hoy)
                uow.confirmar()
                return Resultado.rechazo(e)
            if ticket is None:                  # retenida: espera autorización (US-04)
                uow.confirmar()
                return Resultado(False, "AUTORIZACION_REQUERIDA",
                                 "Venta retenida: requiere autorización del Responsable de farmacia")
            try:
                for linea in venta.lineas:
                    inv = uow.inventarios.obtener(venta.sucursal_id, linea.sku)
                    inv.descontar(linea.numero_lote, linea.cantidad, hoy)
            except ErrorDeDominio as e:
                return Resultado.rechazo(e)     # sin confirmar => rollback de todo
            uow.confirmar()                     # commit y luego se publican los eventos
            return Resultado.ok("VENTA_COBRADA", folio=ticket.folio,
                                total=str(ticket.total.monto))


class AutorizacionDeVentaService:
    """Otorgar autorizaciones sobre una venta retenida (CU-02, US-04)."""

    def __init__(self, uow: FabricaDeUoW, reloj: Reloj):
        self._uow, self._reloj = uow, reloj

    def otorgar(self, cmd: OtorgarAutorizacionDeVenta) -> Resultado:
        with self._uow() as uow:
            venta = uow.ventas.obtener(cmd.venta_id)
            try:
                autorizacion = Autorizacion(cmd.tipo, cmd.autorizado_por, cmd.rol,
                                            self._reloj.hoy(), cmd.motivo)
                venta.otorgar_autorizacion(autorizacion)
            except ErrorDeDominio as e:
                return Resultado.rechazo(e)
            uow.confirmar()
            return Resultado.ok(estado=venta.estado.value)


class RetiroDeLoteService:
    """CU-04 (US-08)."""

    def __init__(self, uow: FabricaDeUoW, reloj: Reloj, almacen: NotificadorDeAlmacen):
        self._uow, self._reloj, self._almacen = uow, reloj, almacen

    def registrar_retiro(self, cmd: RegistrarRetiroDeLote) -> Resultado:
        hoy = self._reloj.hoy()
        with self._uow() as uow:
            try:
                autorizacion = Autorizacion(TipoDeAutorizacion.RETIRO_DE_LOTE,
                                            cmd.registrado_por, cmd.rol, hoy, cmd.motivo)
                lote = uow.lotes.obtener(cmd.sku, NumeroDeLote(cmd.numero_lote))
                lote.retirar(cmd.motivo, autorizacion, hoy)
            except ErrorDeDominio as e:
                return Resultado.rechazo(e)
            uow.confirmar()
            return Resultado.ok("LOTE_BLOQUEADO_EN_TODAS_LAS_SUCURSALES")

    def notificar_a_almacen(self, evento: LoteRetirado) -> None:
        """Reacciona al Domain Event LoteRetirado (ya con commit hecho)."""
        self._almacen.notificar_recoleccion_de_lote(evento.sku, evento.numero_lote,
                                                    evento.motivo)


class ResurtidoService:
    """CU-05 (US-12, US-13)."""

    def __init__(self, uow: FabricaDeUoW):
        self._uow = uow

    def generar_alerta_de_resurtido(self, evento: ExistenciaBajoMinimo) -> Resultado:
        with self._uow() as uow:
            producto = uow.productos.obtener(evento.sku)
            inventario = uow.inventarios.obtener(evento.sucursal_id, evento.sku)
            alerta = AlertaDeResurtido(uow.alertas.siguiente_id(), evento.sucursal_id,
                                       evento.sku, producto.proveedor_id,
                                       inventario.cantidad_a_resurtir())
            uow.alertas.agregar(alerta)
            uow.confirmar()
            return Resultado.ok(alerta_id=alerta.id, cantidad_sugerida=alerta.cantidad_sugerida)

    def generar_orden_de_compra(self, cmd: GenerarOrdenDeCompra) -> Resultado:
        with self._uow() as uow:
            if cmd.rol is not Rol.COMPRAS:
                return Resultado(False, "ROL_SIN_PERMISO",
                                 "Sólo Compras genera órdenes de compra")
            alertas = uow.alertas.pendientes_de_proveedor(cmd.proveedor_id)
            if not alertas:
                return Resultado(False, "SIN_ALERTAS_PENDIENTES",
                                 "No hay alertas de resurtido pendientes para el proveedor")
            orden = OrdenDeCompra(uow.ordenes.siguiente_id(), cmd.proveedor_id)
            for alerta in alertas:
                orden.agregar_desde_alerta(alerta)
                alerta.marcar_atendida(orden.id)
            orden.confirmar()
            uow.ordenes.agregar(orden)
            uow.confirmar()
            return Resultado.ok(orden_id=orden.id, lineas=len(orden.lineas))
