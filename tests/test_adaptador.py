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


def test_listar_objetivos_con_descripcion():
    from ghostmind.adaptador import listar_objetivos

    objetivos = listar_objetivos()
    assert list(objetivos) == ["legacy", "modernizado"]
    assert all(descripcion for descripcion in objetivos.values())


def test_caja_negra_solo_con_punto_de_entrada(tmp_path):
    import json

    from ghostmind.adaptador import listar_objetivos

    ruta = tmp_path / "proyectos.json"
    ruta.write_text(json.dumps({"credito": {
        "nombre": "Crédito", "descripcion": "", "diccionario": "diccionario_credito.json",
        "cajas_negras": {"legacy": "legacy.crdapr01:CRDAPR01"}}}), encoding="utf-8")
    assert callable(resolver_objetivo("legacy", "credito", ruta))
    assert listar_objetivos("credito", ruta) == {"legacy": ""}


def test_cajas_negras_por_proyecto():
    from ghostmind.adaptador import listar_objetivos
    from ghostmind.proyectos import ProyectoDesconocido

    assert list(listar_objetivos("seguros")) == ["legacy"]
    assert resolver_objetivo("legacy", "seguros") is not resolver_objetivo("legacy", "credito")
    with pytest.raises(ObjetivoDesconocido):
        resolver_objetivo("modernizado", "seguros")
    with pytest.raises(ProyectoDesconocido):
        resolver_objetivo("legacy", "nomina")


def test_orden_objetivos(capsys):
    from ghostmind.__main__ import main

    assert main(["objetivos"]) == 0
    salida = capsys.readouterr().out
    assert "legacy" in salida and "modernizado" in salida
    assert main(["objetivos", "--proyecto", "seguros"]) == 0
    salida = capsys.readouterr().out
    assert "SINAUT01" in salida and "modernizado" not in salida


def test_orden_proyectos(capsys):
    from ghostmind.__main__ import main

    assert main(["proyectos"]) == 0
    salida = capsys.readouterr().out
    for texto in ("credito", "seguros", "Créditos (CRDAPR01)", "Seguros de auto (SINAUT01)",
                  "dias_aviso", "0 a 120 días", "PAGAR, OBJETAR, INVESTIGAR", "posiciones 23 a 25"):
        assert texto in salida, texto


def test_orden_con_proyecto_desconocido(capsys):
    from ghostmind.__main__ import main

    assert main(["descubrir", "--proyecto", "nomina"]) == 2
    assert "nomina" in capsys.readouterr().err


def test_descubrir_otro_proyecto_desde_la_terminal(tmp_path, capsys):
    from ghostmind.__main__ import main
    from ghostmind.proyectos import obtener_proyecto
    from ghostmind.registro import Registro

    ruta = tmp_path / "seguros.sqlite"
    assert main(["descubrir", "--proyecto", "seguros", "--objetivo", "legacy", "--presupuesto", "1500",
                 "--db", str(ruta)]) == 0
    salida = capsys.readouterr().out
    assert "ENTONCES" in salida and "PAGAR" in salida
    reg = Registro(ruta, obtener_proyecto("seguros").diccionario())
    assert [e["objetivo"] for e in reg.ejecuciones("descubrimiento")] == ["legacy"]
    reg.cerrar()
