"""Composition root: único lugar donde se eligen las implementaciones concretas."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .aplicacion.consultas import (
    ConsultarCaducidadesProximasHandler,
    ConsultarDisponibilidadEnSucursalesHandler,
)
from .aplicacion.servicios import (
    AutorizacionDeVentaService,
    ResurtidoService,
    RetiroDeLoteService,
    VentaMostradorService,
)
from .dominio.eventos import ExistenciaBajoMinimo, LoteRetirado
from .dominio.seleccion_de_lote import PrimeroEnCaducarPrimeroEnSalir, SeleccionDeLote
from .dominio.valores import LimitesDeVentaControlada
from .infraestructura.memoria import (
    AlmacenEnMemoria,
    BusDeEventosEnMemoria,
    LecturaDeInventarioEnMemoria,
    NotificadorDeAlmacenEnMemoria,
    RelojFijo,
    UnidadDeTrabajoEnMemoria,
)


@dataclass
class Aplicacion:
    almacen: AlmacenEnMemoria
    bus: BusDeEventosEnMemoria
    almacen_fisico: NotificadorDeAlmacenEnMemoria
    venta: VentaMostradorService
    autorizacion: AutorizacionDeVentaService
    retiro: RetiroDeLoteService
    resurtido: ResurtidoService
    disponibilidad: ConsultarDisponibilidadEnSucursalesHandler
    caducidades: ConsultarCaducidadesProximasHandler


def construir_aplicacion(hoy: date) -> Aplicacion:
    almacen, bus = AlmacenEnMemoria(), BusDeEventosEnMemoria()
    reloj, notificador = RelojFijo(hoy), NotificadorDeAlmacenEnMemoria()
    uow = lambda: UnidadDeTrabajoEnMemoria(almacen, bus)   # noqa: E731
    lectura = LecturaDeInventarioEnMemoria(almacen)

    app = Aplicacion(
        almacen=almacen, bus=bus, almacen_fisico=notificador,
        venta=VentaMostradorService(uow, SeleccionDeLote(PrimeroEnCaducarPrimeroEnSalir()),
                                    LimitesDeVentaControlada(), reloj),
        autorizacion=AutorizacionDeVentaService(uow, reloj),
        retiro=RetiroDeLoteService(uow, reloj, notificador),
        resurtido=ResurtidoService(uow),
        disponibilidad=ConsultarDisponibilidadEnSucursalesHandler(lectura),
        caducidades=ConsultarCaducidadesProximasHandler(lectura, reloj),
    )
    bus.suscribir(ExistenciaBajoMinimo, app.resurtido.generar_alerta_de_resurtido)
    bus.suscribir(LoteRetirado, app.retiro.notificar_a_almacen)
    return app
