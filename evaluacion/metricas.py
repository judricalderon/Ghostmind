"""Métricas del experimento (spec.md, "Definición de las métricas"; research.md, D12).

Este módulo está fuera de GhostMind y es el único, junto con ``verdad.py``, que usa las reglas
verdaderas. Las definiciones y umbrales se fijaron en la especificación antes de ejecutar:

- Pureza de una regla reportada: proporción de 2.000 solicitudes uniformes dentro de su región
  en las que el legacy toma la decisión que la regla afirma. La regla existe si su pureza es de al
  menos 95 %, y se asocia a la regla plantada (o al defecto) que decide la mayoría de esas
  solicitudes.
- Regla plantada recuperada: al menos una regla reportada que existe está asociada a ella, y en
  2.000 solicitudes uniformes de su región efectiva las reglas de GhostMind predicen su decisión
  en al menos el 90 %.
- C1 = recuperadas / 10; C2 = reportadas que existen / reportadas; C3 = coincidencias con el
  legacy en 10.000 solicitudes nuevas; C5 = alteraciones detectadas / alteraciones.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Iterable, Mapping

import numpy as np
import pandas as pd

from evaluacion.muestras import uniformes
from evaluacion.verdad import DEFECTO, ReglaVerdadera, Verdad
from ghostmind.diccionario import Diccionario
from ghostmind.reglas import Caja

UMBRAL_PUREZA = 0.95
UMBRAL_FIDELIDAD_LOCAL = 0.90
MUESTRAS_POR_REGLA = 2_000
CASOS_C3 = 10_000
SEMILLA_C3 = 20261112
METAS = {"C1": 0.80, "C2": 0.90, "C3": 0.95, "C5": 1.00}

Predictor = Callable[[pd.DataFrame], np.ndarray]


def muestras_en_caja(caja: Caja, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """``n`` solicitudes uniformes dentro de una caja, como tabla."""
    columnas = {}
    for campo in caja.dic.campos:
        if campo.es_numerico:
            lo, hi = caja.intervalos[campo.nombre]
            columnas[campo.nombre] = rng.integers(lo, hi + 1, size=n)
        else:
            valores = np.array(caja.conjuntos[campo.nombre], dtype=object)
            columnas[campo.nombre] = valores[rng.integers(0, len(valores), size=n)]
    return pd.DataFrame(columnas)


def _registros(tabla: pd.DataFrame, dic: Diccionario) -> list[dict]:
    filas = tabla[list(dic.nombres)].to_dict("records")
    return [{k: (int(v) if dic.campo(k).es_numerico else str(v)) for k, v in f.items()} for f in filas]


class PredictorReglas:
    """Predice con las reglas que reportó GhostMind (cada solicitud cae en una sola regla)."""

    def __init__(self, reglas: Iterable[Mapping[str, Any]], dic: Diccionario):
        self.dic = dic
        self.reglas = [(Caja.desde_condiciones(dic, r["condiciones"]), r["decision"]) for r in reglas]

    def __call__(self, tabla: pd.DataFrame) -> np.ndarray:
        salida = np.full(len(tabla), None, dtype=object)
        for caja, decision in self.reglas:
            salida[caja.mascara(tabla)] = decision
        return salida


# C2: pureza y existencia de cada regla reportada

def evaluar_regla_reportada(caja: Caja, decision: str, verdad: Verdad, dic: Diccionario,
                            rng: np.random.Generator, n: int = MUESTRAS_POR_REGLA) -> dict[str, Any]:
    evaluaciones = [verdad.evaluar(s) for s in _registros(muestras_en_caja(caja, n, rng), dic)]
    pureza = sum(d == decision for d, _ in evaluaciones) / n
    asociada = Counter(regla for _, regla in evaluaciones).most_common(1)[0][0]
    return {"pureza": pureza, "existe": pureza >= UMBRAL_PUREZA, "asociada": asociada}


def calcular_c2(detalle: list[Mapping[str, Any]]) -> dict[str, Any]:
    existen = sum(bool(d["existe"]) for d in detalle)
    reportadas = len(detalle)
    valor = existen / reportadas if reportadas else 0.0
    return {"valor": valor, "meta": METAS["C2"], "cumple": valor >= METAS["C2"], "existen": existen,
            "reportadas": reportadas}


# C1: recuperación de cada regla plantada

def fidelidad_local(regla: ReglaVerdadera, verdad: Verdad, predecir: Predictor, dic: Diccionario,
                    rng: np.random.Generator, n: int = MUESTRAS_POR_REGLA,
                    max_intentos: int = 400) -> float:
    """Aciertos de GhostMind en ``n`` solicitudes uniformes de la región efectiva de la regla."""
    caja = Caja.desde_condiciones(dic, regla.condiciones)
    efectivas: list[pd.DataFrame] = []
    reunidas = 0
    for _ in range(max_intentos):
        lote = muestras_en_caja(caja, n, rng)
        mascara = np.array([verdad.evaluar(s)[1] == regla.id for s in _registros(lote, dic)])
        efectivas.append(lote[mascara])
        reunidas += int(mascara.sum())
        if reunidas >= n:
            break
    tabla = pd.concat(efectivas, ignore_index=True).head(n)
    if tabla.empty:
        return 0.0
    return float(np.mean(predecir(tabla) == regla.decision))


def calcular_c1(verdad: Verdad, detalle_reportadas: list[Mapping[str, Any]], predecir: Predictor,
                dic: Diccionario, rng: np.random.Generator, n: int = MUESTRAS_POR_REGLA) -> dict[str, Any]:
    detalle = []
    for regla in verdad.reglas:
        asociadas = [d["codigo"] for d in detalle_reportadas if d["existe"] and d["asociada"] == regla.id]
        fidelidad = fidelidad_local(regla, verdad, predecir, dic, rng, n)
        detalle.append({
            "regla": regla.id,
            "tipo": regla.tipo,
            "descripcion": regla.descripcion,
            "reglas_asociadas": asociadas,
            "fidelidad_local": fidelidad,
            "recuperada": bool(asociadas) and fidelidad >= UMBRAL_FIDELIDAD_LOCAL,
        })
    recuperadas = sum(d["recuperada"] for d in detalle)
    valor = recuperadas / len(detalle)
    return {"valor": valor, "meta": METAS["C1"], "cumple": valor >= METAS["C1"], "recuperadas": recuperadas,
            "total": len(detalle), "detalle": detalle}


# C3: fidelidad en casos nuevos

def calcular_c3(predecir: Predictor, dic: Diccionario, sistema: Callable[[str], str], n: int = CASOS_C3,
                semilla: int = SEMILLA_C3, registrados: set[tuple] | None = None) -> dict[str, Any]:
    solicitudes = uniformes(dic, n, semilla)
    tabla = pd.DataFrame(solicitudes)
    predichas = predecir(tabla)
    reales = np.array([sistema(dic.armar_registro(s)) for s in solicitudes], dtype=object)
    coinciden = int(np.sum(predichas == reales))
    claves = {tuple(s[c] for c in dic.nombres) for s in solicitudes}
    en_registro = len(claves & registrados) if registrados else 0
    valor = coinciden / n
    return {"valor": valor, "meta": METAS["C3"], "cumple": valor >= METAS["C3"], "casos": n,
            "coinciden": coinciden, "semilla": semilla, "casos_en_registro": en_registro}


# C5: detección de las reglas alteradas

def calcular_c5(diferencias: pd.DataFrame, verdad: Verdad, alteraciones: list[dict]) -> dict[str, Any]:
    """Una alteración se detecta si alguna diferencia reportada la explica aplicada sola."""
    casos = diferencias.to_dict("records")
    detalle = []
    for alteracion in alteraciones:
        alterada = verdad.con_alteraciones([alteracion])
        atribuidas = sum(alterada.decision(c) != verdad.decision(c) for c in casos)
        detalle.append({
            "alteracion": alteracion["id"],
            "regla": alteracion["regla"],
            "descripcion": alteracion["descripcion"],
            "diferencias_atribuidas": atribuidas,
            "detectada": atribuidas > 0,
        })
    detectadas = sum(d["detectada"] for d in detalle)
    valor = detectadas / len(detalle) if detalle else 0.0
    return {"valor": valor, "meta": METAS["C5"], "cumple": valor >= METAS["C5"], "detectadas": detectadas,
            "total": len(detalle), "diferencias_reportadas": len(casos), "detalle": detalle}


__all__ = [
    "PredictorReglas", "muestras_en_caja", "evaluar_regla_reportada", "calcular_c2", "fidelidad_local",
    "calcular_c1", "calcular_c3", "calcular_c5", "METAS", "UMBRAL_PUREZA", "UMBRAL_FIDELIDAD_LOCAL",
    "MUESTRAS_POR_REGLA", "CASOS_C3", "SEMILLA_C3", "DEFECTO",
]
