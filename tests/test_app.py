"""Pruebas de la interfaz del catálogo con streamlit.testing (T035)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from apoyo import ejecucion_pequena
from ghostmind.registro import Registro

APP = str(Path(__file__).resolve().parent.parent / "app" / "catalogo.py")


def abrir_app():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


@pytest.fixture
def base_con_ejecucion(tmp_path, monkeypatch, dic):
    ruta = tmp_path / "app.sqlite"
    reg = Registro(ruta, dic)
    resultado = ejecucion_pequena(dic, reg)
    reg.cerrar()
    monkeypatch.setenv("GHOSTMIND_DB", str(ruta))
    monkeypatch.delenv("GHOSTMIND_LLM", raising=False)
    return ruta, resultado


def test_sin_ejecuciones_muestra_ayuda(tmp_path, monkeypatch):
    monkeypatch.setenv("GHOSTMIND_DB", str(tmp_path / "vacia.sqlite"))
    at = abrir_app()
    textos = " ".join(str(e.value) for e in at.info)
    assert "python -m ghostmind descubrir" in textos


def test_lista_de_reglas_y_filtros(base_con_ejecucion):
    _, resultado = base_con_ejecucion
    at = abrir_app()
    tabla = at.dataframe[0].value
    assert list(tabla["Código"]) == [r.codigo for r in resultado.reglas]
    at.multiselect(key="filtro_decision").set_value(["RECHAZADO"]).run()
    tabla = at.dataframe[0].value
    assert set(tabla["Decisión"]) == {"RECHAZADO"}


def test_validar_y_rechazar_desde_la_interfaz(base_con_ejecucion, dic):
    ruta, resultado = base_con_ejecucion
    at = abrir_app()
    codigo = resultado.reglas[0].codigo
    at.selectbox(key="regla").select(codigo).run()
    at.text_area(key="nota").input("Revisada con el área de crédito").run()
    at.button(key="aprobar").click().run()
    assert not at.exception
    reg = Registro(ruta, dic)
    regla = next(r for r in reg.reglas(resultado.ejecucion_id) if r["codigo"] == codigo)
    assert regla["estado"] == "validada"
    at.button(key="rechazar").click().run()
    regla = next(r for r in reg.reglas(resultado.ejecucion_id) if r["codigo"] == codigo)
    assert regla["estado"] == "rechazada"
    reg.cerrar()


def test_boton_de_exportar(base_con_ejecucion):
    at = abrir_app()
    descargas = [e for e in at.get("download_button")]
    assert descargas, "falta el botón de exportar"


def test_verificacion_desde_la_interfaz(base_con_ejecucion, dic):
    ruta, resultado = base_con_ejecucion
    at = abrir_app()
    assert any("Todavía no hay verificaciones" in str(e.value) for e in at.info)
    at.button(key="verificar").click().run()
    assert not at.exception, at.exception
    reg = Registro(ruta, dic)
    verificaciones = reg.ejecuciones("verificacion")
    assert len(verificaciones) == 1
    assert verificaciones[0]["ejecucion_base_id"] == resultado.ejecucion_id
    assert verificaciones[0]["objetivo"] == "modernizado"
    reg.cerrar()
    tablas = [d.value for d in at.dataframe if "Diferencias" in d.value.columns]
    assert tablas and tablas[0]["Diferencias"].sum() > 0
