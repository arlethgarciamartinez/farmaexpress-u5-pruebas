"""Implementaciones EN MEMORIA de los puertos (para pruebas y demostración).
En producción serían RepositorioDeVentasSql, etc., sobre una BD relacional;
el dominio y la aplicación no cambian (principio D de SOLID, ADR-003)."""
from __future__ import annotations

import copy
from datetime import date

from ..aplicacion.puertos import LecturaDeInventario, NotificadorDeAlmacen, Reloj, UnidadDeTrabajo
from ..dominio.excepciones import EntidadNoEncontrada
from ..dominio.inventario import InventarioDeProducto
from ..dominio.lote import EstadoDeLote, Lote
from ..dominio.orden_de_compra import AlertaDeResurtido, EstadoDeAlerta, OrdenDeCompra
from ..dominio.producto import Producto
from ..dominio.repositorios import (
    RepositorioDeAlertas,
    RepositorioDeInventario,
    RepositorioDeLotes,
    RepositorioDeOrdenesDeCompra,
    RepositorioDeProductos,
    RepositorioDeVentas,
)
from ..dominio.valores import NumeroDeLote, Sku
from ..dominio.venta import Venta


class RelojFijo(Reloj):
    def __init__(self, hoy: date):
        self._hoy = hoy

    def hoy(self) -> date:
        return self._hoy


class AlmacenEnMemoria:
    """Estado compartido que simula la base de datos."""

    def __init__(self):
        self.ventas: dict[int, Venta] = {}
        self.lotes: dict[tuple[Sku, NumeroDeLote], Lote] = {}
        self.inventarios: dict[tuple[str, Sku], InventarioDeProducto] = {}
        self.productos: dict[Sku, Producto] = {}
        self.alertas: dict[int, AlertaDeResurtido] = {}
        self.ordenes: dict[int, OrdenDeCompra] = {}

    def instantanea(self) -> dict:
        return copy.deepcopy(self.__dict__)

    def restaurar(self, instantanea: dict) -> None:
        self.__dict__.update(instantanea)


class BusDeEventosEnMemoria:
    def __init__(self):
        self._manejadores: dict[type, list] = {}
        self.publicados: list = []
        self.errores: list = []

    def suscribir(self, tipo_de_evento: type, manejador) -> None:
        self._manejadores.setdefault(tipo_de_evento, []).append(manejador)

    def publicar(self, evento) -> None:
        self.publicados.append(evento)
        for manejador in self._manejadores.get(type(evento), []):
            try:
                manejador(evento)
            except Exception as error:      # un manejador no deshace la venta ya confirmada
                self.errores.append((evento, error))


class _Repo:
    def __init__(self, uow: "UnidadDeTrabajoEnMemoria"):
        self._uow = uow

    @property
    def _a(self) -> AlmacenEnMemoria:
        return self._uow.almacen

    def _ver(self, agregado):
        self._uow._vistos.append(agregado)
        return agregado

    def _buscar(self, coleccion: dict, clave, nombre: str):
        try:
            return self._ver(coleccion[clave])
        except KeyError:
            raise EntidadNoEncontrada(f"No existe {nombre}: {clave}") from None


class RepositorioDeVentasEnMemoria(_Repo, RepositorioDeVentas):
    def siguiente_id(self) -> int:
        return max(self._a.ventas, default=0) + 1

    def agregar(self, venta: Venta) -> None:
        self._a.ventas[venta.id] = self._ver(venta)

    def obtener(self, venta_id: int) -> Venta:
        return self._buscar(self._a.ventas, venta_id, 'la venta')


class RepositorioDeLotesEnMemoria(_Repo, RepositorioDeLotes):
    def obtener(self, sku: Sku, numero: NumeroDeLote) -> Lote:
        return self._buscar(self._a.lotes, (sku, numero), 'el lote')

    def de_producto(self, sku: Sku) -> list[Lote]:
        return [self._ver(l) for (s, _), l in self._a.lotes.items() if s == sku]

    def agregar(self, lote: Lote) -> None:
        self._a.lotes[(lote.sku, lote.numero)] = self._ver(lote)


class RepositorioDeInventarioEnMemoria(_Repo, RepositorioDeInventario):
    def obtener(self, sucursal_id: str, sku: Sku) -> InventarioDeProducto:
        return self._buscar(self._a.inventarios, (sucursal_id, sku), 'el inventario')

    def agregar(self, inventario: InventarioDeProducto) -> None:
        self._a.inventarios[(inventario.sucursal_id, inventario.sku)] = self._ver(inventario)


class RepositorioDeProductosEnMemoria(_Repo, RepositorioDeProductos):
    def obtener(self, sku: Sku) -> Producto:
        return self._buscar(self._a.productos, sku, 'el producto')

    def agregar(self, producto: Producto) -> None:
        self._a.productos[producto.sku] = producto


class RepositorioDeAlertasEnMemoria(_Repo, RepositorioDeAlertas):
    def siguiente_id(self) -> int:
        return max(self._a.alertas, default=0) + 1

    def agregar(self, alerta: AlertaDeResurtido) -> None:
        self._a.alertas[alerta.id] = self._ver(alerta)

    def pendientes_de_proveedor(self, proveedor_id: str) -> list[AlertaDeResurtido]:
        return [self._ver(a) for a in self._a.alertas.values()
                if a.proveedor_id == proveedor_id and a.estado is EstadoDeAlerta.PENDIENTE]


class RepositorioDeOrdenesDeCompraEnMemoria(_Repo, RepositorioDeOrdenesDeCompra):
    def siguiente_id(self) -> int:
        return max(self._a.ordenes, default=0) + 1

    def agregar(self, orden: OrdenDeCompra) -> None:
        self._a.ordenes[orden.id] = self._ver(orden)

    def obtener(self, orden_id: int) -> OrdenDeCompra:
        return self._buscar(self._a.ordenes, orden_id, 'la orden de compra')


class UnidadDeTrabajoEnMemoria(UnidadDeTrabajo):
    def __init__(self, almacen: AlmacenEnMemoria, bus: BusDeEventosEnMemoria):
        self.almacen = almacen
        self._bus = bus
        self._vistos: list = []
        self._confirmada = False
        self._instantanea: dict | None = None
        self.ventas = RepositorioDeVentasEnMemoria(self)
        self.lotes = RepositorioDeLotesEnMemoria(self)
        self.inventarios = RepositorioDeInventarioEnMemoria(self)
        self.productos = RepositorioDeProductosEnMemoria(self)
        self.alertas = RepositorioDeAlertasEnMemoria(self)
        self.ordenes = RepositorioDeOrdenesDeCompraEnMemoria(self)

    def __enter__(self):
        self._instantanea = self.almacen.instantanea()       # BEGIN
        return self

    def confirmar(self) -> None:                              # COMMIT
        self._confirmada = True
        eventos = []
        for agregado in self._vistos:
            eventos.extend(agregado.extraer_eventos())
        self._instantanea = None
        for evento in eventos:                                # publicar DESPUÉS del commit
            self._bus.publicar(evento)

    def __exit__(self, *exc) -> None:
        if not self._confirmada and self._instantanea is not None:
            self.almacen.restaurar(self._instantanea)         # ROLLBACK
        self._instantanea = None


class NotificadorDeAlmacenEnMemoria(NotificadorDeAlmacen):
    def __init__(self):
        self.notificaciones: list[tuple[Sku, NumeroDeLote, str]] = []

    def notificar_recoleccion_de_lote(self, sku, numero, motivo) -> None:
        self.notificaciones.append((sku, numero, motivo))


class LecturaDeInventarioEnMemoria(LecturaDeInventario):
    """Lee directamente el almacén (proyección de lectura). En producción sería
    una consulta SQL / vista optimizada, sin cargar Aggregates."""

    def __init__(self, almacen: AlmacenEnMemoria):
        self._a = almacen

    def existencia_en_otras_sucursales(self, sucursal_actual, sku):
        return [(s, inv.total()) for (s, k), inv in self._a.inventarios.items()
                if k == sku and s != sucursal_actual]

    def lotes_con_existencia(self, sucursal_id):
        filas = []
        for (s, sku), inv in self._a.inventarios.items():
            if s != sucursal_id:
                continue
            for numero in inv.lotes_con_existencia():
                lote = self._a.lotes[(sku, numero)]
                if lote.estado is EstadoDeLote.DISPONIBLE:
                    filas.append((sku, numero, lote.fecha_caducidad, inv.cantidad_en(numero)))
        return filas
