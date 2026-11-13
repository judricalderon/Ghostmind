"""Muestreo inicial (research.md, D5) y generadores de solicitudes.

Combina solicitudes uniformes, valores límite de cada campo numérico y todas las combinaciones de
los campos categóricos. Todo depende de un generador con semilla, así que es reproducible.
"""

from __future__ import annotations

import itertools
from typing import Mapping

import numpy as np

from ghostmind.diccionario import Diccionario, Solicitud

PARAMETROS_POR_DEFECTO = {"aleatorio": 400, "bases_limite": 10, "bases_categoria": 10}


def solicitud_uniforme(dic: Diccionario, rng: np.random.Generator,
                       fijos: Mapping[str, int | str] | None = None) -> Solicitud:
    """Una solicitud uniforme sobre el diccionario, con algunos campos opcionalmente fijos."""
    solicitud: Solicitud = {}
    for campo in dic.campos:
        if campo.es_numerico:
            solicitud[campo.nombre] = int(rng.integers(campo.minimo, campo.maximo + 1))
        else:
            valores = campo.nombres_valores
            solicitud[campo.nombre] = valores[int(rng.integers(0, len(valores)))]
    if fijos:
        solicitud.update(fijos)
    return solicitud


def tamano_muestreo_inicial(dic: Diccionario, parametros: Mapping[str, int] | None = None) -> int:
    p = {**PARAMETROS_POR_DEFECTO, **(parametros or {})}
    combinaciones = 1
    for campo in dic.categoricos:
        combinaciones *= len(campo.valores)
    return p["aleatorio"] + 2 * len(dic.numericos) * p["bases_limite"] + combinaciones * p["bases_categoria"]


def muestreo_inicial(dic: Diccionario, rng: np.random.Generator,
                     parametros: Mapping[str, int] | None = None) -> list[tuple[str, Solicitud]]:
    """Devuelve la lista ordenada de (origen, solicitud) del muestreo inicial."""
    p = {**PARAMETROS_POR_DEFECTO, **(parametros or {})}
    muestras: list[tuple[str, Solicitud]] = []

    for _ in range(p["aleatorio"]):
        muestras.append(("aleatorio", solicitud_uniforme(dic, rng)))

    for campo in dic.numericos:
        for valor in (campo.minimo, campo.maximo):
            for _ in range(p["bases_limite"]):
                muestras.append(("limite", solicitud_uniforme(dic, rng, {campo.nombre: valor})))

    nombres_cat = [c.nombre for c in dic.categoricos]
    for combinacion in itertools.product(*(c.nombres_valores for c in dic.categoricos)):
        fijos = dict(zip(nombres_cat, combinacion))
        for _ in range(p["bases_categoria"]):
            muestras.append(("categoria", solicitud_uniforme(dic, rng, fijos)))

    return muestras
