from __future__ import annotations

from .base import RaizDeAgregado
from .valores import Dinero, Sku


class Producto(RaizDeAgregado):
    """Aggregate de catálogo (lectura casi exclusiva). Identidad: SKU."""

    def __init__(self, sku: Sku, nombre: str, precio: Dinero, es_controlado: bool,
                 proveedor_id: str, sustitutos: tuple[Sku, ...] = ()):
        super().__init__()
        self.sku = sku
        self.nombre = nombre
        self.precio = precio
        self.es_controlado = es_controlado  # medicamento controlado => requiere receta
        self.proveedor_id = proveedor_id
        self.sustitutos = tuple(sustitutos)  # productos equivalentes (producto sustituto)

    def admite_como_sustituto(self, otro: Sku) -> bool:
        return otro in self.sustitutos
