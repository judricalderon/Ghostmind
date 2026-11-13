"""Pruebas de revisiones del especialista y exportación del catálogo (T034, T040)."""

import json

import pytest

from apoyo import ejecucion_pequena
from ghostmind.__main__ import main
from ghostmind.catalogo import exportar, exportar_json, historial, revisar
from ghostmind.registro import Registro


@pytest.fixture
def ejecucion(dic, registro):
    return ejecucion_pequena(dic, registro)


def test_validar_y_rechazar_con_historial(registro, ejecucion):
    regla = registro.reglas(ejecucion.ejecucion_id)[0]
    revisar(registro, regla["id"], "validada", "Coincide con la política de score")
    assert registro.regla(regla["id"])["estado"] == "validada"
    revisar(registro, regla["id"], "rechazada")
    assert registro.regla(regla["id"])["estado"] == "rechazada"
    pasos = historial(registro, regla["id"])
    assert [p["decision"] for p in pasos] == ["validada", "rechazada"]
    assert pasos[0]["nota"] == "Coincide con la política de score"
    assert all(p["momento"] for p in pasos)


def test_solo_el_especialista_valida_o_rechaza(registro, ejecucion):
    regla = registro.reglas(ejecucion.ejecucion_id)[0]
    with pytest.raises(ValueError):
        revisar(registro, regla["id"], "corroborada")
    with pytest.raises(KeyError):
        revisar(registro, 99_999, "validada")


def test_las_revisiones_persisten(tmp_path, dic):
    ruta = tmp_path / "persistencia.sqlite"
    reg = Registro(ruta, dic)
    resultado = ejecucion_pequena(dic, reg)
    regla_id = reg.reglas(resultado.ejecucion_id)[1]["id"]
    revisar(reg, regla_id, "validada", "ok")
    reg.cerrar()
    otro = Registro(ruta, dic)
    assert otro.regla(regla_id)["estado"] == "validada"
    assert len(historial(otro, regla_id)) == 1
    otro.cerrar()


def test_exportacion_cumple_el_contrato(registro, ejecucion):
    regla_id = registro.reglas(ejecucion.ejecucion_id)[0]["id"]
    revisar(registro, regla_id, "validada", "ok")
    catalogo = exportar(registro, ejecucion.ejecucion_id)
    assert catalogo["formato"] == "ghostmind-catalogo/1"
    assert catalogo["generado"]
    assert catalogo["ejecucion"]["id"] == ejecucion.ejecucion_id
    assert catalogo["ejecucion"]["consultas"] == ejecucion.consultas
    for clave in ("objetivo", "semilla", "presupuesto", "rondas", "motivo_parada", "version"):
        assert clave in catalogo["ejecucion"]
    codigos = [r["codigo"] for r in catalogo["reglas"]]
    assert codigos == sorted(codigos)
    for r in catalogo["reglas"]:
        assert set(r) == {
            "codigo", "decision", "condiciones", "umbrales_confirmados", "respaldo", "contraejemplos",
            "confianza", "estado", "texto_tecnico", "texto_negocio", "texto_llm", "revisiones",
        }
        assert 0 <= r["confianza"] <= 1
        assert r["estado"] in {"hipotesis", "corroborada", "validada", "rechazada"}
    primera = next(r for r in catalogo["reglas"] if r["revisiones"])
    assert primera["estado"] == "validada"
    assert primera["revisiones"][0]["nota"] == "ok"
    json.dumps(catalogo, ensure_ascii=False)  # serializable


def test_exportar_json_y_orden_cli(tmp_path, dic):
    ruta_db = tmp_path / "cli.sqlite"
    reg = Registro(ruta_db, dic)
    resultado = ejecucion_pequena(dic, reg)
    archivo = exportar_json(reg, resultado.ejecucion_id, tmp_path / "catalogo.json")
    reg.cerrar()
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    assert len(datos["reglas"]) == len(resultado.reglas)
    salida = tmp_path / "desde_cli.json"
    assert main(["exportar", "--ejecucion", str(resultado.ejecucion_id), "--salida", str(salida),
                 "--db", str(ruta_db)]) == 0
    assert json.loads(salida.read_text(encoding="utf-8"))["reglas"] == datos["reglas"]
