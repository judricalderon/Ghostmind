"""Pruebas del legacy simulado contra las reglas verdaderas (T008 y T015)."""

import ast
import itertools
from collections import Counter
from pathlib import Path

import pytest

from evaluacion.muestras import uniformes
from evaluacion.verdad import DEFECTO, Verdad
from ghostmind.diccionario import Diccionario
from legacy.crdapr01 import CRDAPR01

RUTA_LEGACY = Path(__file__).resolve().parent.parent / "legacy" / "crdapr01.py"
DECISIONES = {"APROBADO", "RECHAZADO", "REVISION_MANUAL"}


@pytest.fixture(scope="module")
def dic():
    return Diccionario.cargar()


@pytest.fixture(scope="module")
def verdad():
    return Verdad.cargar()


def decidir_legacy(dic, solicitud):
    return CRDAPR01(dic.armar_registro(solicitud))


def valores_criticos(dic, verdad):
    """Bordes del dominio más los dos lados de cada umbral de las reglas verdaderas."""
    criticos = {c.nombre: {c.minimo, c.maximo} for c in dic.numericos}
    for regla in verdad.reglas:
        for campo, cond in regla.condiciones.items():
            if campo not in criticos:
                continue
            if "min" in cond:
                criticos[campo] |= {cond["min"] - 1, cond["min"]}
            if "max" in cond:
                criticos[campo] |= {cond["max"], cond["max"] + 1}
    for campo in dic.numericos:
        criticos[campo.nombre] = {v for v in criticos[campo.nombre] if campo.minimo <= v <= campo.maximo}
    for campo in dic.categoricos:
        criticos[campo.nombre] = set(campo.nombres_valores)
    return {nombre: sorted(valores) for nombre, valores in criticos.items()}


def test_legacy_no_depende_de_ghostmind_ni_de_la_evaluacion():
    arbol = ast.parse(RUTA_LEGACY.read_text(encoding="utf-8"))
    importados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            importados.add((nodo.module or "").split(".")[0])
    assert not importados & {"ghostmind", "evaluacion"}


def test_registro_invalido_no_es_una_decision():
    assert CRDAPR01("123") not in DECISIONES
    assert CRDAPR01(None) not in DECISIONES


def test_concordancia_en_50000_solicitudes_uniformes(dic, verdad):
    solicitudes = uniformes(dic, 50_000, semilla=12345)
    diferencias = []
    for solicitud in solicitudes:
        d_legacy = decidir_legacy(dic, solicitud)
        assert d_legacy in DECISIONES
        if d_legacy != verdad.decision(solicitud):
            diferencias.append(solicitud)
    assert diferencias == []


def test_concordancia_en_todos_los_valores_criticos(dic, verdad):
    criticos = valores_criticos(dic, verdad)
    nombres = [c.nombre for c in dic.campos]
    reglas_vistas = Counter()
    total = 0
    for combinacion in itertools.product(*(criticos[n] for n in nombres)):
        solicitud = dict(zip(nombres, combinacion))
        decision, regla = verdad.evaluar(solicitud)
        assert decidir_legacy(dic, solicitud) == decision, solicitud
        reglas_vistas[regla] += 1
        total += 1
    assert total > 100_000
    # Todas las reglas y el comportamiento por defecto aparecen en la grilla.
    assert set(reglas_vistas) == {f"R{i:02d}" for i in range(1, 11)} | {DEFECTO}


def test_fracciones_efectivas(dic, verdad):
    n = 200_000
    conteo = Counter(verdad.evaluar(s)[1] for s in uniformes(dic, n, semilla=2026))
    fracciones = {regla: conteo[regla] / n for regla in sorted(conteo)}
    print("\nFracción efectiva de cada regla (200.000 solicitudes uniformes, semilla 2026):")
    for regla, fraccion in fracciones.items():
        print(f"  {regla:8s} {fraccion * 100:7.3f} %")
    for i in range(1, 11):
        assert fracciones.get(f"R{i:02d}", 0) > 0
    assert fracciones["R03"] < 0.001
