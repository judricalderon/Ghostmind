"""Utilidades compartidas por las pruebas."""

import pytest

from ghostmind.diccionario import Diccionario
from ghostmind.registro import Registro

BASE = {
    "edad": 35,
    "ingreso_mensual": 3_000_000,
    "monto": 20_000_000,
    "plazo_meses": 36,
    "puntaje_credito": 700,
    "antiguedad_meses": 50,
    "tipo_empleo": "EMPLEADO",
    "codigo_convenio": "NINGUNO",
}


@pytest.fixture(scope="session")
def dic():
    return Diccionario.cargar()


@pytest.fixture
def registro(tmp_path):
    reg = Registro(tmp_path / "prueba.sqlite")
    yield reg
    reg.cerrar()


@pytest.fixture
def solicitud_base():
    return dict(BASE)
