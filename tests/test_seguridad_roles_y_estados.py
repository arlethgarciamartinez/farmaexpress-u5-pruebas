"""Seguridad de negocio (BN-10): quién puede autorizar y qué ventas ya no se pueden modificar."""
from datetime import date, timedelta
from itertools import product

import pytest

from farmaexpress.dominio.excepciones import (
    AutorizacionRequerida,
    RolSinPermiso,
    VentaNoModificable,
)
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
from farmaexpress.dominio.venta import Venta

HOY = date(2026, 10, 12)
LOTE = NumeroDeLote("L-1")
OTROS_ROLES = [rol for rol in Rol if rol is not Rol.RESPONSABLE_DE_FARMACIA]


@pytest.mark.parametrize("tipo", list(TipoDeAutorizacion))
def test_pharmacist_can_grant_every_type_of_authorization(tipo):
    """CP-20 · Éxito · el Responsable de farmacia puede otorgar cualquier tipo."""
    autorizacion = Autorizacion(tipo, "dra.ruiz", Rol.RESPONSABLE_DE_FARMACIA, HOY)

    assert autorizacion.rol is Rol.RESPONSABLE_DE_FARMACIA


@pytest.mark.parametrize(("rol", "tipo"), list(product(OTROS_ROLES, TipoDeAutorizacion)))
def test_any_other_role_cannot_grant_authorizations(rol, tipo):
    """CP-21 · Error · Cajero, Compras, Almacén y Gerencia (4 roles x 3 tipos = 12)."""
    with pytest.raises(RolSinPermiso):
        Autorizacion(tipo, "alguien", rol, HOY)


def producto(es_controlado: bool = False) -> Producto:
    return Producto(Sku("SKU-1"), "Producto", Dinero.mxn(50), es_controlado, "PROV-A")


def venta_cobrada() -> Venta:
    venta = Venta(id=1, sucursal_id="SUC-01", cajero="cajero.ana", fecha=HOY)
    venta.agregar_producto(producto(), LOTE, cantidad=1)
    venta.confirmar_cobro(HOY, LimitesDeVentaControlada())
    return venta


def venta_rechazada() -> Venta:
    venta = Venta(id=2, sucursal_id="SUC-01", cajero="cajero.ana", fecha=HOY)
    venta.rechazar("Receta vencida", HOY)
    return venta


@pytest.mark.parametrize("construir", [venta_cobrada, venta_rechazada])
def test_charged_or_rejected_sale_cannot_be_modified(construir):
    """CP-22 · Error · invariante I4: una venta cobrada o rechazada ya no cambia."""
    venta = construir()

    with pytest.raises(VentaNoModificable):
        venta.agregar_producto(producto(), LOTE, cantidad=1)
    with pytest.raises(VentaNoModificable):
        venta.registrar_receta(Receta("P", "M", "C", HOY - timedelta(days=1)))
    with pytest.raises(VentaNoModificable):
        venta.rechazar("otro motivo", HOY)


def test_substituting_a_controlled_product_requires_pharmacist_authorization():
    """CP-23 · Error · US-06: sin autorización no se sustituye un controlado."""
    solicitado = Producto(
        Sku("CLONAZEPAM-2"), "Clonazepam", Dinero.mxn(400), True, "PROV-B",
        (Sku("CLONAZEPAM-GEN-2"),),
    )
    sustituto = Producto(Sku("CLONAZEPAM-GEN-2"), "Genérico", Dinero.mxn(300), True, "PROV-B")
    venta = Venta(id=3, sucursal_id="SUC-01", cajero="cajero.ana", fecha=HOY)

    with pytest.raises(AutorizacionRequerida):
        venta.agregar_sustituto(solicitado, sustituto, LOTE, cantidad=1, autorizacion=None)

    assert venta.lineas == []
