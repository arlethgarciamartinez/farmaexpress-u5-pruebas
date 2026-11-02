"""Regla 2 (US-04, BN-10, invariante I2): una venta de controlados que supera 10 piezas
o $3,000 MXN se retiene hasta que el Responsable de farmacia la autorice."""
from datetime import date, timedelta

import pytest

from farmaexpress.dominio.producto import Producto
from farmaexpress.dominio.valores import (
    Autorizacion,
    Dinero,
    LimitesDeVentaControlada,
    NumeroDeLote,
    Receta,
    Rol,
    Sku,
    TipoDeAutorizacion,
)
from farmaexpress.dominio.venta import EstadoDeVenta, Venta

HOY = date(2026, 10, 12)
LOTE = NumeroDeLote("C-1")
LIMITES = LimitesDeVentaControlada()


def controlado(precio) -> Producto:
    return Producto(Sku("CLONAZEPAM-2"), "Clonazepam 2 mg", Dinero.mxn(precio), True, "PROV-B")


def venta_controlada(precio, piezas: int) -> Venta:
    venta = Venta(id=1, sucursal_id="SUC-01", cajero="cajero.ana", fecha=HOY)
    venta.agregar_producto(controlado(precio), LOTE, cantidad=piezas)
    venta.registrar_receta(Receta("Juan López", "Dr. Pérez", "CED-123", HOY - timedelta(days=3)))
    return venta


def test_controlled_sale_below_both_limits_is_charged():
    """CP-07 · Éxito · 5 piezas x $400 = $2,000: no necesita autorización."""
    # Arrange
    venta = venta_controlada(400, piezas=5)

    # Act
    ticket = venta.confirmar_cobro(HOY, LIMITES)

    # Assert
    assert ticket is not None
    assert ticket.total == Dinero.mxn(2000)
    assert venta.estado is EstadoDeVenta.COBRADA


def test_sale_exactly_at_10_pieces_and_3000_pesos_is_charged_without_authorization():
    """CP-08 · Límite · 10 piezas x $300 = $3,000 exactos: US-04 dice 'supera', no 'iguala'."""
    venta = venta_controlada(300, piezas=10)

    ticket = venta.confirmar_cobro(HOY, LIMITES)

    assert ticket is not None
    assert ticket.total == Dinero.mxn(3000)
    assert venta.estado is EstadoDeVenta.COBRADA


def test_sale_of_11_pieces_is_held_for_authorization():
    """CP-09 · Error · 11 piezas: la venta queda retenida y NO se cobra."""
    venta = venta_controlada(100, piezas=11)

    ticket = venta.confirmar_cobro(HOY, LIMITES)

    assert ticket is None
    assert venta.estado is EstadoDeVenta.PENDIENTE_DE_AUTORIZACION


def test_sale_of_one_cent_above_3000_is_held_for_authorization():
    """CP-10 · Límite · una pieza de $3,000.01: supera el monto por un centavo."""
    venta = venta_controlada("3000.01", piezas=1)

    ticket = venta.confirmar_cobro(HOY, LIMITES)

    assert ticket is None
    assert venta.estado is EstadoDeVenta.PENDIENTE_DE_AUTORIZACION


def test_held_sale_is_charged_after_pharmacist_authorizes():
    """CP-11 · Éxito · con autorización del Responsable la venta retenida se cobra."""
    venta = venta_controlada(100, piezas=11)
    assert venta.confirmar_cobro(HOY, LIMITES) is None
    autorizacion = Autorizacion(
        TipoDeAutorizacion.VENTA_CONTROLADA_EXCEDE_LIMITE,
        "dra.ruiz",
        Rol.RESPONSABLE_DE_FARMACIA,
        HOY,
    )

    venta.otorgar_autorizacion(autorizacion)
    ticket = venta.confirmar_cobro(HOY, LIMITES)

    assert ticket is not None
    assert venta.estado is EstadoDeVenta.COBRADA


def test_limit_only_counts_controlled_products():
    """CP-12 · Límite · 20 piezas de un producto SIN restricción no activan el límite."""
    paracetamol = Producto(Sku("PARACETAMOL-500"), "Paracetamol", Dinero.mxn(50), False, "PROV-A")
    venta = Venta(id=2, sucursal_id="SUC-01", cajero="cajero.ana", fecha=HOY)
    venta.agregar_producto(paracetamol, LOTE, cantidad=20)

    ticket = venta.confirmar_cobro(HOY, LIMITES)

    assert ticket is not None
    assert venta.estado is EstadoDeVenta.COBRADA


@pytest.mark.parametrize(
    ("piezas", "monto", "excede"),
    [
        (10, "3000.00", False),  # justo en ambos límites
        (11, "100.00", True),    # una pieza de más
        (1, "3000.01", True),    # un centavo de más
        (0, "0.00", False),
    ],
)
def test_limits_value_object_table(piezas, monto, excede):
    """Tabla de verdad del Value Object LimitesDeVentaControlada."""
    assert LIMITES.excede(piezas, Dinero.mxn(monto)) is excede
