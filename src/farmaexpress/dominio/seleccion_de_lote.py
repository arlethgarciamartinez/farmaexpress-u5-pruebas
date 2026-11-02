"""Domain Service: elegir el lote que se vende. Cruza dos Aggregates (Lote e
InventarioDeProducto), por eso no pertenece a ninguno de los dos.

La política de orden es intercambiable (OCP). FEFO (primero en caducar,
primero en salir) es un SUPUESTO pendiente de validar: U2 sólo dice
'descuenta la existencia del lote correspondiente' (US-01)."""
from __future__ import annotations

from datetime import date
from typing import Iterable, Protocol

from .excepciones import ErrorDeDominio, ExistenciaInsuficiente
from .inventario import InventarioDeProducto
from .lote import Lote
from .valores import NumeroDeLote


class PoliticaDeOrdenDeLotes(Protocol):
    def ordenar(self, lotes: Iterable[Lote]) -> list[Lote]: ...


class PrimeroEnCaducarPrimeroEnSalir:
    def ordenar(self, lotes: Iterable[Lote]) -> list[Lote]:
        return sorted(lotes, key=lambda l: l.fecha_caducidad)


class SeleccionDeLote:
    def __init__(self, politica: PoliticaDeOrdenDeLotes):
        self._politica = politica

    def seleccionar(self, inventario: InventarioDeProducto,
                    lotes: dict[NumeroDeLote, Lote], cantidad: int,
                    hoy: date) -> NumeroDeLote:
        candidatos = [lotes[n] for n in inventario.lotes_con_existencia() if n in lotes]
        primer_bloqueo: ErrorDeDominio | None = None
        for lote in self._politica.ordenar(candidatos):
            try:
                lote.verificar_vendible(hoy)
            except ErrorDeDominio as bloqueo:      # caducado o retirado
                primer_bloqueo = primer_bloqueo or bloqueo
                continue
            if inventario.cantidad_en(lote.numero) >= cantidad:
                return lote.numero
        if primer_bloqueo is not None:
            raise primer_bloqueo
        raise ExistenciaInsuficiente("No hay existencia disponible del producto")
