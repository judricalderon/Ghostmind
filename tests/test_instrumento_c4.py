"""Pruebas del instrumento de C4 con respuestas sintéticas (no son datos del experimento)."""

import csv
import json

import pytest

from evaluacion.instrumento_c4.generar import CARPETA, calcular_clave, cargar_preguntas, generar, solicitud_de
from evaluacion.instrumento_c4.puntuar import puntuar
from evaluacion.verdad import Verdad
from legacy.crdapr01 import CRDAPR01

LETRA = {"APROBADO": "A", "RECHAZADO": "B", "REVISION_MANUAL": "C"}


@pytest.fixture(scope="module")
def clave():
    return calcular_clave(cargar_preguntas(), Verdad.cargar())


def test_la_clave_coincide_con_el_legacy(dic, clave):
    definicion = cargar_preguntas()
    for p in definicion["preguntas"]:
        if p["tipo"] == "decision":
            assert CRDAPR01(dic.armar_registro(solicitud_de(definicion, p))) == clave[p["id"]]["respuesta"]
    assert clave["P9"]["respuesta"] == "NO"  # el plazo no participa en ninguna regla
    assert len({c["regla"] for c in clave.values() if c["regla"]}) >= 8  # cubre reglas distintas


def test_archivos_versionados_estan_al_dia(clave):
    guardada = json.loads((CARPETA / "clave.json").read_text(encoding="utf-8"))
    assert guardada == clave
    encabezado = (CARPETA / "plantilla_respuestas.csv").read_text(encoding="utf-8").strip().split(",")
    assert encabezado[:3] == ["participante", "perfil", "P1"] and encabezado[-1] == "comentario"
    assert "P10" in (CARPETA / "cuestionario.md").read_text(encoding="utf-8")


def escribir(tmp_path, filas):
    ruta = tmp_path / "respuestas.csv"
    encabezado = (CARPETA / "plantilla_respuestas.csv").read_text(encoding="utf-8").strip().split(",")
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=encabezado)
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta


def respuestas_correctas(clave):
    return {p: (LETRA[c["respuesta"]] if c["respuesta"] in LETRA else c["respuesta"].capitalize().replace("Si", "Sí"))
            for p, c in clave.items()}


def test_puntuacion(tmp_path, clave):
    perfectas = respuestas_correctas(clave)
    mitad = {p: ("A" if i % 2 else v) for i, (p, v) in enumerate(perfectas.items())}
    filas = [
        {"participante": "S1", "perfil": "sintético", **perfectas, "U1": 5, "U2": 4, "U3": 4, "comentario": ""},
        {"participante": "S2", "perfil": "sintético", **mitad, "U1": 3, "U2": 3, "U3": 2, "comentario": ""},
    ]
    resultado = puntuar(escribir(tmp_path, filas), clave)
    assert resultado["participantes"] == 2
    assert resultado["detalle"][0]["correctas"] == len(clave)
    assert resultado["utilidad_promedio"] == 4.0
    esperado = (len(clave) + resultado["detalle"][1]["correctas"]) / (2 * len(clave))
    assert resultado["proporcion_correctas"] == pytest.approx(esperado)
    assert resultado["cumple"] == (esperado >= 2 / 3)


def test_valoracion_fuera_de_rango(tmp_path, clave):
    fila = {"participante": "S1", "perfil": "", **respuestas_correctas(clave), "U1": 7, "U2": "", "U3": "",
            "comentario": ""}
    with pytest.raises(ValueError):
        puntuar(escribir(tmp_path, [fila]), clave)


def test_generar_en_otra_carpeta(tmp_path):
    clave = generar(tmp_path)
    assert (tmp_path / "cuestionario.md").exists() and (tmp_path / "clave.json").exists()
    assert len(clave) == 10
