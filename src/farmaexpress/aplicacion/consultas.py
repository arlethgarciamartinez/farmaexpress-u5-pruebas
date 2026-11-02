"""Lado Query de CQRS: no usan Aggregates ni Unit of Work; devuelven DTOs de
lectura pensados para la pantalla/reporte (no son el modelo de escritura)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..dominio.valores import Sku
from .puertos import LecturaDeInventario, Reloj


# ---- Query 1: US-15 ----------------------------------------------------
@dataclass(frozen=True)
class ConsultarDisponibilidadEnSucursales:
    sucursal_actual: str
    sku: Sku


@dataclass(frozen=True)
class DisponibilidadEnSucursalDTO:
    sucursal_id: str
    cantidad_disponible: int


class ConsultarDisponibilidadEnSucursalesHandler:
    def __init__(self, lectura: LecturaDeInventario):
        self._lectura = lectura

    def manejar(self, q: ConsultarDisponibilidadEnSucursales) -> list[DisponibilidadEnSucursalDTO]:
        filas = self._lectura.existencia_en_otras_sucursales(q.sucursal_actual, q.sku)
        return [DisponibilidadEnSucursalDTO(s, c) for s, c in filas if c > 0]


# ---- Query 2: US-09 / US-18 -------------------------------------------
@dataclass(frozen=True)
class ConsultarCaducidadesProximas:
    sucursal_id: str


@dataclass(frozen=True)
class CaducidadProximaDTO:
    sku: str
    numero_lote: str
    fecha_caducidad: date
    dias_restantes: int
    severidad_dias: int          # 90, 60 o 30 (umbrales del BRD)
    cantidad: int


class ConsultarCaducidadesProximasHandler:
    UMBRALES = (30, 60, 90)

    def __init__(self, lectura: LecturaDeInventario, reloj: Reloj):
        self._lectura, self._reloj = lectura, reloj

    def manejar(self, q: ConsultarCaducidadesProximas) -> list[CaducidadProximaDTO]:
        hoy = self._reloj.hoy()
        resultado = []
        for sku, lote, caduca, cantidad in self._lectura.lotes_con_existencia(q.sucursal_id):
            dias = (caduca - hoy).days
            umbral = next((u for u in self.UMBRALES if dias <= u), None)
            if umbral is not None and dias >= 0:
                resultado.append(CaducidadProximaDTO(sku.valor, lote.valor, caduca,
                                                     dias, umbral, cantidad))
        return sorted(resultado, key=lambda d: d.dias_restantes)
