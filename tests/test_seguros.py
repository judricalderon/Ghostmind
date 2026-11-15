"""Proyecto de demostración de seguros (Fase 9, T064).

El legacy simulado SINAUT01 debe coincidir con sus reglas plantadas, y GhostMind debe poder
descubrir sus reglas con el mismo motor que usa para crédito. Este proyecto no forma parte de las
métricas C1 a C5; la prueba de descubrimiento solo comprueba que el cambio de proyecto funciona.
"""

import itertools
from collections import Counter
from pathlib import Path

import pytest

from evaluacion.muestras import uniformes
from evaluacion.verdad import DEFECTO, Verdad
from ghostmind.adaptador import resolver_objetivo
from ghostmind.explorador import Explorador, Parametros
from ghostmind.proyectos import obtener_proyecto
from ghostmind.registro import Registro
from ghostmind.reglas import Caja
from legacy.sinaut01 import SINAUT01

RUTA_VERDAD = Path(__file__).resolve().parent.parent / "evaluacion" / "reglas_verdaderas_seguros.json"


@pytest.fixture(scope="module")
def proyecto():
    return obtener_proyecto("seguros")


@pytest.fixture(scope="module")
def dic(proyecto):
    return proyecto.diccionario()


@pytest.fixture(scope="module")
def verdad():
    return Verdad.cargar(RUTA_VERDAD)


def decidir(dic, solicitud):
    return SINAUT01(dic.armar_registro(solicitud))


def test_registro_de_30_posiciones(dic):
    solicitud = {"antiguedad_poliza": 400, "valor_reclamado": 12_500_000, "valor_asegurado": 60_000_000,
                 "dias_aviso": 5, "reclamos_previos": 1, "edad_conductor": 34,
                 "tipo_siniestro": "CHOQUE", "cobertura": "PLENA"}
    registro = dic.armar_registro(solicitud)
    assert registro == "0400" + "012500000" + "060000000" + "005" + "1" + "34" + "C" + "P"
    assert dic.leer_registro(registro) == solicitud
    assert SINAUT01(registro) == "PAGAR"


def test_registros_invalidos():
    numericos = "0400" + "012500000" + "060000000" + "005" + "1" + "34"
    assert SINAUT01(None) == "ERR-REG"
    assert SINAUT01("123") == "ERR-LON"
    assert SINAUT01("X" * 30) == "ERR-NUM"
    assert SINAUT01(numericos + "ZP") == "ERR-COD"
    assert SINAUT01(numericos + "CX") == "ERR-COD"


def test_legacy_coincide_con_las_reglas_plantadas(dic, verdad):
    decisiones = Counter()
    for solicitud in uniformes(dic, 20_000, 2026):
        esperado = verdad.decision(solicitud)
        assert decidir(dic, solicitud) == esperado, solicitud
        decisiones[esperado] += 1
    assert set(decisiones) == {"PAGAR", "OBJETAR", "INVESTIGAR"}


def test_legacy_coincide_en_los_bordes(dic, verdad):
    criticos = {c.nombre: {c.minimo, c.maximo} for c in dic.numericos}
    for regla in verdad.reglas:
        for campo, cond in regla.condiciones.items():
            if campo in criticos:
                for limite in (cond.get("min"), cond.get("max")):
                    if limite is not None:
                        criticos[campo] |= {limite - 1, limite, limite + 1}
    bases = iter(uniformes(dic, 5_000, 7))
    revisados = 0
    for campo in dic.numericos:
        valores = sorted(v for v in criticos[campo.nombre] if campo.minimo <= v <= campo.maximo)
        for valor, (tipo, cobertura) in itertools.product(
                valores, itertools.product(*(c.nombres_valores for c in dic.categoricos))):
            base = next(bases)
            solicitud = dict(base, **{campo.nombre: valor, "tipo_siniestro": tipo, "cobertura": cobertura})
            assert decidir(dic, solicitud) == verdad.decision(solicitud), solicitud
            revisados += 1
    assert revisados >= 200  # 29 valores críticos por 8 combinaciones de categorías


def test_cada_regla_plantada_decide_algun_caso(dic, verdad):
    reglas = Counter(verdad.evaluar(s)[1] for s in uniformes(dic, 50_000, 11))
    assert set(reglas) == {r.id for r in verdad.reglas} | {DEFECTO}


def test_cajas_negras_del_proyecto():
    assert resolver_objetivo("legacy", "seguros") is SINAUT01


@pytest.fixture(scope="module")
def descubrimiento(tmp_path_factory, dic):
    registro = Registro(tmp_path_factory.mktemp("seguros") / "seguros.sqlite", dic)
    resultado = Explorador(dic, registro, "legacy", 42, Parametros(), proyecto="seguros").descubrir()
    yield registro, resultado
    registro.cerrar()


def test_descubrimiento_sobre_seguros(dic, descubrimiento):
    registro, resultado = descubrimiento
    assert resultado.motivo == "estable"
    assert resultado.reglas
    assert {r.decision for r in resultado.reglas} == {"PAGAR", "OBJETAR", "INVESTIGAR"}
    reglas = registro.reglas(resultado.ejecucion_id)
    textos = " ".join(r["texto_negocio"] for r in reglas)
    assert "Se objeta la reclamación cuando" in textos
    assert "la solicitud" not in textos


def test_las_reglas_de_seguros_reproducen_el_legacy(dic, descubrimiento):
    """Concordancia en casos nuevos (no es C3: este proyecto no entra en las métricas)."""
    registro, resultado = descubrimiento
    cajas = [(Caja.desde_condiciones(dic, r["condiciones"]), r["decision"])
             for r in registro.reglas(resultado.ejecucion_id)]
    aciertos = 0
    solicitudes = uniformes(dic, 2_000, 20261115)
    for solicitud in solicitudes:
        predichas = [d for caja, d in cajas if caja.contiene(solicitud)]
        assert len(predichas) == 1, "las reglas deben cubrir el espacio sin traslaparse"
        aciertos += predichas[0] == decidir(dic, solicitud)
    assert aciertos / len(solicitudes) >= 0.95


def test_umbrales_confirmados_de_seguros(descubrimiento):
    registro, resultado = descubrimiento
    umbrales = registro.umbrales(resultado.ejecucion_id)
    confirmados = set(zip(umbrales["campo"], umbrales["valor_cambio"].astype(int)))
    assert ("dias_aviso", 91) in confirmados
    assert ("edad_conductor", 18) in confirmados
