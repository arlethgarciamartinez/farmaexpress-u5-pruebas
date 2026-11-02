"""Pruebas de arquitectura: la regla de dependencia (D de SOLID) se verifica, no se supone.
dominio  -> no importa aplicacion ni infraestructura
aplicacion -> no importa infraestructura"""
import ast
from pathlib import Path

import conftest  # noqa: F401  (agrega src/ al path)
import pytest

from farmaexpress.dominio.excepciones import EntidadNoEncontrada

RAIZ = Path(__file__).resolve().parents[1] / "src" / "farmaexpress"


def importaciones(carpeta: str) -> set[str]:
    modulos = set()
    for archivo in (RAIZ / carpeta).glob("*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom):
                base = nodo.module or ""
                modulos.add(("." * nodo.level) + base)
            elif isinstance(nodo, ast.Import):
                modulos.update(a.name for a in nodo.names)
    return modulos


def test_el_dominio_no_depende_de_aplicacion_ni_infraestructura():
    prohibidos = [m for m in importaciones("dominio")
                  if "aplicacion" in m or "infraestructura" in m or m.startswith("...")]
    assert prohibidos == []


def test_la_aplicacion_no_depende_de_infraestructura():
    assert [m for m in importaciones("aplicacion") if "infraestructura" in m] == []


def test_el_dominio_no_usa_sql_ni_frameworks():
    externos = {"sqlalchemy", "django", "flask", "sqlite3", "psycopg2"}
    assert externos.isdisjoint({m.split(".")[0] for m in importaciones("dominio")})


def test_los_repositorios_cumplen_el_mismo_contrato_cuando_no_existe_el_aggregate(app):
    from farmaexpress.infraestructura.memoria import UnidadDeTrabajoEnMemoria
    with UnidadDeTrabajoEnMemoria(app.almacen, app.bus) as uow:
        with pytest.raises(EntidadNoEncontrada):
            uow.ventas.obtener(999)
