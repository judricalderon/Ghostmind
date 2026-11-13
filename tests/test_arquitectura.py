"""Caja negra estricta (constitución, principio I; T016).

GhostMind no puede importar el legacy ni la evaluación, ni mencionar sus archivos, y solo el
adaptador puede resolver puntos de entrada de sistemas.
"""

import ast
import re
from pathlib import Path

import pytest

PAQUETE = Path(__file__).resolve().parent.parent / "ghostmind"
ARCHIVOS = sorted(PAQUETE.rglob("*.py"))

PROHIBIDOS_EN_TEXTO = [
    re.compile(r"reglas_verdaderas", re.IGNORECASE),
    re.compile(r"alteraciones\.json", re.IGNORECASE),
    re.compile(r"crdapr", re.IGNORECASE),
    re.compile(r"\bevaluacion\b", re.IGNORECASE),
    re.compile(r"\blegacy[./\\][a-z_]", re.IGNORECASE),
]


def modulos_importados(arbol: ast.AST) -> set[str]:
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module)
    return nombres


def test_hay_archivos_que_revisar():
    assert any(a.name == "adaptador.py" for a in ARCHIVOS)


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda a: a.name)
def test_no_importa_legacy_ni_evaluacion(archivo):
    importados = modulos_importados(ast.parse(archivo.read_text(encoding="utf-8")))
    raices = {m.split(".")[0] for m in importados}
    assert not raices & {"legacy", "evaluacion"}, f"{archivo.name} importa {raices}"


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda a: a.name)
def test_no_menciona_archivos_del_legacy_ni_de_la_evaluacion(archivo):
    texto = archivo.read_text(encoding="utf-8")
    for patron in PROHIBIDOS_EN_TEXTO:
        assert not patron.search(texto), f"{archivo.name} menciona {patron.pattern}"


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda a: a.name)
def test_solo_el_adaptador_resuelve_puntos_de_entrada(archivo):
    if archivo.name == "adaptador.py":
        return
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    assert "importlib" not in {m.split(".")[0] for m in modulos_importados(arbol)}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Name):
            assert nodo.id not in {"__import__", "import_module"}, archivo.name
        if isinstance(nodo, ast.Attribute):
            assert nodo.attr != "import_module", archivo.name
