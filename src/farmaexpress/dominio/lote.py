from __future__ import annotations

from datetime import date
from enum import Enum

from .base import RaizDeAgregado
from .eventos import LoteMarcadoComoCaducado, LoteRetirado
from .excepciones import LoteCaducado
from .excepciones import LoteRetirado as LoteRetiradoError
from .valores import Autorizacion, NumeroDeLote, Sku, TipoDeAutorizacion


class EstadoDeLote(Enum):
    DISPONIBLE = "Disponible"
    RETIRADO = "Retirado"
    CADUCADO = "Caducado"


class Lote(RaizDeAgregado):
    """Aggregate Lote. Identidad: (SKU, número de lote). Es GLOBAL (no por
    sucursal): retirarlo cambia un único registro y bloquea la venta en todas
    las sucursales (BN-06, US-08). Ver ADR-002."""

    def __init__(self, sku: Sku, numero: NumeroDeLote, fecha_caducidad: date):
        super().__init__()
        self.sku = sku
        self.numero = numero
        self.fecha_caducidad = fecha_caducidad
        self.estado = EstadoDeLote.DISPONIBLE

    def esta_caducado(self, hoy: date) -> bool:
        return hoy > self.fecha_caducidad

    def verificar_vendible(self, hoy: date) -> None:
        """BN-02 / US-07: impedir venta de caducados o lotes retirados."""
        if self.estado is EstadoDeLote.RETIRADO:
            raise LoteRetiradoError(
                f"El lote {self.numero.valor} fue retirado y no puede venderse",
                self.numero)
        if self.estado is EstadoDeLote.CADUCADO or self.esta_caducado(hoy):
            raise LoteCaducado(
                f"El lote {self.numero.valor} está caducado", self.numero)

    def marcar_caducado(self, hoy: date) -> None:
        if self.esta_caducado(hoy) and self.estado is EstadoDeLote.DISPONIBLE:
            self.estado = EstadoDeLote.CADUCADO
            self.registrar_evento(
                LoteMarcadoComoCaducado(self.sku, self.numero, hoy))

    def retirar(self, motivo: str, autorizacion: Autorizacion, hoy: date) -> None:
        """US-08: sólo con Autorizacion de Responsable de farmacia."""
        if autorizacion.tipo is not TipoDeAutorizacion.RETIRO_DE_LOTE:
            raise ValueError("Autorización de tipo incorrecto para retirar un lote")
        if self.estado is EstadoDeLote.RETIRADO:
            return  # idempotente
        self.estado = EstadoDeLote.RETIRADO
        self.registrar_evento(LoteRetirado(self.sku, self.numero, motivo, hoy))
