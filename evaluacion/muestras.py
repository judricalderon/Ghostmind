"""Generación de solicitudes uniformes para la evaluación.

Es independiente del muestreo de GhostMind, para que las solicitudes de evaluación no compartan
código ni semillas con el descubrimiento.
"""

from __future__ import annotations

import numpy as np

from ghostmind.diccionario import Diccionario


def uniformes(dic: Diccionario, n: int, semilla: int) -> list[dict]:
    """Devuelve ``n`` solicitudes uniformes sobre el diccionario."""
    rng = np.random.default_rng(semilla)
    columnas = {}
    for campo in dic.campos:
        if campo.es_numerico:
            columnas[campo.nombre] = rng.integers(campo.minimo, campo.maximo + 1, size=n).tolist()
        else:
            valores = campo.nombres_valores
            indices = rng.integers(0, len(valores), size=n)
            columnas[campo.nombre] = [valores[i] for i in indices]
    return [{nombre: columnas[nombre][i] for nombre in dic.nombres} for i in range(n)]
