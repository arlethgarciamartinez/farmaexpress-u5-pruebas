"""Commands: intención de CAMBIAR el estado. Nombres en infinitivo/imperativo de negocio."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..dominio.valores import Rol, Sku, TipoDeAutorizacion


@dataclass(frozen=True)
class IniciarVenta:
    sucursal_id: str
    cajero: str


@dataclass(frozen=True)
class AgregarProductoALaVenta:
    venta_id: int
    sku: Sku
    cantidad: int


@dataclass(frozen=True)
class RegistrarRecetaEnVenta:
    venta_id: int
    paciente: str
    medico: str
    cedula_profesional: str
    fecha_emision: date | None


@dataclass(frozen=True)
class AceptarSustituto:
    venta_id: int
    sku_solicitado: Sku
    sku_sustituto: Sku
    cantidad: int
    autorizado_por: str | None = None       # sólo para sustituir controlados
    rol_autorizador: Rol | None = None


@dataclass(frozen=True)
class OtorgarAutorizacionDeVenta:
    venta_id: int
    tipo: TipoDeAutorizacion
    autorizado_por: str
    rol: Rol
    motivo: str = ""


@dataclass(frozen=True)
class ConfirmarCobro:
    venta_id: int


@dataclass(frozen=True)
class RegistrarRetiroDeLote:
    sku: Sku
    numero_lote: str
    motivo: str
    registrado_por: str
    rol: Rol


@dataclass(frozen=True)
class GenerarOrdenDeCompra:
    proveedor_id: str
    confirmada_por: str
    rol: Rol
