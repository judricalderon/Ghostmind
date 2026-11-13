"""Catálogo de reglas: revisiones del especialista y exportación (FR-016, FR-017).

Solo el especialista puede marcar una regla como ``validada`` o ``rechazada``; cada decisión queda
en el historial con su fecha y una nota opcional.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ghostmind.registro import Registro, ahora

DECISIONES_ESPECIALISTA = ("validada", "rechazada")
FORMATO = "ghostmind-catalogo/1"


def revisar(registro: Registro, regla_id: int, decision: str, nota: str | None = None) -> None:
    """Registra que el especialista valida o rechaza una regla."""
    if decision not in DECISIONES_ESPECIALISTA:
        raise ValueError(f"El especialista solo puede validar o rechazar, no {decision!r}.")
    registro.regla(regla_id)  # KeyError si no existe
    nota = (nota or "").strip() or None
    registro.guardar_revision(regla_id, decision, nota)


def historial(registro: Registro, regla_id: int) -> list[dict[str, Any]]:
    return registro.revisiones(regla_id)


def exportar(registro: Registro, ejecucion_id: int) -> dict[str, Any]:
    """Catálogo de una ejecución con el formato de contracts/catalogo-json.md."""
    e = registro.ejecucion(ejecucion_id)
    reglas = []
    for r in sorted(registro.reglas(ejecucion_id), key=lambda r: r["codigo"]):
        reglas.append({
            "codigo": r["codigo"],
            "decision": r["decision"],
            "condiciones": r["condiciones"],
            "umbrales_confirmados": r["umbrales_confirmados"],
            "respaldo": r["respaldo"],
            "contraejemplos": r["contraejemplos"],
            "confianza": round(float(r["confianza"]), 4),
            "estado": r["estado"],
            "texto_tecnico": r["texto_tecnico"],
            "texto_negocio": r["texto_negocio"],
            "texto_llm": r["texto_llm"],
            "revisiones": registro.revisiones(r["id"]),
        })
    return {
        "formato": FORMATO,
        "generado": ahora(),
        "ejecucion": {
            "id": e["id"],
            "objetivo": e["objetivo"],
            "semilla": e["semilla"],
            "presupuesto": e["presupuesto"],
            "consultas": e["consultas"],
            "rondas": e["rondas"],
            "motivo_parada": e["motivo_parada"],
            "version": e["version"],
        },
        "reglas": reglas,
    }


def exportar_json(registro: Registro, ejecucion_id: int, ruta: Path | str) -> Path:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(exportar(registro, ejecucion_id), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return ruta
