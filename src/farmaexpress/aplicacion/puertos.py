"""Puertos (interfaces) que la capa de aplicación necesita de la infraestructura."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..dominio.repositorios import (
    RepositorioDeAlertas,
    RepositorioDeInventario,
    RepositorioDeLotes,
    RepositorioDeOrdenesDeCompra,
    RepositorioDeProductos,
    RepositorioDeVentas,
)
from ..dominio.valores import NumeroDeLote, Sku


class UnidadDeTrabajo(ABC):
    """Unit of Work: una operación de negocio = una transacción.
    Inicia al entrar al bloque `with`; `confirmar()` hace commit y SOLO
    después publica los Domain Events; si el bloque termina sin confirmar
    (o con excepción) se revierte todo."""

    ventas: RepositorioDeVentas
    lotes: RepositorioDeLotes
    inventarios: RepositorioDeInventario
    productos: RepositorioDeProductos
    alertas: RepositorioDeAlertas
    ordenes: RepositorioDeOrdenesDeCompra

    @abstractmethod
    def __enter__(self) -> "UnidadDeTrabajo": ...
    @abstractmethod
    def __exit__(self, *exc) -> None: ...
    @abstractmethod
    def confirmar(self) -> None: ...


class Reloj(ABC):
    @abstractmethod
    def hoy(self) -> date: ...


class NotificadorDeAlmacen(ABC):
    @abstractmethod
    def notificar_recoleccion_de_lote(self, sku: Sku, numero: NumeroDeLote,
                                      motivo: str) -> None: ...


class LecturaDeInventario(ABC):
    """Puerto de LECTURA (lado Query de CQRS). Devuelve datos planos, no Aggregates."""

    @abstractmethod
    def existencia_en_otras_sucursales(self, sucursal_actual: str, sku: Sku) -> list[tuple[str, int]]: ...

    @abstractmethod
    def lotes_con_existencia(self, sucursal_id: str) -> list[tuple[Sku, NumeroDeLote, date, int]]: ...
