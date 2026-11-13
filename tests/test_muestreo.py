"""Pruebas del muestreo inicial (T019) y de la orden muestrear (T023)."""

import itertools
from collections import Counter

import numpy as np

from ghostmind.__main__ import main
from ghostmind.muestreo import muestreo_inicial
from ghostmind.registro import Registro


def generar(dic, semilla=42):
    return muestreo_inicial(dic, np.random.default_rng(semilla))


def test_tamanos_por_origen(dic):
    muestras = generar(dic)
    conteo = Counter(origen for origen, _ in muestras)
    assert conteo == {"aleatorio": 400, "limite": 120, "categoria": 200}


def test_todas_las_solicitudes_son_validas(dic):
    for _, solicitud in generar(dic):
        dic.validar(solicitud)


def test_valores_limite(dic):
    limites = [s for o, s in generar(dic) if o == "limite"]
    for campo in dic.numericos:
        assert sum(s[campo.nombre] == campo.minimo for s in limites) >= 10
        assert sum(s[campo.nombre] == campo.maximo for s in limites) >= 10


def test_todas_las_combinaciones_de_categorias(dic):
    por_categoria = Counter(
        (s["tipo_empleo"], s["codigo_convenio"]) for o, s in generar(dic) if o == "categoria"
    )
    combinaciones = set(itertools.product(*(c.nombres_valores for c in dic.categoricos)))
    assert set(por_categoria) == combinaciones
    assert all(n == 10 for n in por_categoria.values())


def test_determinismo(dic):
    assert generar(dic, 42) == generar(dic, 42)
    assert generar(dic, 42) != generar(dic, 43)


def test_orden_muestrear(tmp_path, capsys):
    ruta = tmp_path / "cli.sqlite"
    assert main(["muestrear", "--objetivo", "legacy", "--semilla", "42", "--db", str(ruta)]) == 0
    assert main(["muestrear", "--objetivo", "legacy", "--semilla", "42", "--db", str(ruta)]) == 0
    salida = capsys.readouterr().out
    assert "consultas" in salida.lower()
    reg = Registro(ruta)
    primera, segunda = reg.casos(1), reg.casos(2)
    reg.cerrar()
    assert len(primera) == 720
    assert set(primera["ronda"]) == {0}
    assert primera["origen"].value_counts().to_dict() == {"aleatorio": 400, "categoria": 200, "limite": 120}
    columnas = ["n_consulta", "origen", "edad", "monto", "tipo_empleo", "codigo_convenio", "decision"]
    assert primera[columnas].equals(segunda[columnas])
