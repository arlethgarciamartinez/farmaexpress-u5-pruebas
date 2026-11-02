"""Regla 3 (BN-02, BN-06, US-07, US-08): un lote caducado o retirado no es vendible."""
from datetime import date, timedelta

import pytest

from farmaexpress.dominio.excepciones import LoteCaducado
from farmaexpress.dominio.excepciones import LoteRetirado as LoteRetiradoError
from farmaexpress.dominio.lote import EstadoDeLote, Lote
from farmaexpress.dominio.valores import (
    Autorizacion,
    NumeroDeLote,
    Rol,
    Sku,
    TipoDeAutorizacion,
)

HOY = date(2026, 10, 12)


def lote_que_caduca_en(dias: int) -> Lote:
    return Lote(Sku("CLONAZEPAM-2"), NumeroDeLote("C-1"), HOY + timedelta(days=dias))


def autorizacion_de_retiro() -> Autorizacion:
    return Autorizacion(
        TipoDeAutorizacion.RETIRO_DE_LOTE,
        "dra.ruiz",
        Rol.RESPONSABLE_DE_FARMACIA,
        HOY,
        "Aviso del proveedor",
    )


def test_lot_with_200_days_left_is_sellable():
    """CP-13 · Éxito · lote vigente: no lanza ninguna excepción."""
    # Arrange
    lote = lote_que_caduca_en(200)

    # Act / Assert
    lote.verificar_vendible(HOY)  # si lanza, la prueba falla
    assert lote.estado is EstadoDeLote.DISPONIBLE


def test_lot_expiring_today_is_still_sellable():
    """CP-14 · Límite · caduca hoy: todavía se vende (la regla es hoy > fecha de caducidad)."""
    lote = lote_que_caduca_en(0)

    lote.verificar_vendible(HOY)

    assert lote.esta_caducado(HOY) is False


def test_lot_is_not_sellable_the_day_after_it_expires():
    """CP-15 · Límite/Error · un día después de la fecha de caducidad ya no se vende."""
    lote = lote_que_caduca_en(0)

    with pytest.raises(LoteCaducado):
        lote.verificar_vendible(HOY + timedelta(days=1))


def test_withdrawn_lot_is_not_sellable():
    """CP-16 · Error · lote retirado por el proveedor o la autoridad."""
    lote = lote_que_caduca_en(200)
    lote.retirar("Aviso del proveedor", autorizacion_de_retiro(), HOY)

    with pytest.raises(LoteRetiradoError):
        lote.verificar_vendible(HOY)

    assert lote.estado is EstadoDeLote.RETIRADO


def test_withdrawing_twice_is_idempotent_and_emits_one_event():
    """CP-17 · Límite · retirar dos veces no duplica el evento (idempotencia, BN-06)."""
    lote = lote_que_caduca_en(200)

    lote.retirar("Aviso", autorizacion_de_retiro(), HOY)
    lote.retirar("Aviso", autorizacion_de_retiro(), HOY)

    assert len(lote.extraer_eventos()) == 1


def test_withdrawal_requires_an_authorization_of_the_right_type():
    """CP-18 · Error · una autorización de otro tipo no sirve para retirar un lote."""
    lote = lote_que_caduca_en(200)
    equivocada = Autorizacion(
        TipoDeAutorizacion.VENTA_CONTROLADA_EXCEDE_LIMITE,
        "dra.ruiz",
        Rol.RESPONSABLE_DE_FARMACIA,
        HOY,
    )

    with pytest.raises(ValueError, match="tipo incorrecto"):
        lote.retirar("Aviso", equivocada, HOY)

    assert lote.estado is EstadoDeLote.DISPONIBLE


def test_expired_lot_is_marked_once_and_emits_one_event():
    """CP-19 · Límite · marcar caducado emite un solo evento aunque se repita."""
    lote = lote_que_caduca_en(-1)

    lote.marcar_caducado(HOY)
    lote.marcar_caducado(HOY)

    assert lote.estado is EstadoDeLote.CADUCADO
    assert len(lote.extraer_eventos()) == 1
