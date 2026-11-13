"""Pruebas del diccionario de campos y del registro de ancho fijo (T007)."""

import copy
import json

import pytest

from ghostmind.diccionario import RUTA_DICCIONARIO, Diccionario, SolicitudInvalida

NOMBRES = [
    "edad",
    "ingreso_mensual",
    "monto",
    "plazo_meses",
    "puntaje_credito",
    "antiguedad_meses",
    "tipo_empleo",
    "codigo_convenio",
]

EJEMPLO = {
    "edad": 35,
    "ingreso_mensual": 2_500_000,
    "monto": 30_000_000,
    "plazo_meses": 36,
    "puntaje_credito": 720,
    "antiguedad_meses": 96,
    "tipo_empleo": "EMPLEADO",
    "codigo_convenio": "C-12",
}


@pytest.fixture(scope="module")
def dic():
    return Diccionario.cargar()


def test_campos_y_decisiones(dic):
    assert [c.nombre for c in dic.campos] == NOMBRES
    assert dic.decisiones == ("APROBADO", "RECHAZADO", "REVISION_MANUAL")
    assert dic.longitud_registro == 35
    assert [c.nombre for c in dic.numericos] == NOMBRES[:6]
    assert [c.nombre for c in dic.categoricos] == NOMBRES[6:]


def test_rangos_y_valores(dic):
    for campo in dic.numericos:
        assert campo.minimo <= campo.maximo
        assert len(str(campo.maximo)) <= campo.longitud
    assert dic.campo("tipo_empleo").nombres_valores == (
        "EMPLEADO",
        "INDEPENDIENTE",
        "PENSIONADO",
        "DESEMPLEADO",
    )
    assert dic.campo("codigo_convenio").nombres_valores == ("NINGUNO", "C-12", "C-31", "C-45", "C-77")


def test_registro_cubre_35_posiciones_sin_traslape(dic):
    ocupadas = []
    for campo in dic.campos:
        ocupadas.extend(range(campo.inicio, campo.inicio + campo.longitud))
    assert sorted(ocupadas) == list(range(1, 36))


def test_codigos_caben_en_su_longitud(dic):
    for campo in dic.categoricos:
        for valor in campo.valores:
            assert len(valor.codigo) == campo.longitud


def test_ejemplo_del_contrato(dic):
    registro = dic.armar_registro(EJEMPLO)
    assert registro == "035002500000030000000036720096EC-12"
    assert dic.leer_registro(registro) == EJEMPLO


def test_convenio_ninguno_son_espacios(dic):
    solicitud = dict(EJEMPLO, codigo_convenio="NINGUNO", tipo_empleo="DESEMPLEADO")
    registro = dic.armar_registro(solicitud)
    assert registro.endswith("D    ")
    assert dic.leer_registro(registro) == solicitud


def test_valores_extremos(dic):
    minimos = {c.nombre: c.minimo for c in dic.numericos}
    maximos = {c.nombre: c.maximo for c in dic.numericos}
    for numericos in (minimos, maximos):
        solicitud = dict(numericos, tipo_empleo="PENSIONADO", codigo_convenio="C-77")
        registro = dic.armar_registro(solicitud)
        assert len(registro) == 35
        assert dic.leer_registro(registro) == solicitud


@pytest.mark.parametrize(
    "cambio",
    [
        {"edad": 17},
        {"edad": 81},
        {"monto": 150_000_001},
        {"ingreso_mensual": -1},
        {"edad": 35.5},
        {"edad": "35"},
        {"edad": True},
        {"tipo_empleo": "ESTUDIANTE"},
        {"codigo_convenio": "C-99"},
    ],
)
def test_solicitudes_invalidas(dic, cambio):
    with pytest.raises(SolicitudInvalida):
        dic.validar(dict(EJEMPLO, **cambio))


def test_campos_faltantes_o_sobrantes(dic):
    faltante = dict(EJEMPLO)
    del faltante["plazo_meses"]
    with pytest.raises(SolicitudInvalida):
        dic.validar(faltante)
    with pytest.raises(SolicitudInvalida):
        dic.validar(dict(EJEMPLO, color="rojo"))


def test_diccionario_con_traslape_se_rechaza():
    datos = json.loads(RUTA_DICCIONARIO.read_text(encoding="utf-8"))
    roto = copy.deepcopy(datos)
    roto["campos"][1]["inicio"] = 2
    with pytest.raises(ValueError):
        Diccionario.desde_dict(roto)


def test_diccionario_con_nombres_repetidos_se_rechaza():
    datos = json.loads(RUTA_DICCIONARIO.read_text(encoding="utf-8"))
    roto = copy.deepcopy(datos)
    roto["campos"][1]["nombre"] = "edad"
    with pytest.raises(ValueError):
        Diccionario.desde_dict(roto)
