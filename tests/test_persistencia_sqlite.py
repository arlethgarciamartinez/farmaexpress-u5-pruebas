"""Integración con SQLite EN MEMORIA y SQLAlchemy: commit, rollback y contrato del repositorio.

Cada prueba crea su propio motor, así que no comparten datos ni tocan información real.
"""
from datetime import date, timedelta
from unittest.mock import Mock

import pytest

from farmaexpress.aplicacion.comandos import RegistrarRetiroDeLote
from farmaexpress.aplicacion.puertos import NotificadorDeAlmacen
from farmaexpress.aplicacion.servicios import RetiroDeLoteService
from farmaexpress.dominio.eventos import LoteRetirado
from farmaexpress.dominio.excepciones import EntidadNoEncontrada
from farmaexpress.dominio.lote import EstadoDeLote, Lote
from farmaexpress.dominio.valores import (
    Autorizacion,
    NumeroDeLote,
    Rol,
    Sku,
    TipoDeAutorizacion,
)
from farmaexpress.infraestructura.memoria import BusDeEventosEnMemoria, RelojFijo
from farmaexpress.infraestructura.sql import UnidadDeTrabajoSql, crear_motor

HOY = date(2026, 10, 12)
SKU = Sku("PARACETAMOL-500")
NUMERO = NumeroDeLote("P-1")


@pytest.fixture
def motor():
    motor = crear_motor()  # SQLite en memoria, uno nuevo por prueba
    yield motor
    motor.dispose()  # cierra las conexiones al terminar la prueba


@pytest.fixture
def bus():
    return BusDeEventosEnMemoria()


def sembrar_lote(motor, bus) -> None:
    with UnidadDeTrabajoSql(motor, bus) as uow:
        uow.lotes.agregar(Lote(SKU, NUMERO, HOY + timedelta(days=200)))
        uow.confirmar()


def leer_lote(motor, bus) -> Lote:
    with UnidadDeTrabajoSql(motor, bus) as uow:  # sesión NUEVA: lee lo realmente guardado
        return uow.lotes.obtener(SKU, NUMERO)


def autorizacion_de_retiro() -> Autorizacion:
    return Autorizacion(
        TipoDeAutorizacion.RETIRO_DE_LOTE, "dra.ruiz", Rol.RESPONSABLE_DE_FARMACIA, HOY
    )


def test_committed_lot_is_persisted_and_can_be_read_in_a_new_session(motor, bus):
    """CP-24 · Éxito · commit: el lote se guarda y una sesión nueva lo lee completo."""
    # Arrange / Act
    sembrar_lote(motor, bus)

    # Assert
    lote = leer_lote(motor, bus)
    assert lote.sku == SKU
    assert lote.numero == NUMERO
    assert lote.fecha_caducidad == HOY + timedelta(days=200)
    assert lote.estado is EstadoDeLote.DISPONIBLE


def test_lot_added_without_confirming_is_rolled_back(motor, bus):
    """CP-25 · Error · sin confirmar, al salir del bloque se hace rollback."""
    with UnidadDeTrabajoSql(motor, bus) as uow:
        uow.lotes.agregar(Lote(SKU, NUMERO, HOY + timedelta(days=200)))
        # no se llama a confirmar()

    with pytest.raises(EntidadNoEncontrada):
        leer_lote(motor, bus)


def test_change_made_before_an_exception_is_rolled_back(motor, bus):
    """CP-26 · Error · si algo falla a mitad de la operación, el retiro no queda guardado."""
    sembrar_lote(motor, bus)

    with pytest.raises(RuntimeError), UnidadDeTrabajoSql(motor, bus) as uow:
        lote = uow.lotes.obtener(SKU, NUMERO)
        lote.retirar("Aviso", autorizacion_de_retiro(), HOY)
        raise RuntimeError("falla simulada antes del commit")

    assert leer_lote(motor, bus).estado is EstadoDeLote.DISPONIBLE


def test_missing_lot_raises_the_common_repository_error(motor, bus):
    """CP-27 · Error · el repositorio SQL cumple el mismo contrato que el de memoria."""
    with UnidadDeTrabajoSql(motor, bus) as uow, pytest.raises(EntidadNoEncontrada):
        uow.lotes.obtener(SKU, NumeroDeLote("NO-EXISTE"))


def test_repository_returns_only_lots_of_the_requested_product(motor, bus):
    """CP-28 · Límite · de_producto no mezcla lotes de otros SKU."""
    with UnidadDeTrabajoSql(motor, bus) as uow:
        uow.lotes.agregar(Lote(SKU, NumeroDeLote("P-1"), HOY + timedelta(days=30)))
        uow.lotes.agregar(Lote(SKU, NumeroDeLote("P-2"), HOY + timedelta(days=60)))
        uow.lotes.agregar(Lote(Sku("IBUPROFENO-400"), NumeroDeLote("I-1"), HOY))
        uow.confirmar()

    with UnidadDeTrabajoSql(motor, bus) as uow:
        numeros = sorted(lote.numero.valor for lote in uow.lotes.de_producto(SKU))

    assert numeros == ["P-1", "P-2"]


def armar_servicio_de_retiro(motor, bus, almacen):
    servicio = RetiroDeLoteService(
        lambda: UnidadDeTrabajoSql(motor, bus), RelojFijo(HOY), almacen
    )
    bus.suscribir(LoteRetirado, servicio.notificar_a_almacen)
    return servicio


def test_withdrawal_use_case_persists_the_new_state(motor, bus):
    """CP-29 · Éxito · CU-04 de punta a punta: el retiro queda guardado en la base."""
    sembrar_lote(motor, bus)
    servicio = armar_servicio_de_retiro(motor, bus, Mock(spec=NotificadorDeAlmacen))

    resultado = servicio.registrar_retiro(RegistrarRetiroDeLote(
        SKU, "P-1", "Aviso del proveedor", "dra.ruiz", Rol.RESPONSABLE_DE_FARMACIA
    ))

    assert resultado.exitoso
    assert leer_lote(motor, bus).estado is EstadoDeLote.RETIRADO


def test_withdrawal_by_a_cashier_is_denied_and_nothing_is_saved(motor, bus):
    """CP-30 · Error · seguridad + persistencia: un Cajero no puede retirar lotes."""
    sembrar_lote(motor, bus)
    servicio = armar_servicio_de_retiro(motor, bus, Mock(spec=NotificadorDeAlmacen))

    resultado = servicio.registrar_retiro(RegistrarRetiroDeLote(
        SKU, "P-1", "Aviso", "cajero.ana", Rol.CAJERO
    ))

    assert not resultado.exitoso
    assert resultado.codigo == "ROL_SIN_PERMISO"
    assert leer_lote(motor, bus).estado is EstadoDeLote.DISPONIBLE
