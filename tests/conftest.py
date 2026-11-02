import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from farmaexpress.composicion import construir_aplicacion  # noqa: E402
from farmaexpress.dominio.inventario import InventarioDeProducto  # noqa: E402
from farmaexpress.dominio.lote import Lote  # noqa: E402
from farmaexpress.dominio.producto import Producto  # noqa: E402
from farmaexpress.dominio.valores import Dinero, NivelesDeInventario, NumeroDeLote, Sku  # noqa: E402

HOY = date(2026, 10, 12)
SUC1, SUC2 = "SUC-01", "SUC-02"
PARA, IBU = Sku("PARACETAMOL-500"), Sku("IBUPROFENO-400")
CLON, CLON_GEN = Sku("CLONAZEPAM-2"), Sku("CLONAZEPAM-GEN-2")


def n(x):
    return NumeroDeLote(x)


@pytest.fixture
def app():
    app = construir_aplicacion(HOY)
    a = app.almacen
    productos = [
        Producto(PARA, "Paracetamol 500 mg", Dinero.mxn(50), False, "PROV-A", (IBU,)),
        Producto(IBU, "Ibuprofeno 400 mg", Dinero.mxn(60), False, "PROV-A"),
        Producto(CLON, "Clonazepam 2 mg", Dinero.mxn(400), True, "PROV-B", (CLON_GEN,)),
        Producto(CLON_GEN, "Clonazepam genérico 2 mg", Dinero.mxn(300), True, "PROV-B"),
    ]
    for p in productos:
        a.productos[p.sku] = p
    lotes = [
        Lote(PARA, n("P-1"), HOY + timedelta(days=200)),
        Lote(IBU, n("I-1"), HOY + timedelta(days=200)),
        Lote(CLON, n("C-1"), HOY + timedelta(days=80)),
        Lote(CLON, n("C-2"), HOY + timedelta(days=20)),      # caduca antes (FEFO)
        Lote(CLON_GEN, n("G-1"), HOY + timedelta(days=100)),
    ]
    for l in lotes:
        a.lotes[(l.sku, l.numero)] = l
    inv = [
        InventarioDeProducto(SUC1, PARA, NivelesDeInventario(10, 50), {n("P-1"): 20}),
        InventarioDeProducto(SUC1, IBU, NivelesDeInventario(5, 40), {n("I-1"): 0}),
        InventarioDeProducto(SUC1, CLON, NivelesDeInventario(10, 50), {n("C-1"): 20, n("C-2"): 5}),
        InventarioDeProducto(SUC1, CLON_GEN, NivelesDeInventario(5, 30), {n("G-1"): 0}),
        InventarioDeProducto(SUC2, PARA, NivelesDeInventario(10, 50), {n("P-1"): 15}),
        InventarioDeProducto(SUC2, IBU, NivelesDeInventario(5, 40), {n("I-1"): 8}),
        InventarioDeProducto(SUC2, CLON_GEN, NivelesDeInventario(5, 30), {n("G-1"): 12}),
    ]
    for i in inv:
        a.inventarios[(i.sucursal_id, i.sku)] = i
    return app
