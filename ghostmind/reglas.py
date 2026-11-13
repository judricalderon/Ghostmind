"""Reglas descubiertas: cajas de condiciones, confianza, estados y redacción (D6, D8, D9).

Una regla es una caja del espacio de entradas (un intervalo entero por campo numérico y un
conjunto de valores por campo categórico) junto con la decisión que el sistema toma dentro de ella.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from ghostmind.diccionario import Diccionario, Solicitud

ESTADOS = ("hipotesis", "corroborada", "validada", "rechazada")
MIN_RESPALDO_CORROBORADA = 30
MIN_PRUEBAS_CORROBORADA = 20

FRASE_DECISION = {
    "APROBADO": "Se aprueba la solicitud",
    "RECHAZADO": "Se rechaza la solicitud",
    "REVISION_MANUAL": "La solicitud pasa a revisión manual",
}
FRASE_CUALQUIERA = {
    "APROBADO": "Se aprueba cualquier solicitud.",
    "RECHAZADO": "Se rechaza cualquier solicitud.",
    "REVISION_MANUAL": "Cualquier solicitud pasa a revisión manual.",
}


def umbral_a_entero(umbral: float, lado: str) -> tuple[str, int]:
    """Convierte un umbral del árbol (``x <= umbral``) en un límite entero inclusivo."""
    piso = math.floor(umbral)
    if lado == "izquierda":
        return "max", piso
    if lado == "derecha":
        return "min", piso + 1
    raise ValueError(f"Lado desconocido: {lado!r}")


def confianza_wilson(respaldo: int, contraejemplos: int, z: float = 1.96) -> float:
    """Límite inferior del intervalo de Wilson para respaldo / (respaldo + contraejemplos)."""
    n = respaldo + contraejemplos
    if n == 0:
        return 0.0
    p = respaldo / n
    z2 = z * z
    centro = p + z2 / (2 * n)
    margen = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return max(0.0, (centro - margen) / (1 + z2 / n))


def estado_automatico(respaldo: int, contraejemplos: int, consultas_prueba: int,
                      min_respaldo: int = MIN_RESPALDO_CORROBORADA,
                      min_pruebas: int = MIN_PRUEBAS_CORROBORADA) -> str:
    """Estado que GhostMind puede asignar por sí mismo: ``corroborada`` o ``hipotesis``."""
    if respaldo >= min_respaldo and contraejemplos == 0 and consultas_prueba >= min_pruebas:
        return "corroborada"
    return "hipotesis"


def formato_miles(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


class Caja:
    """Región del espacio de entradas: intervalos enteros inclusivos y conjuntos de valores."""

    def __init__(self, dic: Diccionario, intervalos: Mapping[str, tuple[int, int]],
                 conjuntos: Mapping[str, Iterable[str]]):
        self.dic = dic
        self.intervalos = {c.nombre: tuple(intervalos[c.nombre]) for c in dic.numericos}
        self.conjuntos = {
            c.nombre: tuple(v for v in c.nombres_valores if v in set(conjuntos[c.nombre]))
            for c in dic.categoricos
        }

    # Construcción

    @classmethod
    def completa(cls, dic: Diccionario) -> "Caja":
        return cls(
            dic,
            {c.nombre: (c.minimo, c.maximo) for c in dic.numericos},
            {c.nombre: c.nombres_valores for c in dic.categoricos},
        )

    @classmethod
    def desde_condiciones(cls, dic: Diccionario, condiciones: Mapping[str, Mapping[str, Any]]) -> "Caja":
        caja = cls.completa(dic)
        for campo, cond in condiciones.items():
            if "valores" in cond:
                caja = caja.solo_valores(campo, cond["valores"])
            else:
                if "min" in cond:
                    caja = caja.con_minimo(campo, cond["min"])
                if "max" in cond:
                    caja = caja.con_maximo(campo, cond["max"])
        return caja

    def _copia(self, intervalos=None, conjuntos=None) -> "Caja":
        return Caja(self.dic, intervalos or self.intervalos, conjuntos or self.conjuntos)

    def con_minimo(self, campo: str, valor: int) -> "Caja":
        lo, hi = self.intervalos[campo]
        return self._copia(intervalos={**self.intervalos, campo: (max(lo, valor), hi)})

    def con_maximo(self, campo: str, valor: int) -> "Caja":
        lo, hi = self.intervalos[campo]
        return self._copia(intervalos={**self.intervalos, campo: (lo, min(hi, valor))})

    def solo_valores(self, campo: str, valores: Iterable[str]) -> "Caja":
        permitidos = set(valores)
        return self._copia(conjuntos={
            **self.conjuntos, campo: tuple(v for v in self.conjuntos[campo] if v in permitidos)
        })

    def solo_valor(self, campo: str, valor: str) -> "Caja":
        return self.solo_valores(campo, [valor])

    def sin_valor(self, campo: str, valor: str) -> "Caja":
        return self._copia(conjuntos={
            **self.conjuntos, campo: tuple(v for v in self.conjuntos[campo] if v != valor)
        })

    # Consultas

    @property
    def vacia(self) -> bool:
        return any(lo > hi for lo, hi in self.intervalos.values()) or any(
            not valores for valores in self.conjuntos.values()
        )

    def clave(self) -> tuple:
        return (tuple(sorted(self.intervalos.items())), tuple(sorted(self.conjuntos.items())))

    def __eq__(self, otra: object) -> bool:
        return isinstance(otra, Caja) and self.clave() == otra.clave()

    def __hash__(self) -> int:
        return hash(self.clave())

    def __repr__(self) -> str:
        return f"Caja({self.condiciones()})"

    def contiene(self, solicitud: Mapping[str, Any]) -> bool:
        for campo, (lo, hi) in self.intervalos.items():
            if not lo <= solicitud[campo] <= hi:
                return False
        for campo, valores in self.conjuntos.items():
            if solicitud[campo] not in valores:
                return False
        return True

    def mascara(self, tabla: pd.DataFrame) -> np.ndarray:
        mascara = np.ones(len(tabla), dtype=bool)
        for campo, (lo, hi) in self.intervalos.items():
            columna = tabla[campo].to_numpy()
            mascara &= (columna >= lo) & (columna <= hi)
        for campo, valores in self.conjuntos.items():
            mascara &= tabla[campo].isin(valores).to_numpy()
        return mascara

    def restringidos(self) -> list[str]:
        """Campos (en orden del diccionario) cuya condición no es todo el dominio."""
        nombres = []
        for campo in self.dic.campos:
            if campo.es_numerico:
                if self.intervalos[campo.nombre] != (campo.minimo, campo.maximo):
                    nombres.append(campo.nombre)
            elif self.conjuntos[campo.nombre] != campo.nombres_valores:
                nombres.append(campo.nombre)
        return nombres

    def condiciones(self) -> dict[str, dict]:
        """Formato JSON de data-model.md: solo los campos que restringen algo."""
        salida: dict[str, dict] = {}
        for nombre in self.restringidos():
            if nombre in self.intervalos:
                lo, hi = self.intervalos[nombre]
                salida[nombre] = {"min": lo, "max": hi}
            else:
                salida[nombre] = {"valores": list(self.conjuntos[nombre])}
        return salida

    def muestrear(self, rng: np.random.Generator, fijos: Mapping[str, Any] | None = None) -> Solicitud:
        """Solicitud uniforme dentro de la caja."""
        solicitud: Solicitud = {}
        for campo in self.dic.campos:
            if campo.es_numerico:
                lo, hi = self.intervalos[campo.nombre]
                solicitud[campo.nombre] = int(rng.integers(lo, hi + 1))
            else:
                valores = self.conjuntos[campo.nombre]
                solicitud[campo.nombre] = valores[int(rng.integers(0, len(valores)))]
        if fijos:
            solicitud.update(fijos)
        return solicitud

    # Redacción

    def _partes_tecnicas(self) -> list[str]:
        partes = []
        for nombre in self.restringidos():
            campo = self.dic.campo(nombre)
            if campo.es_numerico:
                lo, hi = self.intervalos[nombre]
                if lo != campo.minimo and hi != campo.maximo:
                    partes.append(f"{lo} <= {nombre} <= {hi}")
                elif lo != campo.minimo:
                    partes.append(f"{nombre} >= {lo}")
                else:
                    partes.append(f"{nombre} <= {hi}")
            else:
                incluidos = self.conjuntos[nombre]
                excluidos = tuple(v for v in campo.nombres_valores if v not in incluidos)
                if len(incluidos) == 1:
                    partes.append(f"{nombre} = {incluidos[0]}")
                elif len(excluidos) == 1:
                    partes.append(f"{nombre} != {excluidos[0]}")
                elif len(excluidos) < len(incluidos):
                    partes.append(f"{nombre} NO EN {{{', '.join(excluidos)}}}")
                else:
                    partes.append(f"{nombre} EN {{{', '.join(incluidos)}}}")
        return partes

    def _partes_negocio(self) -> list[str]:
        partes = []
        for nombre in self.restringidos():
            campo = self.dic.campo(nombre)
            sujeto = f"{campo.articulo} {campo.etiqueta}"
            if campo.es_numerico:
                lo, hi = self.intervalos[nombre]
                unidad = f" {campo.unidad}" if campo.unidad else ""
                if lo != campo.minimo and hi != campo.maximo:
                    partes.append(f"{sujeto} está entre {formato_miles(lo)} y {formato_miles(hi)}{unidad}")
                elif lo != campo.minimo:
                    partes.append(f"{sujeto} es de {formato_miles(lo)}{unidad} o más")
                else:
                    partes.append(f"{sujeto} es de {formato_miles(hi)}{unidad} o menos")
            else:
                incluidos = [campo.etiqueta_valor(v) for v in self.conjuntos[nombre]]
                excluidos = [campo.etiqueta_valor(v) for v in campo.nombres_valores
                             if v not in self.conjuntos[nombre]]
                if len(excluidos) < len(incluidos) and len(incluidos) > 1:
                    partes.append(f"{sujeto} no es {_lista(excluidos, 'ni')}")
                else:
                    partes.append(f"{sujeto} es {_lista(incluidos, 'o')}")
        return partes


def _lista(elementos: list[str], conector: str) -> str:
    if len(elementos) == 1:
        return elementos[0]
    return f"{', '.join(elementos[:-1])} {conector} {elementos[-1]}"


@dataclass
class Regla:
    """Regla descubierta con su evidencia y su estado."""

    codigo: str
    caja: Caja
    decision: str
    respaldo: int = 0
    contraejemplos: int = 0
    consultas_prueba: int = 0
    estado: str = "hipotesis"
    umbrales_confirmados: list[dict] = field(default_factory=list)
    casos_respaldo: list[int] = field(default_factory=list, repr=False)
    casos_contraejemplo: list[int] = field(default_factory=list, repr=False)
    id: int | None = None

    @property
    def confianza(self) -> float:
        return confianza_wilson(self.respaldo, self.contraejemplos)

    def actualizar_estado(self) -> None:
        if self.estado in ("hipotesis", "corroborada"):
            self.estado = estado_automatico(self.respaldo, self.contraejemplos, self.consultas_prueba)

    def texto_tecnico(self) -> str:
        partes = self.caja._partes_tecnicas()
        condicion = " Y ".join(partes) if partes else "cualquier solicitud"
        return f"SI {condicion} ENTONCES {self.decision}"

    def texto_negocio(self) -> str:
        partes = self.caja._partes_negocio()
        if not partes:
            return FRASE_CUALQUIERA[self.decision]
        return f"{FRASE_DECISION[self.decision]} cuando {_lista(partes, 'y')}."
