"""Domain Events: hechos del negocio que ya ocurrieron (en pasado)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .valores import NumeroDeLote, Sku


@dataclass(frozen=True)
class VentaCobrada:
    venta_id: int
    sucursal_id: str
    total_mxn: str
    fecha: date


@dataclass(frozen=True)
class VentaRechazada:
    venta_id: int
    motivo: str
    fecha: date


@dataclass(frozen=True)
class VentaRetenidaPorAutorizacion:
    venta_id: int
    motivo: str


@dataclass(frozen=True)
class SustitucionAceptada:
    venta_id: int
    sku_solicitado: Sku
    sku_sustituto: Sku


@dataclass(frozen=True)
class LoteRetirado:
    sku: Sku
    numero_lote: NumeroDeLote
    motivo: str
    fecha: date


@dataclass(frozen=True)
class LoteMarcadoComoCaducado:
    sku: Sku
    numero_lote: NumeroDeLote
    fecha: date


@dataclass(frozen=True)
class ExistenciaBajoMinimo:
    sucursal_id: str
    sku: Sku
    existencia_actual: int


@dataclass(frozen=True)
class ProductoAgotado:
    sucursal_id: str
    sku: Sku


@dataclass(frozen=True)
class AlertaDeResurtidoGenerada:
    alerta_id: int
    sucursal_id: str
    sku: Sku
    cantidad_sugerida: int


@dataclass(frozen=True)
class OrdenDeCompraConfirmada:
    orden_id: int
    proveedor_id: str
