"""Value Objects: definidos por sus valores, inmutables, sin identidad propia."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from .excepciones import RolSinPermiso


@dataclass(frozen=True)
class Sku:
    valor: str

    def __post_init__(self):
        if not self.valor:
            raise ValueError("El SKU no puede estar vacío")


@dataclass(frozen=True)
class NumeroDeLote:
    valor: str

    def __post_init__(self):
        if not self.valor:
            raise ValueError("El número de lote no puede estar vacío")


@dataclass(frozen=True, order=True)
class Dinero:
    monto: Decimal
    moneda: str = "MXN"

    @staticmethod
    def mxn(valor) -> "Dinero":
        return Dinero(Decimal(str(valor)))

    def __add__(self, otro: "Dinero") -> "Dinero":
        return Dinero(self.monto + otro.monto, self.moneda)

    def por(self, piezas: int) -> "Dinero":
        return Dinero(self.monto * piezas, self.moneda)


class Rol(Enum):
    CAJERO = "Cajero"
    RESPONSABLE_DE_FARMACIA = "Responsable de farmacia"
    COMPRAS = "Compras"
    ALMACEN = "Almacén"
    GERENCIA = "Gerencia / Dirección"


class TipoDeAutorizacion(Enum):
    VENTA_CONTROLADA_EXCEDE_LIMITE = "Venta controlada que excede límite"  # US-04
    SUSTITUCION_DE_CONTROLADO = "Sustitución de medicamento controlado"  # US-06
    RETIRO_DE_LOTE = "Retiro de lote"  # US-08


@dataclass(frozen=True)
class Autorizacion:
    """Aprobación explícita de un rol con permisos suficientes (glosario).
    BN-10: sólo el Responsable de farmacia puede otorgarla."""

    tipo: TipoDeAutorizacion
    autorizado_por: str
    rol: Rol
    fecha: date
    motivo: str = ""

    def __post_init__(self):
        if self.rol is not Rol.RESPONSABLE_DE_FARMACIA:
            raise RolSinPermiso(
                f"El rol '{self.rol.value}' no puede otorgar: {self.tipo.value}"
            )


@dataclass(frozen=True)
class Receta:
    """Receta médica (glosario). Vigencia de 30 días tomada de US-03
    (supuesto pendiente de validar con el stakeholder / asesor legal)."""

    paciente: str
    medico: str
    cedula_profesional: str
    fecha_emision: date | None
    VIGENCIA_EN_DIAS = 30

    def faltantes(self) -> list[str]:
        campos = {
            "paciente": self.paciente,
            "médico": self.medico,
            "cédula profesional": self.cedula_profesional,
            "fecha de emisión": self.fecha_emision,
        }
        return [nombre for nombre, valor in campos.items() if not valor]

    def esta_completa(self) -> bool:
        return not self.faltantes()

    def esta_vigente(self, hoy: date) -> bool:
        return (hoy - self.fecha_emision).days <= self.VIGENCIA_EN_DIAS


@dataclass(frozen=True)
class LimitesDeVentaControlada:
    """US-04: más de 10 piezas o más de $3,000 MXN requiere autorización."""

    max_piezas: int = 10
    max_monto: Dinero = Dinero.mxn(3000)

    def excede(self, piezas: int, monto: Dinero) -> bool:
        return piezas > self.max_piezas or monto > self.max_monto


@dataclass(frozen=True)
class NivelesDeInventario:
    """Punto de reorden (mínimo) y máximo de inventario (glosario)."""

    minimo: int
    maximo: int

    def __post_init__(self):
        if not (0 <= self.minimo <= self.maximo):
            raise ValueError("Se requiere 0 <= mínimo <= máximo")


@dataclass(frozen=True)
class Ticket:
    folio: str
    total: Dinero
    fecha: date
