"""Proyectos con atributos propios (Fase 9, T063)."""

import json

import pytest

from ghostmind.proyectos import (
    PROYECTO_POR_DEFECTO,
    ProyectoDesconocido,
    cargar_proyectos,
    obtener_proyecto,
)


def test_proyectos_incluidos():
    proyectos = cargar_proyectos()
    assert list(proyectos) == ["credito", "seguros"]
    assert PROYECTO_POR_DEFECTO == "credito"
    assert all(p.nombre and p.descripcion for p in proyectos.values())


def test_credito_trae_legacy_y_modernizado():
    credito = obtener_proyecto()
    assert credito.clave == "credito"
    assert list(credito.cajas_negras) == ["legacy", "modernizado"]
    assert credito.cajas_negras["legacy"].punto_de_entrada == "legacy.crdapr01:CRDAPR01"
    assert all(c.descripcion for c in credito.cajas_negras.values())


def test_cada_proyecto_tiene_su_diccionario():
    credito = obtener_proyecto("credito").diccionario()
    seguros = obtener_proyecto("seguros").diccionario()
    assert credito.longitud_registro == 35 and seguros.longitud_registro == 30
    assert set(credito.nombres).isdisjoint(seguros.nombres)
    assert seguros.decisiones == ("PAGAR", "OBJETAR", "INVESTIGAR")


def test_base_de_cada_proyecto(tmp_path, monkeypatch):
    monkeypatch.setenv("GHOSTMIND_DB", str(tmp_path / "principal.sqlite"))
    assert obtener_proyecto("credito").ruta_base() == tmp_path / "principal.sqlite"
    assert obtener_proyecto("seguros").ruta_base() == tmp_path / "seguros.sqlite"


def test_proyecto_desconocido():
    with pytest.raises(ProyectoDesconocido):
        obtener_proyecto("nomina")


def escribir(tmp_path, datos):
    ruta = tmp_path / "proyectos.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return ruta


def proyecto_minimo(**extra):
    return {"nombre": "X", "descripcion": "", "diccionario": "diccionario_credito.json",
            "cajas_negras": {"legacy": "legacy.crdapr01:CRDAPR01"}, **extra}


def test_caja_negra_en_formato_corto(tmp_path):
    proyectos = cargar_proyectos(escribir(tmp_path, {"a": proyecto_minimo()}))
    caja = proyectos["a"].cajas_negras["legacy"]
    assert (caja.punto_de_entrada, caja.descripcion) == ("legacy.crdapr01:CRDAPR01", "")


@pytest.mark.parametrize("datos", [
    {},
    {"a": proyecto_minimo(), "b": proyecto_minimo()},  # dos proyectos en la base principal
    {"a": proyecto_minimo(base="x.sqlite"), "b": proyecto_minimo(base="x.sqlite")},
    {"a": proyecto_minimo(cajas_negras={})},
    {"a": proyecto_minimo(diccionario="no_existe.json")},
])
def test_proyectos_invalidos(tmp_path, datos):
    with pytest.raises(ValueError):
        cargar_proyectos(escribir(tmp_path, datos))
