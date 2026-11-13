"""Extractor de reglas: árbol de decisión interpretable convertido en cajas (research.md, D6).

Los campos categóricos entran como variables indicadoras. Los numéricos entran por su posición
entre los valores observados: scikit-learn guarda las entradas del árbol en ``float32``, que no
distingue enteros grandes como 80.000.000 y 80.000.001. Como el árbol solo depende del orden de
los valores, las particiones son las mismas, y cada umbral se traduce al punto medio entre los dos
valores originales que separa. Cada hoja es una regla; cada nodo interno numérico es un umbral
candidato para la bisección.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

from ghostmind.diccionario import Diccionario
from ghostmind.reglas import Caja, umbral_a_entero


@dataclass(frozen=True)
class Hoja:
    nodo: int
    caja: Caja
    decision: str
    casos: int


@dataclass(frozen=True)
class Division:
    nodo: int
    campo: str
    umbral: float  # en unidades del campo: punto medio entre los dos valores que separa
    caja: Caja  # región que llega al nodo


class Codificador:
    """Traduce solicitudes a la matriz de entrada del árbol."""

    def __init__(self, dic: Diccionario):
        self.dic = dic
        self.origen: list[tuple[str, str | None]] = []  # (campo, valor categórico o None)
        for campo in dic.campos:
            if campo.es_numerico:
                self.origen.append((campo.nombre, None))
            else:
                for valor in campo.nombres_valores:
                    self.origen.append((campo.nombre, valor))

    def matriz(self, tabla: pd.DataFrame, valores_numericos: Mapping[str, np.ndarray]) -> np.ndarray:
        """Matriz con posiciones para los numéricos e indicadoras para los categóricos."""
        columnas = []
        for campo, valor in self.origen:
            if valor is None:
                columnas.append(np.searchsorted(valores_numericos[campo], tabla[campo].to_numpy()))
            else:
                columnas.append((tabla[campo] == valor).to_numpy())
        return np.column_stack(columnas).astype(np.float32)


class Modelo:
    """Árbol ajustado con acceso a sus hojas, divisiones y predicciones."""

    def __init__(self, dic: Diccionario, arbol: DecisionTreeClassifier, codificador: Codificador,
                 valores_numericos: Mapping[str, np.ndarray]):
        self.dic = dic
        self.arbol = arbol
        self.codificador = codificador
        t = arbol.tree_
        self._izq = t.children_left
        self._der = t.children_right
        self._clases = list(arbol.classes_)
        self._decision = {n: self._clases[int(np.argmax(t.value[n][0]))] for n in range(t.node_count)}
        self._casos = t.n_node_samples
        # Para cada nodo interno: (campo, valor categórico o None, umbral en unidades originales)
        self._prueba: dict[int, tuple[str, str | None, float]] = {}
        for nodo in range(t.node_count):
            if self._izq[nodo] == -1:
                continue
            campo, valor = codificador.origen[t.feature[nodo]]
            if valor is None:
                posicion = int(np.floor(t.threshold[nodo]))
                observados = valores_numericos[campo]
                umbral = (float(observados[posicion]) + float(observados[posicion + 1])) / 2
            else:
                umbral = 0.5
            self._prueba[nodo] = (campo, valor, umbral)
        self._cajas: dict[int, Caja] = {}
        self._recorrer(0, Caja.completa(dic))

    def _recorrer(self, nodo: int, caja: Caja) -> None:
        self._cajas[nodo] = caja
        if self._izq[nodo] == -1:
            return
        campo, valor, umbral = self._prueba[nodo]
        if valor is None:
            _, maximo = umbral_a_entero(umbral, "izquierda")
            _, minimo = umbral_a_entero(umbral, "derecha")
            self._recorrer(self._izq[nodo], caja.con_maximo(campo, maximo))
            self._recorrer(self._der[nodo], caja.con_minimo(campo, minimo))
        else:  # variable indicadora: izquierda = no es el valor; derecha = es el valor
            self._recorrer(self._izq[nodo], caja.sin_valor(campo, valor))
            self._recorrer(self._der[nodo], caja.solo_valor(campo, valor))

    def hojas(self) -> list[Hoja]:
        return [
            Hoja(nodo, self._cajas[nodo], self._decision[nodo], int(self._casos[nodo]))
            for nodo in sorted(self._cajas)
            if self._izq[nodo] == -1
        ]

    def divisiones(self) -> list[Division]:
        """Nodos internos con umbral sobre un campo numérico, en orden de nodo."""
        return [
            Division(nodo, campo, umbral, self._cajas[nodo])
            for nodo, (campo, valor, umbral) in sorted(self._prueba.items())
            if valor is None
        ]

    def nodo_hoja(self, solicitud: Mapping) -> int:
        nodo = 0
        while self._izq[nodo] != -1:
            campo, valor, umbral = self._prueba[nodo]
            if valor is None:
                a_la_izquierda = solicitud[campo] <= umbral
            else:
                a_la_izquierda = solicitud[campo] != valor
            nodo = self._izq[nodo] if a_la_izquierda else self._der[nodo]
        return nodo

    def predecir_uno(self, solicitud: Mapping) -> str:
        return self._decision[self.nodo_hoja(solicitud)]

    def predecir(self, tabla: pd.DataFrame) -> np.ndarray:
        """Predicción vectorizada: cada fila cae en exactamente una hoja."""
        salida = np.empty(len(tabla), dtype=object)
        for hoja in self.hojas():
            salida[hoja.caja.mascara(tabla)] = hoja.decision
        return salida


class Extractor:
    """Induce reglas a partir de los casos registrados."""

    def __init__(self, dic: Diccionario, semilla: int, min_casos_hoja: int = 3):
        self.dic = dic
        self.semilla = semilla
        self.min_casos_hoja = min_casos_hoja
        self.codificador = Codificador(dic)

    def ajustar(self, datos: pd.DataFrame) -> Modelo:
        """``datos`` tiene una columna por campo del diccionario y la columna ``decision``."""
        valores_numericos = {
            c.nombre: np.unique(datos[c.nombre].to_numpy(dtype=np.int64)) for c in self.dic.numericos
        }
        arbol = DecisionTreeClassifier(
            criterion="entropy",
            min_samples_leaf=self.min_casos_hoja,
            random_state=self.semilla,
        )
        arbol.fit(self.codificador.matriz(datos, valores_numericos), datos["decision"].to_numpy())
        return Modelo(self.dic, arbol, self.codificador, valores_numericos)
