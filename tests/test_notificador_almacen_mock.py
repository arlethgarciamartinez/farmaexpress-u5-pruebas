"""Servicio externo simulado con unittest.mock: el aviso a Almacén al retirar un lote.

Se usa Mock(spec=NotificadorDeAlmacen): imita el puerto real y falla si se llama a un método
que no existe. No se hace ninguna llamada de red ni se contacta a Almacén de verdad.
"""
from datetime import date, timedelta
from unittest.mock import Mock

import pytest

from farmaexpress.aplicacion.comandos import RegistrarRetiroDeLote
from farmaexpress.aplicacion.puertos import NotificadorDeAlmacen
from farmaexpress.aplicacion.servicios import RetiroDeLoteService
from farmaexpress.dominio.eventos import LoteRetirado
from farmaexpress.dominio.lote import EstadoDeLote, Lote
from farmaexpress.dominio.valores import NumeroDeLote, Rol, Sku
from farmaexpress.infraestructura.memoria import BusDeEventosEnMemoria, RelojFijo
from farmaexpress.infraestructura.sql import UnidadDeTrabajoSql, crear_motor

HOY = date(2026, 10, 12)
SKU = Sku("PARACETAMOL-500")
NUMERO = NumeroDeLote("P-1")
MOTIVO = "Aviso del proveedor"


@pytest.fixture
def entorno():
    motor, bus = crear_motor(), BusDeEventosEnMemoria()
    almacen = Mock(spec=NotificadorDeAlmacen)
    servicio = RetiroDeLoteService(lambda: UnidadDeTrabajoSql(motor, bus), RelojFijo(HOY), almacen)
    bus.suscribir(LoteRetirado, servicio.notificar_a_almacen)
    with UnidadDeTrabajoSql(motor, bus) as uow:
        uow.lotes.agregar(Lote(SKU, NUMERO, HOY + timedelta(days=200)))
        uow.confirmar()
    yield motor, bus, almacen, servicio
    motor.dispose()  # cierra las conexiones al terminar la prueba


def retirar(servicio, rol=Rol.RESPONSABLE_DE_FARMACIA):
    return servicio.registrar_retiro(RegistrarRetiroDeLote(SKU, "P-1", MOTIVO, "dra.ruiz", rol))


def estado_guardado(motor, bus) -> EstadoDeLote:
    with UnidadDeTrabajoSql(motor, bus) as uow:
        return uow.lotes.obtener(SKU, NUMERO).estado


def test_warehouse_is_notified_when_the_gateway_approves(entorno):
    """CP-31 · Éxito · el servicio externo responde bien: se avisa a Almacén una vez."""
    # Arrange
    motor, bus, almacen, servicio = entorno

    # Act
    resultado = retirar(servicio)

    # Assert
    assert resultado.exitoso
    almacen.notificar_recoleccion_de_lote.assert_called_once_with(SKU, NUMERO, MOTIVO)
    assert bus.errores == []


def test_withdrawal_is_kept_when_the_warehouse_service_is_down(entorno):
    """CP-32 · Error · Almacén no responde (ConnectionError): el retiro YA confirmado no se deshace."""
    motor, bus, almacen, servicio = entorno
    almacen.notificar_recoleccion_de_lote.side_effect = ConnectionError("sin red")

    resultado = retirar(servicio)

    assert resultado.exitoso
    assert estado_guardado(motor, bus) is EstadoDeLote.RETIRADO
    assert len(bus.errores) == 1
    assert isinstance(bus.errores[0][1], ConnectionError)


def test_withdrawal_is_kept_when_the_warehouse_service_times_out(entorno):
    """CP-33 · Límite · timeout: mismo comportamiento y el error queda registrado."""
    motor, bus, almacen, servicio = entorno
    almacen.notificar_recoleccion_de_lote.side_effect = TimeoutError("tiempo agotado")

    resultado = retirar(servicio)

    assert resultado.exitoso
    assert estado_guardado(motor, bus) is EstadoDeLote.RETIRADO
    assert isinstance(bus.errores[0][1], TimeoutError)


def test_warehouse_is_not_notified_when_the_role_is_not_allowed(entorno):
    """CP-34 · Error · si el retiro se rechaza por rol, no hay aviso a Almacén."""
    motor, bus, almacen, servicio = entorno

    resultado = retirar(servicio, rol=Rol.CAJERO)

    assert not resultado.exitoso
    almacen.notificar_recoleccion_de_lote.assert_not_called()


def test_withdrawing_an_already_withdrawn_lot_notifies_only_once(entorno):
    """CP-35 · Límite · el retiro es idempotente: no se avisa dos veces a Almacén."""
    motor, bus, almacen, servicio = entorno

    retirar(servicio)
    retirar(servicio)

    assert almacen.notificar_recoleccion_de_lote.call_count == 1
