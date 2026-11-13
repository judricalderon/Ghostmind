"""Evaluador declarativo de las reglas verdaderas (solo para la evaluación).

Interpreta ``reglas_verdaderas.json``: recorre las reglas en orden de precedencia y devuelve la
decisión y el identificador de la regla que decide. Es una segunda implementación, independiente
del legacy, que sirve para comprobarlo y para calcular las métricas por región.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

RUTA_REGLAS = Path(__file__).resolve().parent / "reglas_verdaderas.json"
DEFECTO = "DEFECTO"


def cumple(condiciones: Mapping[str, Mapping[str, Any]], solicitud: Mapping[str, Any]) -> bool:
    """Indica si la solicitud está dentro de la caja descrita por las condiciones."""
    for campo, cond in condiciones.items():
        valor = solicitud[campo]
        if "valores" in cond:
            if valor not in cond["valores"]:
                return False
            continue
        if "min" in cond and valor < cond["min"]:
            return False
        if "max" in cond and valor > cond["max"]:
            return False
    return True


@dataclass(frozen=True)
class ReglaVerdadera:
    id: str
    tipo: str
    descripcion: str
    condiciones: dict
    decision: str

    def cumple(self, solicitud: Mapping[str, Any]) -> bool:
        return cumple(self.condiciones, solicitud)


class Verdad:
    """Conjunto ordenado de reglas verdaderas con su decisión por defecto."""

    def __init__(self, reglas: list[ReglaVerdadera], decision_por_defecto: str):
        self.reglas = reglas
        self.decision_por_defecto = decision_por_defecto
        self._por_id = {r.id: r for r in reglas}

    @classmethod
    def cargar(cls, ruta: Path | str | None = None) -> "Verdad":
        datos = json.loads(Path(ruta or RUTA_REGLAS).read_text(encoding="utf-8"))
        reglas = [
            ReglaVerdadera(
                id=r["id"],
                tipo=r["tipo"],
                descripcion=r["descripcion"],
                condiciones=r["condiciones"],
                decision=r["decision"],
            )
            for r in datos["reglas"]
        ]
        return cls(reglas, datos["decision_por_defecto"])

    def regla(self, regla_id: str) -> ReglaVerdadera:
        return self._por_id[regla_id]

    def evaluar(self, solicitud: Mapping[str, Any]) -> tuple[str, str]:
        """Devuelve (decisión, id de la regla que decide o ``DEFECTO``)."""
        for regla in self.reglas:
            if regla.cumple(solicitud):
                return regla.decision, regla.id
        return self.decision_por_defecto, DEFECTO

    def decision(self, solicitud: Mapping[str, Any]) -> str:
        return self.evaluar(solicitud)[0]
