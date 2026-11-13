"""Pruebas de las métricas del experimento con casos construidos a mano (T048)."""

import numpy as np
import pandas as pd
import pytest

from evaluacion.metricas import (
    PredictorReglas,
    calcular_c1,
    calcular_c2,
    calcular_c3,
    calcular_c5,
    evaluar_regla_reportada,
    fidelidad_local,
)
from evaluacion.verdad import Verdad, cargar_alteraciones
from ghostmind.reglas import Caja


@pytest.fixture(scope="module")
def verdad():
    return Verdad.cargar()


def predictor_de(verdad, dic):
    """Predictor que decide como una Verdad dada (sirve de GhostMind perfecto o imperfecto)."""
    def predecir(tabla):
        return np.array([verdad.decision(f) for f in tabla[list(dic.nombres)].to_dict("records")])
    return predecir


def test_pureza_de_una_regla_exacta(dic, verdad):
    caja = (Caja.completa(dic).con_minimo("edad", 21).con_maximo("puntaje_credito", 399)
            .sin_valor("codigo_convenio", "C-77"))
    r = evaluar_regla_reportada(caja, "RECHAZADO", verdad, dic, np.random.default_rng(1), n=2000)
    assert r["pureza"] >= 0.99
    assert r["existe"]
    assert r["asociada"] == "R04"


def test_pureza_de_una_regla_mezclada(dic, verdad):
    caja = (Caja.completa(dic).con_minimo("edad", 21).con_maximo("puntaje_credito", 549)
            .sin_valor("codigo_convenio", "C-77"))
    r = evaluar_regla_reportada(caja, "RECHAZADO", verdad, dic, np.random.default_rng(1), n=2000)
    assert r["pureza"] < 0.95
    assert not r["existe"]


def test_asociacion_con_la_regla_fosil_y_el_defecto(dic, verdad):
    fosil = Caja.completa(dic).solo_valor("codigo_convenio", "C-77")
    assert evaluar_regla_reportada(fosil, "APROBADO", verdad, dic, np.random.default_rng(2))["asociada"] == "R01"
    defecto = (Caja.completa(dic).con_minimo("edad", 21).con_minimo("puntaje_credito", 550)
               .con_minimo("ingreso_mensual", 1_500_000).con_maximo("monto", 40_000_000)
               .sin_valor("tipo_empleo", "DESEMPLEADO").sin_valor("codigo_convenio", "C-77"))
    r = evaluar_regla_reportada(defecto, "APROBADO", verdad, dic, np.random.default_rng(2))
    assert r["existe"] and r["asociada"] == "DEFECTO"


def test_fidelidad_local_con_predictor_perfecto(dic, verdad):
    predecir = predictor_de(verdad, dic)
    for regla in verdad.reglas:
        assert fidelidad_local(regla, verdad, predecir, dic, np.random.default_rng(3), n=500) == 1.0


def test_fidelidad_local_sin_la_regla_rara(dic, verdad):
    sin_r03 = Verdad([r for r in verdad.reglas if r.id != "R03"], verdad.decision_por_defecto)
    valor = fidelidad_local(verdad.regla("R03"), verdad, predictor_de(sin_r03, dic), dic,
                            np.random.default_rng(4), n=500)
    assert valor < 0.9


def test_c1_cuenta_recuperadas(dic, verdad):
    # Reglas reportadas: una por regla plantada salvo R03, con su caja verdadera.
    reportadas = []
    for regla in verdad.reglas:
        if regla.id == "R03":
            continue
        reportadas.append({"codigo": regla.id, "existe": True, "asociada": regla.id})
    sin_r03 = Verdad([r for r in verdad.reglas if r.id != "R03"], verdad.decision_por_defecto)
    c1 = calcular_c1(verdad, reportadas, predictor_de(sin_r03, dic), dic, np.random.default_rng(5), n=500)
    assert c1["recuperadas"] == 9
    assert c1["valor"] == pytest.approx(0.9)
    assert [d["regla"] for d in c1["detalle"] if not d["recuperada"]] == ["R03"]


def test_c2():
    detalle = [{"existe": True}, {"existe": True}, {"existe": False}, {"existe": True}]
    c2 = calcular_c2(detalle)
    assert (c2["existen"], c2["reportadas"], c2["valor"]) == (3, 4, 0.75)


def test_c3_y_predictor_de_reglas(dic, verdad):
    from legacy.crdapr01 import CRDAPR01

    perfecto = calcular_c3(predictor_de(verdad, dic), dic, CRDAPR01, n=2000, semilla=9, registrados=set())
    assert perfecto["valor"] == 1.0
    siempre_aprueba = calcular_c3(lambda t: np.array(["APROBADO"] * len(t)), dic, CRDAPR01, n=2000, semilla=9,
                                  registrados=set())
    assert 0.25 < siempre_aprueba["valor"] < 0.5
    reglas = [{"condiciones": {"puntaje_credito": {"min": 150, "max": 399}}, "decision": "RECHAZADO"},
              {"condiciones": {"puntaje_credito": {"min": 400, "max": 950}}, "decision": "APROBADO"}]
    tabla = pd.DataFrame([{**{c.nombre: c.minimo for c in dic.numericos}, "tipo_empleo": "EMPLEADO",
                           "codigo_convenio": "NINGUNO", "puntaje_credito": p} for p in (399, 400)])
    assert list(PredictorReglas(reglas, dic)(tabla)) == ["RECHAZADO", "APROBADO"]


def test_c5_atribuye_diferencias(dic, verdad):
    alteraciones = cargar_alteraciones()
    base = {"edad": 35, "ingreso_mensual": 3_000_000, "monto": 20_000_000, "plazo_meses": 36,
            "antiguedad_meses": 50, "tipo_empleo": "EMPLEADO", "codigo_convenio": "NINGUNO"}
    solo_a2 = pd.DataFrame([dict(base, puntaje_credito=405), dict(base, puntaje_credito=419)])
    c5 = calcular_c5(solo_a2, verdad, alteraciones)
    assert c5["detectadas"] == 1
    assert c5["valor"] == pytest.approx(1 / 3)
    assert [d["alteracion"] for d in c5["detalle"] if d["detectada"]] == ["A2"]
    vacio = calcular_c5(solo_a2.iloc[0:0], verdad, alteraciones)
    assert vacio["detectadas"] == 0
