"""Pruebas de la versión modernizada y de las alteraciones (T041)."""

import ast
import itertools
from pathlib import Path

import pytest

from evaluacion.muestras import uniformes
from evaluacion.verdad import Verdad, cargar_alteraciones
from legacy.crdapr01 import CRDAPR01 as legacy
from legacy.crdapr_moderno import CRDAPR01 as moderno

RUTA_MODERNO = Path(__file__).resolve().parent.parent / "legacy" / "crdapr_moderno.py"
DECISIONES = {"APROBADO", "RECHAZADO", "REVISION_MANUAL"}


@pytest.fixture(scope="module")
def alteraciones():
    return cargar_alteraciones()


@pytest.fixture(scope="module")
def verdad():
    return Verdad.cargar()


@pytest.fixture(scope="module")
def verdad_moderna(verdad, alteraciones):
    return verdad.con_alteraciones(alteraciones)


def criticos(dic, *verdades):
    valores = {c.nombre: {c.minimo, c.maximo} for c in dic.numericos}
    for v in verdades:
        for regla in v.reglas:
            for campo, cond in regla.condiciones.items():
                if campo in valores:
                    if "min" in cond:
                        valores[campo] |= {cond["min"] - 1, cond["min"]}
                    if "max" in cond:
                        valores[campo] |= {cond["max"], cond["max"] + 1}
    for c in dic.numericos:
        valores[c.nombre] = sorted(x for x in valores[c.nombre] if c.minimo <= x <= c.maximo)
    for c in dic.categoricos:
        valores[c.nombre] = list(c.nombres_valores)
    return valores


def test_tres_alteraciones_documentadas(alteraciones):
    assert [(a["id"], a["regla"], a["tipo"]) for a in alteraciones] == [
        ("A1", "R01", "eliminar"),
        ("A2", "R04", "cambiar_condicion"),
        ("A3", "R05", "eliminar"),
    ]
    assert alteraciones[1]["nueva_condicion"] == {"puntaje_credito": {"max": 419}}


def test_con_alteraciones(verdad, verdad_moderna):
    assert [r.id for r in verdad_moderna.reglas] == ["R02", "R03", "R04", "R06", "R07", "R08", "R09", "R10"]
    assert verdad_moderna.regla("R04").condiciones == {"puntaje_credito": {"max": 419}}
    assert verdad.regla("R04").condiciones == {"puntaje_credito": {"max": 399}}  # el original no cambia


def test_moderno_no_depende_de_ghostmind_ni_de_la_evaluacion():
    arbol = ast.parse(RUTA_MODERNO.read_text(encoding="utf-8"))
    raices = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            raices.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            raices.add((nodo.module or "").split(".")[0])
    assert not raices & {"ghostmind", "evaluacion", "legacy"}


def test_registro_invalido():
    assert moderno("abc") not in DECISIONES
    assert moderno(None) not in DECISIONES


def test_moderno_coincide_con_las_reglas_alteradas(dic, verdad_moderna):
    for solicitud in uniformes(dic, 50_000, semilla=777):
        assert moderno(dic.armar_registro(solicitud)) == verdad_moderna.decision(solicitud), solicitud


def test_moderno_en_valores_criticos_y_atribucion(dic, verdad, verdad_moderna, alteraciones):
    valores = criticos(dic, verdad, verdad_moderna)
    nombres = list(dic.nombres)
    individuales = {a["id"]: verdad.con_alteraciones([a]) for a in alteraciones}
    diferencias = 0
    for combinacion in itertools.product(*(valores[n] for n in nombres)):
        solicitud = dict(zip(nombres, combinacion))
        registro = dic.armar_registro(solicitud)
        d_moderno = moderno(registro)
        assert d_moderno == verdad_moderna.decision(solicitud), solicitud
        if d_moderno != legacy(registro):
            diferencias += 1
            # Toda diferencia la explica al menos una alteración aplicada sola.
            assert any(v.decision(solicitud) != verdad.decision(solicitud) for v in individuales.values())
    assert diferencias > 0
