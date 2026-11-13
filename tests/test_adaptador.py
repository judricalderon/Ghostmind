"""Pruebas del adaptador (T017), según contracts/adaptador.md."""

import pandas as pd
import pytest

from ghostmind.adaptador import (
    Adaptador,
    ErrorDelSistema,
    ObjetivoDesconocido,
    PresupuestoAgotado,
    resolver_objetivo,
)
from ghostmind.diccionario import SolicitudInvalida


def nuevo(registro, dic, objetivo="legacy", presupuesto=100):
    eid = registro.crear_ejecucion("descubrimiento", "prueba", semilla=1, presupuesto=presupuesto)
    return Adaptador(dic, objetivo, registro, eid, presupuesto), eid


def test_consulta_al_legacy_y_registra(registro, dic, solicitud_base):
    adaptador, eid = nuevo(registro, dic)
    assert adaptador.consultar(solicitud_base, ronda=0, origen="aleatorio") == "APROBADO"
    assert adaptador.consultar(dict(solicitud_base, edad=20), ronda=0, origen="limite") == "RECHAZADO"
    assert adaptador.consultas == 2
    assert adaptador.restantes == 98
    casos = registro.casos(eid)
    assert list(casos["decision"]) == ["APROBADO", "RECHAZADO"]
    assert list(casos["n_consulta"]) == [1, 2]
    assert casos.loc[1, "edad"] == 20


def test_solicitud_invalida_no_cuenta(registro, dic, solicitud_base):
    adaptador, eid = nuevo(registro, dic)
    with pytest.raises(SolicitudInvalida):
        adaptador.consultar(dict(solicitud_base, edad=200), ronda=0, origen="aleatorio")
    assert adaptador.consultas == 0
    assert registro.contar_casos(eid) == 0


def test_presupuesto_agotado(registro, dic, solicitud_base):
    adaptador, eid = nuevo(registro, dic, presupuesto=3)
    for edad in (30, 31, 32):
        adaptador.consultar(dict(solicitud_base, edad=edad), ronda=0, origen="aleatorio")
    with pytest.raises(PresupuestoAgotado):
        adaptador.consultar(dict(solicitud_base, edad=33), ronda=0, origen="aleatorio")
    assert adaptador.consultas == 3
    assert registro.contar_casos(eid) == 3


def test_sistema_que_falla(registro, dic, solicitud_base):
    def roto(registro_texto):
        raise RuntimeError("abend S0C7")

    adaptador, eid = nuevo(registro, dic, objetivo=roto)
    with pytest.raises(ErrorDelSistema):
        adaptador.consultar(solicitud_base, ronda=0, origen="aleatorio")
    assert adaptador.consultas == 1
    assert adaptador.errores == 1
    caso = registro.casos(eid).iloc[0]
    assert pd.isna(caso["decision"])
    assert "S0C7" in caso["error"]


def test_respuesta_inesperada(registro, dic, solicitud_base):
    adaptador, eid = nuevo(registro, dic, objetivo=lambda r: "QUIZAS")
    with pytest.raises(ErrorDelSistema):
        adaptador.consultar(solicitud_base, ronda=0, origen="aleatorio")
    assert registro.casos(eid).iloc[0]["error"].startswith("Respuesta inesperada")


def test_el_sistema_recibe_el_registro_de_ancho_fijo(registro, dic, solicitud_base):
    recibidos = []

    def espia(texto):
        recibidos.append(texto)
        return "APROBADO"

    adaptador, _ = nuevo(registro, dic, objetivo=espia)
    adaptador.consultar(solicitud_base, ronda=0, origen="aleatorio")
    assert recibidos == [dic.armar_registro(solicitud_base)]


def test_origen_invalido_no_consulta(registro, dic, solicitud_base):
    adaptador, eid = nuevo(registro, dic)
    with pytest.raises(ValueError):
        adaptador.consultar(solicitud_base, ronda=0, origen="corazonada")
    assert adaptador.consultas == 0


def test_resolver_objetivos():
    assert callable(resolver_objetivo("legacy"))
    with pytest.raises(ObjetivoDesconocido):
        resolver_objetivo("mainframe_del_vecino")


def test_consultas_coinciden_con_el_registro(registro, dic, solicitud_base):
    adaptador, eid = nuevo(registro, dic)
    for puntaje in range(380, 420):
        adaptador.consultar(dict(solicitud_base, puntaje_credito=puntaje), ronda=1, origen="biseccion")
    assert adaptador.consultas == registro.contar_casos(eid) == 40
