"""Pruebas de cajas, reglas, confianza, estados y redacción (T024)."""

import numpy as np
import pandas as pd
import pytest

from ghostmind.reglas import Caja, Regla, confianza_wilson, estado_automatico, umbral_a_entero


def caja_ejemplo(dic):
    return (
        Caja.completa(dic)
        .con_minimo("edad", 21)
        .con_maximo("puntaje_credito", 399)
        .sin_valor("codigo_convenio", "C-77")
    )


@pytest.mark.parametrize(
    ("umbral", "lado", "esperado"),
    [(399.5, "izquierda", ("max", 399)), (399.5, "derecha", ("min", 400)),
     (80000000.5, "derecha", ("min", 80000001)), (20.5, "izquierda", ("max", 20))],
)
def test_umbral_a_entero(umbral, lado, esperado):
    assert umbral_a_entero(umbral, lado) == esperado


@pytest.mark.parametrize(
    ("respaldo", "contra", "esperado"),
    [(10, 0, 0.7225), (30, 0, 0.8865), (100, 0, 0.9630), (100, 2, 0.9313), (0, 0, 0.0)],
)
def test_confianza_wilson(respaldo, contra, esperado):
    assert confianza_wilson(respaldo, contra) == pytest.approx(esperado, abs=5e-4)


def test_confianza_crece_con_respaldo_y_baja_con_contraejemplos():
    assert confianza_wilson(50, 0) > confianza_wilson(20, 0)
    assert confianza_wilson(50, 1) < confianza_wilson(50, 0)


def test_estado_automatico():
    assert estado_automatico(30, 0, 20) == "corroborada"
    assert estado_automatico(29, 0, 20) == "hipotesis"
    assert estado_automatico(100, 1, 50) == "hipotesis"
    assert estado_automatico(100, 0, 19) == "hipotesis"


def test_caja_completa_contiene_todo(dic, solicitud_base):
    caja = Caja.completa(dic)
    assert caja.contiene(solicitud_base)
    assert caja.condiciones() == {}
    assert not caja.vacia


def test_caja_restringida(dic, solicitud_base):
    caja = caja_ejemplo(dic)
    assert caja.contiene(dict(solicitud_base, puntaje_credito=399))
    assert not caja.contiene(dict(solicitud_base, puntaje_credito=400))
    assert not caja.contiene(dict(solicitud_base, edad=20, puntaje_credito=300))
    assert not caja.contiene(dict(solicitud_base, codigo_convenio="C-77", puntaje_credito=300))
    assert caja.condiciones() == {
        "edad": {"min": 21, "max": 80},
        "puntaje_credito": {"min": 150, "max": 399},
        "codigo_convenio": {"valores": ["NINGUNO", "C-12", "C-31", "C-45"]},
    }


def test_caja_vacia(dic):
    assert Caja.completa(dic).con_maximo("edad", 30).con_minimo("edad", 31).vacia
    caja = Caja.completa(dic).solo_valor("tipo_empleo", "EMPLEADO").sin_valor("tipo_empleo", "EMPLEADO")
    assert caja.vacia


def test_caja_ida_y_vuelta_por_condiciones(dic):
    caja = caja_ejemplo(dic)
    assert Caja.desde_condiciones(dic, caja.condiciones()) == caja
    assert hash(Caja.desde_condiciones(dic, caja.condiciones())) == hash(caja)


def test_mascara_vectorizada(dic, solicitud_base):
    caja = caja_ejemplo(dic)
    filas = [dict(solicitud_base, puntaje_credito=p) for p in (300, 399, 400, 700)]
    filas.append(dict(solicitud_base, puntaje_credito=300, codigo_convenio="C-77"))
    tabla = pd.DataFrame(filas)
    assert caja.mascara(tabla).tolist() == [True, True, False, False, False]


def test_muestrear_queda_dentro_de_la_caja(dic):
    caja = caja_ejemplo(dic).con_minimo("monto", 48_000_000).con_maximo("monto", 50_000_000)
    rng = np.random.default_rng(0)
    for _ in range(300):
        solicitud = caja.muestrear(rng)
        dic.validar(solicitud)
        assert caja.contiene(solicitud)


def test_redaccion_tecnica_y_de_negocio(dic):
    regla = Regla(codigo="GM-01", caja=caja_ejemplo(dic), decision="RECHAZADO")
    assert regla.texto_tecnico() == (
        "SI edad >= 21 Y puntaje_credito <= 399 Y codigo_convenio != C-77 ENTONCES RECHAZADO"
    )
    assert regla.texto_negocio() == (
        "Se rechaza la solicitud cuando la edad es de 21 años o más, el puntaje de crédito es de "
        "399 puntos o menos y el código de convenio no es C-77."
    )


def test_redaccion_de_intervalos_y_categorias(dic):
    caja = (
        Caja.completa(dic)
        .con_minimo("monto", 48_000_000)
        .con_maximo("monto", 50_000_000)
        .solo_valor("tipo_empleo", "INDEPENDIENTE")
    )
    regla = Regla(codigo="GM-02", caja=caja, decision="REVISION_MANUAL")
    assert regla.texto_tecnico() == (
        "SI 48000000 <= monto <= 50000000 Y tipo_empleo = INDEPENDIENTE ENTONCES REVISION_MANUAL"
    )
    assert regla.texto_negocio() == (
        "La solicitud pasa a revisión manual cuando el monto solicitado está entre 48.000.000 y "
        "50.000.000 pesos y el tipo de empleo es independiente."
    )
    dos = Caja.completa(dic).solo_valores("codigo_convenio", ["C-12", "C-31"])
    assert Regla("GM-03", dos, "APROBADO").texto_negocio() == (
        "Se aprueba la solicitud cuando el código de convenio es C-12 o C-31."
    )
    assert Regla("GM-03", dos, "APROBADO").texto_tecnico() == (
        "SI codigo_convenio EN {C-12, C-31} ENTONCES APROBADO"
    )


def test_redaccion_sin_condiciones(dic):
    regla = Regla("GM-09", Caja.completa(dic), "APROBADO")
    assert regla.texto_tecnico() == "SI cualquier solicitud ENTONCES APROBADO"
    assert regla.texto_negocio() == "Se aprueba cualquier solicitud."


def test_confianza_y_estado_de_una_regla(dic):
    regla = Regla("GM-01", caja_ejemplo(dic), "RECHAZADO", respaldo=100, contraejemplos=0,
                  consultas_prueba=25)
    assert regla.confianza == pytest.approx(0.963, abs=1e-3)
    regla.actualizar_estado()
    assert regla.estado == "corroborada"
