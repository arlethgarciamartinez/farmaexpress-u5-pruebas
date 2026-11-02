"""Interfaces de Repository: hablan el lenguaje del dominio, sin SQL.
Pertenecen al dominio; la infraestructura las implementa."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .inventario import InventarioDeProducto
from .lote import Lote
from .orden_de_compra import AlertaDeResurtido, OrdenDeCompra
from .producto import Producto
from .valores import NumeroDeLote, Sku
from .venta import Venta


class RepositorioDeVentas(ABC):
    @abstractmethod
    def siguiente_id(self) -> int: ...
    @abstractmethod
    def agregar(self, venta: Venta) -> None: ...
    @abstractmethod
    def obtener(self, venta_id: int) -> Venta: ...


class RepositorioDeLotes(ABC):
    @abstractmethod
    def obtener(self, sku: Sku, numero: NumeroDeLote) -> Lote: ...
    @abstractmethod
    def de_producto(self, sku: Sku) -> list[Lote]: ...
    @abstractmethod
    def agregar(self, lote: Lote) -> None: ...


class RepositorioDeInventario(ABC):
    @abstractmethod
    def obtener(self, sucursal_id: str, sku: Sku) -> InventarioDeProducto: ...
    @abstractmethod
    def agregar(self, inventario: InventarioDeProducto) -> None: ...


class RepositorioDeProductos(ABC):
    @abstractmethod
    def obtener(self, sku: Sku) -> Producto: ...
    @abstractmethod
    def agregar(self, producto: Producto) -> None: ...


class RepositorioDeAlertas(ABC):
    @abstractmethod
    def siguiente_id(self) -> int: ...
    @abstractmethod
    def agregar(self, alerta: AlertaDeResurtido) -> None: ...
    @abstractmethod
    def pendientes_de_proveedor(self, proveedor_id: str) -> list[AlertaDeResurtido]: ...


class RepositorioDeOrdenesDeCompra(ABC):
    @abstractmethod
    def siguiente_id(self) -> int: ...
    @abstractmethod
    def agregar(self, orden: OrdenDeCompra) -> None: ...
    @abstractmethod
    def obtener(self, orden_id: int) -> OrdenDeCompra: ...
