"""Genera matriz_casos_pruebas.csv desde los docstrings 'CP-NN · Tipo · descripción'."""
import ast
import csv
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PATRON = re.compile(r"^(CP-\d+)\s*·\s*([^·]+?)\s*·\s*(.+)$", re.S)
CLASIFICACION = {
    "test_regla_receta_vigente": ("R1 Receta vigente", "Dominio"),
    "test_regla_limite_venta_controlada": ("R2 Límite de venta controlada", "Dominio"),
    "test_regla_lote_vendible": ("R3 Lote vendible", "Dominio"),
    "test_seguridad_roles_y_estados": ("BN-10 Roles y estados", "Dominio (seguridad)"),
    "test_persistencia_sqlite": ("Persistencia de lotes", "Integración SQLite"),
    "test_notificador_almacen_mock": ("Notificación a Almacén", "Mock de servicio externo"),
}


def ejecutar_pytest() -> set[tuple[str, str]]:
    xml = RAIZ / ".resultado_pytest.xml"
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", f"--junitxml={xml}"], cwd=RAIZ, check=False
    )
    fallidas = set()
    for caso in ET.parse(xml).getroot().iter("testcase"):
        if caso.find("failure") is not None or caso.find("error") is not None:
            modulo = caso.get("classname", "").split(".")[-1]
            fallidas.add((modulo, caso.get("name", "").split("[")[0]))
    xml.unlink()
    return fallidas


def recolectar():
    for archivo in sorted((RAIZ / "tests").glob("test_*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8-sig"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
                coincide = PATRON.match((ast.get_docstring(nodo) or "").strip())
                if coincide:
                    yield coincide, archivo.stem, nodo.name


def main():
    fallidas = ejecutar_pytest()
    filas = []
    for m, modulo, funcion in recolectar():
        regla, capa = CLASIFICACION.get(modulo, ("", ""))
        filas.append({
            "id": m.group(1),
            "regla": regla,
            "descripcion": " ".join(m.group(3).split()),
            "tipo": m.group(2).strip(),
            "capa": capa,
            "prueba": f"tests/{modulo}.py::{funcion}",
            "estado": "FALLA" if (modulo, funcion) in fallidas else "PASA",
        })
    filas.sort(key=lambda f: int(f["id"].split("-")[1]))
    salida = RAIZ / "matriz_casos_pruebas.csv"
    with salida.open("w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"\n{len(filas)} casos escritos en {salida.name}")
    print(dict(Counter(f["tipo"] for f in filas)))


if __name__ == "__main__":
    main()
