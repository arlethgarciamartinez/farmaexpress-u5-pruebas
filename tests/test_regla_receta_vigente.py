"""Regla 1 (BN-01, US-02/US-03, invariante I1): un medicamento controlado solo se cobra
con receta completa y vigente (<= 30 días). Pruebas unitarias del dominio: sin BD, sin red."""
from datetime import date, timedelta

import pytest

from farmaexpress.dominio.excepciones import (
    RecetaIncompleta,
    RecetaRequerida,
    RecetaVencida,
)
from farmaexpress.dominio.producto import Producto
from farmaexpress.dominio.valores import (
    Dinero,
    LimitesDeVentaControlada,
    NumeroDeLote,
    Receta,
    Sku,
)
from farmaexpress.dominio.venta import EstadoDeVenta, Venta

HOY = date(2026, 10, 12)  # fecha fija: resultados reproducibles
LOTE = NumeroDeLote("C-1")


def clonazepam() -> Producto:
    return Producto(Sku("CLONAZEPAM-2"), "Clonazepam 2 mg", Dinero.mxn(400), True, "PROV-B")


def paracetamol() -> Producto:
    return Producto(Sku("PARACETAMOL-500"), "Paracetamol 500 mg", Dinero.mxn(50), False, "PROV-A")


def receta_de(dias_de_antiguedad: int, medico: str = "Dr. Pérez") -> Receta:
    return Receta("Juan López", medico, "CED-123", HOY - timedelta(days=dias_de_antiguedad))


def venta_con(producto: Producto, receta: Receta | None = None) -> Venta:
    venta = Venta(id=1, sucursal_id="SUC-01", cajero="cajero.ana", fecha=HOY)
    venta.agregar_producto(producto, LOTE, cantidad=1)
    if receta is not None:
        venta.registrar_receta(receta)
    return venta


def test_controlled_sale_with_recent_prescription_is_charged():
    """CP-01 · Éxito · receta de 10 días: se cobra y se emite ticket."""
    # Arrange
    venta = venta_con(clonazepam(), receta_de(10))

    # Act
    ticket = venta.confirmar_cobro(HOY, LimitesDeVentaControlada())

    # Assert
    assert ticket is not None
    assert ticket.total == Dinero.mxn(400)
    assert venta.estado is EstadoDeVenta.COBRADA


def test_prescription_of_exactly_30_days_is_still_valid():
    """CP-02 · Límite · 30 días exactos todavía es vigente (US-03 dice 'supera' los 30)."""
    venta = venta_con(clonazepam(), receta_de(30))

    ticket = venta.confirmar_cobro(HOY, LimitesDeVentaControlada())

    assert ticket is not None
    assert venta.estado is EstadoDeVenta.COBRADA


def test_prescription_of_31_days_is_rejected_and_sale_is_not_charged():
    """CP-03 · Límite/Error · 31 días: receta vencida, la venta no se cobra."""
    venta = venta_con(clonazepam(), receta_de(31))

    with pytest.raises(RecetaVencida):
        venta.confirmar_cobro(HOY, LimitesDeVentaControlada())

    assert venta.estado is EstadoDeVenta.EN_CAPTURA
    assert venta.ticket is None


def test_controlled_sale_without_prescription_is_rejected():
    """CP-04 · Error · sin receta no hay venta de controlados (restricción del BRD)."""
    venta = venta_con(clonazepam(), receta=None)

    with pytest.raises(RecetaRequerida):
        venta.confirmar_cobro(HOY, LimitesDeVentaControlada())

    assert venta.ticket is None


def test_incomplete_prescription_reports_the_missing_field():
    """CP-05 · Error · receta sin médico: se indica qué falta."""
    venta = venta_con(clonazepam(), receta_de(3, medico=""))

    with pytest.raises(RecetaIncompleta, match="médico"):
        venta.confirmar_cobro(HOY, LimitesDeVentaControlada())


def test_non_controlled_product_does_not_need_prescription():
    """CP-06 · Éxito · un producto sin restricción se cobra sin receta (US-01)."""
    venta = venta_con(paracetamol(), receta=None)

    ticket = venta.confirmar_cobro(HOY, LimitesDeVentaControlada())

    assert ticket is not None
    assert ticket.total == Dinero.mxn(50)
