"""Pruebas del evaluador declarativo de reglas verdaderas (T009)."""

import pytest

from evaluacion.verdad import DEFECTO, Verdad

BASE = {
    "edad": 35,
    "ingreso_mensual": 3_000_000,
    "monto": 20_000_000,
    "plazo_meses": 36,
    "puntaje_credito": 700,
    "antiguedad_meses": 50,
    "tipo_empleo": "EMPLEADO",
    "codigo_convenio": "NINGUNO",
}


@pytest.fixture(scope="module")
def verdad():
    return Verdad.cargar()


def caso(**cambios):
    return dict(BASE, **cambios)


def test_estructura(verdad):
    assert [r.id for r in verdad.reglas] == [f"R{i:02d}" for i in range(1, 11)]
    assert verdad.decision_por_defecto == "APROBADO"
    tipos = [r.tipo for r in verdad.reglas]
    assert tipos.count("fosil") == 1
    assert tipos.count("excepcion_rara") == 1
    assert tipos.count("excepcion") >= 2


@pytest.mark.parametrize(
    ("cambios", "esperado"),
    [
        ({}, ("APROBADO", DEFECTO)),
        # R01, la regla fósil, gana sobre todo lo demás
        ({"codigo_convenio": "C-77", "puntaje_credito": 200, "edad": 19}, ("APROBADO", "R01")),
        # R02
        ({"edad": 20}, ("RECHAZADO", "R02")),
        ({"edad": 21}, ("APROBADO", DEFECTO)),
        # R03, excepción rara, gana sobre el puntaje bajo
        ({"tipo_empleo": "INDEPENDIENTE", "codigo_convenio": "C-45", "monto": 48_000_000, "puntaje_credito": 200},
         ("REVISION_MANUAL", "R03")),
        ({"tipo_empleo": "INDEPENDIENTE", "codigo_convenio": "C-45", "monto": 50_000_000},
         ("REVISION_MANUAL", "R03")),
        ({"tipo_empleo": "INDEPENDIENTE", "codigo_convenio": "C-45", "monto": 47_999_999, "puntaje_credito": 200},
         ("RECHAZADO", "R04")),
        ({"tipo_empleo": "INDEPENDIENTE", "codigo_convenio": "C-45", "monto": 50_000_001},
         ("APROBADO", DEFECTO)),
        ({"tipo_empleo": "EMPLEADO", "codigo_convenio": "C-45", "monto": 49_000_000},
         ("APROBADO", DEFECTO)),
        # R04 y R10
        ({"puntaje_credito": 399}, ("RECHAZADO", "R04")),
        ({"puntaje_credito": 400}, ("REVISION_MANUAL", "R10")),
        ({"puntaje_credito": 549}, ("REVISION_MANUAL", "R10")),
        ({"puntaje_credito": 550}, ("APROBADO", DEFECTO)),
        # R05 es excepción de R06
        ({"tipo_empleo": "DESEMPLEADO", "antiguedad_meses": 120}, ("REVISION_MANUAL", "R05")),
        ({"tipo_empleo": "DESEMPLEADO", "antiguedad_meses": 119}, ("RECHAZADO", "R06")),
        # R07 con la libranza C-12 exenta
        ({"ingreso_mensual": 1_499_999}, ("RECHAZADO", "R07")),
        ({"ingreso_mensual": 1_499_999, "codigo_convenio": "C-12"}, ("APROBADO", DEFECTO)),
        ({"ingreso_mensual": 1_500_000}, ("APROBADO", DEFECTO)),
        # R08 es excepción de R09
        ({"monto": 80_000_001, "puntaje_credito": 800, "antiguedad_meses": 60}, ("APROBADO", "R08")),
        ({"monto": 80_000_001, "puntaje_credito": 799, "antiguedad_meses": 60}, ("REVISION_MANUAL", "R09")),
        ({"monto": 80_000_001, "puntaje_credito": 800, "antiguedad_meses": 59}, ("REVISION_MANUAL", "R09")),
        ({"monto": 80_000_000, "puntaje_credito": 500}, ("REVISION_MANUAL", "R10")),
        ({"monto": 80_000_000}, ("APROBADO", DEFECTO)),
    ],
)
def test_ejemplos_por_regla(verdad, cambios, esperado):
    assert verdad.evaluar(caso(**cambios)) == esperado


def test_precedencia_desempleado_antes_que_ingreso(verdad):
    # Un desempleado con ingreso bajo lo decide R06, no R07.
    assert verdad.evaluar(caso(tipo_empleo="DESEMPLEADO", ingreso_mensual=0)) == ("RECHAZADO", "R06")


def test_decision_coincide_con_evaluar(verdad):
    c = caso(puntaje_credito=450)
    assert verdad.decision(c) == verdad.evaluar(c)[0]
