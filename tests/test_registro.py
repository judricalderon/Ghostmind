"""Pruebas del registro de evidencia en SQLite (T018)."""

import sqlite3

import pytest

from ghostmind.registro import ORIGENES, Registro

TABLAS = {"ejecuciones", "casos", "umbrales", "rondas", "reglas", "regla_casos", "revisiones", "diferencias"}


def test_esquema_completo(registro):
    nombres = {
        fila[0]
        for fila in registro.con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert TABLAS <= nombres


def test_columnas_de_casos(registro, dic):
    columnas = [fila[1] for fila in registro.con.execute("PRAGMA table_info(casos)")]
    for esperada in ["ejecucion_id", "n_consulta", "ronda", "origen", "decision", "error", "caso_base_id", "momento"]:
        assert esperada in columnas
    for nombre in dic.nombres:
        assert nombre in columnas


def test_crear_y_cerrar_ejecucion(registro):
    eid = registro.crear_ejecucion("descubrimiento", "legacy", semilla=42, presupuesto=100,
                                   parametros={"muestreo": {"aleatorio": 400}})
    datos = registro.ejecucion(eid)
    assert datos["tipo"] == "descubrimiento"
    assert datos["semilla"] == 42
    assert datos["parametros"] == {"muestreo": {"aleatorio": 400}}
    assert datos["fin"] is None
    registro.cerrar_ejecucion(eid, consultas=7, rondas=2, motivo_parada="estable")
    datos = registro.ejecucion(eid)
    assert (datos["consultas"], datos["rondas"], datos["motivo_parada"]) == (7, 2, "estable")
    assert datos["fin"] is not None
    assert [e["id"] for e in registro.ejecuciones()] == [eid]


def test_tipo_y_motivo_validos(registro):
    with pytest.raises(ValueError):
        registro.crear_ejecucion("otra_cosa", "legacy", semilla=1, presupuesto=10)
    eid = registro.crear_ejecucion("descubrimiento", "legacy", semilla=1, presupuesto=10)
    with pytest.raises(ValueError):
        registro.cerrar_ejecucion(eid, consultas=0, rondas=0, motivo_parada="cansancio")


def test_guardar_y_leer_casos(registro, solicitud_base):
    eid = registro.crear_ejecucion("descubrimiento", "legacy", semilla=1, presupuesto=10)
    c1 = registro.guardar_caso(eid, 1, 0, "aleatorio", solicitud_base, "APROBADO")
    c2 = registro.guardar_caso(eid, 2, 0, "limite", dict(solicitud_base, edad=18), "RECHAZADO")
    c3 = registro.guardar_caso(eid, 3, 1, "biseccion", solicitud_base, None, error="fallo")
    assert c1 < c2 < c3
    tabla = registro.casos(eid)
    assert list(tabla["n_consulta"]) == [1, 2, 3]
    assert list(tabla["origen"]) == ["aleatorio", "limite", "biseccion"]
    assert tabla.loc[1, "edad"] == 18
    assert tabla.loc[2, "error"] == "fallo"
    assert registro.casos(eid, solo_validos=True).shape[0] == 2
    assert registro.contar_casos(eid) == 3


def test_origen_invalido(registro, solicitud_base):
    eid = registro.crear_ejecucion("descubrimiento", "legacy", semilla=1, presupuesto=10)
    with pytest.raises(ValueError):
        registro.guardar_caso(eid, 1, 0, "intuicion", solicitud_base, "APROBADO")
    assert "verificacion" in ORIGENES


def test_caso_requiere_ejecucion_existente(registro, solicitud_base):
    with pytest.raises(sqlite3.IntegrityError):
        registro.guardar_caso(999, 1, 0, "aleatorio", solicitud_base, "APROBADO")


def test_rondas(registro):
    eid = registro.crear_ejecucion("descubrimiento", "legacy", semilla=1, presupuesto=10)
    registro.guardar_ronda(eid, 0, consultas_acumuladas=720, reglas=12, contradicciones=0, umbrales_nuevos=0)
    registro.guardar_ronda(eid, 1, consultas_acumuladas=900, reglas=15, contradicciones=3, umbrales_nuevos=4)
    rondas = registro.rondas(eid)
    assert list(rondas["ronda"]) == [0, 1]
    assert list(rondas["contradicciones"]) == [0, 3]


def test_persistencia_entre_conexiones(tmp_path, solicitud_base):
    ruta = tmp_path / "persistente.sqlite"
    reg = Registro(ruta)
    eid = reg.crear_ejecucion("descubrimiento", "legacy", semilla=1, presupuesto=10)
    reg.guardar_caso(eid, 1, 0, "aleatorio", solicitud_base, "APROBADO")
    reg.cerrar()
    otro = Registro(ruta)
    assert otro.contar_casos(eid) == 1
    otro.cerrar()
