from __future__ import annotations

from datetime import date

from .base import RaizDeAgregado
from .eventos import ExistenciaBajoMinimo, ProductoAgotado
from .excepciones import ExistenciaInsuficiente
from .valores import NivelesDeInventario, NumeroDeLote, Sku


class InventarioDeProducto(RaizDeAgregado):
    """Aggregate: existencia de UN producto en UNA sucursal, desglosada por
    lote. Identidad: (sucursal, SKU). Invariante: ninguna existencia < 0."""

    def __init__(self, sucursal_id: str, sku: Sku, niveles: NivelesDeInventario,
                 existencias: dict[NumeroDeLote, int] | None = None):
        super().__init__()
        self.sucursal_id = sucursal_id
        self.sku = sku
        self.niveles = niveles
        self.existencias: dict[NumeroDeLote, int] = dict(existencias or {})

    def total(self) -> int:
        return sum(self.existencias.values())

    def cantidad_en(self, lote: NumeroDeLote) -> int:
        return self.existencias.get(lote, 0)

    def lotes_con_existencia(self) -> list[NumeroDeLote]:
        return [l for l, c in self.existencias.items() if c > 0]

    def descontar(self, lote: NumeroDeLote, cantidad: int, hoy: date) -> None:
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva")
        if self.cantidad_en(lote) < cantidad:
            raise ExistenciaInsuficiente(
                f"No hay existencia suficiente del lote {lote.valor}")
        antes = self.total()
        self.existencias[lote] -= cantidad
        despues = self.total()
        if despues == 0:
            self.registrar_evento(ProductoAgotado(self.sucursal_id, self.sku))
        # Sólo al CRUZAR el mínimo, para no generar alertas duplicadas (US-12)
        if antes >= self.niveles.minimo > despues:
            self.registrar_evento(
                ExistenciaBajoMinimo(self.sucursal_id, self.sku, despues))

    def recibir(self, lote: NumeroDeLote, cantidad: int) -> None:
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva")
        self.existencias[lote] = self.cantidad_en(lote) + cantidad

    def cantidad_a_resurtir(self) -> int:
        """Máximo de inventario menos la existencia actual (glosario)."""
        return max(self.niveles.maximo - self.total(), 0)
