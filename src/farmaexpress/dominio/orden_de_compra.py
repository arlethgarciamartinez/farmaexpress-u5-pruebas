from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .base import RaizDeAgregado
from .eventos import AlertaDeResurtidoGenerada, OrdenDeCompraConfirmada
from .excepciones import ErrorDeDominio
from .valores import Sku


class EstadoDeAlerta(Enum):
    PENDIENTE = "Pendiente"
    ATENDIDA = "Atendida"


class AlertaDeResurtido(RaizDeAgregado):
    """US-12: producto, sucursal y cantidad sugerida a comprar."""

    def __init__(self, id: int, sucursal_id: str, sku: Sku, proveedor_id: str,
                 cantidad_sugerida: int):
        super().__init__()
        self.id = id
        self.sucursal_id = sucursal_id
        self.sku = sku
        self.proveedor_id = proveedor_id
        self.cantidad_sugerida = cantidad_sugerida
        self.estado = EstadoDeAlerta.PENDIENTE
        self.orden_id: int | None = None
        self.registrar_evento(AlertaDeResurtidoGenerada(
            id, sucursal_id, sku, cantidad_sugerida))

    def marcar_atendida(self, orden_id: int) -> None:
        self.estado = EstadoDeAlerta.ATENDIDA
        self.orden_id = orden_id


class EstadoDeOrden(Enum):
    BORRADOR = "Borrador"
    CONFIRMADA = "Confirmada"


@dataclass(frozen=True)
class LineaDeOrden:
    sku: Sku
    sucursal_destino: str
    cantidad: int


class OrdenDeCompra(RaizDeAgregado):
    """US-13. Invariante: una orden pertenece a UN proveedor y debe tener al
    menos una línea para confirmarse."""

    def __init__(self, id: int, proveedor_id: str):
        super().__init__()
        self.id = id
        self.proveedor_id = proveedor_id
        self.lineas: list[LineaDeOrden] = []
        self.estado = EstadoDeOrden.BORRADOR

    def agregar_desde_alerta(self, alerta: AlertaDeResurtido) -> None:
        if alerta.proveedor_id != self.proveedor_id:
            raise ErrorDeDominio("La alerta pertenece a otro proveedor")
        self.lineas.append(LineaDeOrden(alerta.sku, alerta.sucursal_id,
                                        alerta.cantidad_sugerida))

    def confirmar(self) -> None:
        if not self.lineas:
            raise ErrorDeDominio("La orden de compra no tiene líneas")
        self.estado = EstadoDeOrden.CONFIRMADA
        self.registrar_evento(OrdenDeCompraConfirmada(self.id, self.proveedor_id))
