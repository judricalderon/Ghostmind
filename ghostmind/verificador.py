"""Verificador diferencial (research.md, D10; FR-019).

Repite sobre otra versión del sistema los casos registrados en un descubrimiento, por medio del
mismo adaptador, y compara las decisiones. Las diferencias se agrupan por la regla descubierta
cuya caja contiene el caso, para que el especialista vea qué reglas cambió la modernización.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from ghostmind.adaptador import Adaptador, ErrorDelSistema, resolver_objetivo
from ghostmind.diccionario import Diccionario, Solicitud
from ghostmind.registro import Registro
from ghostmind.reglas import Caja

MAX_EJEMPLOS = 5


@dataclass
class ResumenRegla:
    regla_id: int
    codigo: str
    decision: str
    texto: str
    casos: int = 0
    diferencias: int = 0
    cambios: Counter = field(default_factory=Counter)
    ejemplos: list[dict] = field(default_factory=list)


@dataclass
class ResultadoVerificacion:
    ejecucion_id: int
    ejecucion_base_id: int
    objetivo: str
    casos_repetidos: int
    consultas: int
    diferencias: int
    errores: int
    sin_regla: int
    por_regla: list[ResumenRegla]

    @property
    def reglas_con_diferencias(self) -> list[ResumenRegla]:
        return [r for r in self.por_regla if r.diferencias]


class Verificador:
    """Compara otra versión del sistema contra la evidencia de un descubrimiento."""

    def __init__(self, dic: Diccionario, registro: Registro, objetivo: str | Callable[[str], str]):
        self.dic = dic
        self.registro = registro
        if isinstance(objetivo, str):  # se resuelve antes de crear la ejecución
            self.nombre, self.punto_de_entrada = objetivo, resolver_objetivo(objetivo)
        else:
            self.nombre, self.punto_de_entrada = getattr(objetivo, "__name__", "personalizado"), objetivo

    def _solicitud(self, fila) -> Solicitud:
        return {n: (int(getattr(fila, n)) if self.dic.campo(n).es_numerico else str(getattr(fila, n)))
                for n in self.dic.nombres}

    def verificar(self, ejecucion_base_id: int) -> ResultadoVerificacion:
        base = self.registro.ejecucion(ejecucion_base_id)  # KeyError si no existe
        if base["tipo"] != "descubrimiento":
            raise ValueError("Solo se pueden repetir los casos de una ejecución de descubrimiento.")
        casos = self.registro.casos(ejecucion_base_id, solo_validos=True)
        casos = casos.drop_duplicates(subset=list(self.dic.nombres), keep="first").reset_index(drop=True)
        reglas = self.registro.reglas(ejecucion_base_id)
        resumenes = [ResumenRegla(r["id"], r["codigo"], r["decision"], r["texto_negocio"]) for r in reglas]
        regla_de_caso = np.full(len(casos), -1)
        for indice, regla in enumerate(reglas):
            regla_de_caso[Caja.desde_condiciones(self.dic, regla["condiciones"]).mascara(casos)] = indice

        nombre = self.nombre
        ejecucion_id = self.registro.crear_ejecucion(
            "verificacion", nombre, semilla=None, presupuesto=max(1, len(casos)),
            parametros={"ejecucion_base": ejecucion_base_id}, ejecucion_base_id=ejecucion_base_id,
        )
        adaptador = Adaptador(self.dic, self.punto_de_entrada, self.registro, ejecucion_id, max(1, len(casos)))

        diferencias = errores = sin_regla = 0
        for posicion, fila in enumerate(casos.itertuples(index=False)):
            indice = int(regla_de_caso[posicion])
            resumen = resumenes[indice] if indice >= 0 else None
            if resumen is None:
                sin_regla += 1
            else:
                resumen.casos += 1
            solicitud = self._solicitud(fila)
            try:
                nueva = adaptador.consultar(solicitud, ronda=0, origen="verificacion", caso_base_id=int(fila.id))
            except ErrorDelSistema:
                errores += 1
                continue
            if nueva == fila.decision:
                continue
            diferencias += 1
            self.registro.guardar_diferencia(ejecucion_id, int(fila.id), adaptador.ultimo_caso_id,
                                             resumen.regla_id if resumen else None, fila.decision, nueva)
            if resumen is not None:
                resumen.diferencias += 1
                resumen.cambios[f"{fila.decision} -> {nueva}"] += 1
                if len(resumen.ejemplos) < MAX_EJEMPLOS:
                    resumen.ejemplos.append({**solicitud, "decision_original": fila.decision,
                                             "decision_nueva": nueva})
        self.registro.confirmar()
        self.registro.cerrar_ejecucion(ejecucion_id, adaptador.consultas, 0, "completa")
        return ResultadoVerificacion(
            ejecucion_id=ejecucion_id,
            ejecucion_base_id=ejecucion_base_id,
            objetivo=nombre,
            casos_repetidos=len(casos),
            consultas=adaptador.consultas,
            diferencias=diferencias,
            errores=errores,
            sin_regla=sin_regla,
            por_regla=resumenes,
        )
