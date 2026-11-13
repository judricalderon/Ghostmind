"""Versión modernizada (simulada) del módulo de aprobación de créditos CRDAPR01.

Reescribe la lógica del legacy con nombres claros y constantes con nombre, y conserva el mismo
contrato de entrada y salida: un registro de ancho fijo de 35 posiciones y la decisión como texto.

Esta versión se usa en el experimento para comprobar si el verificador diferencial de GhostMind
detecta reglas que la modernización cambió. Qué cambió respecto al legacy está documentado solo en
``evaluacion/alteraciones.json``; GhostMind no lee este archivo.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    REVISION_MANUAL = "REVISION_MANUAL"


TIPOS_EMPLEO = {"E": "EMPLEADO", "I": "INDEPENDIENTE", "P": "PENSIONADO", "D": "DESEMPLEADO"}
CONVENIOS = {"    ": "NINGUNO", "C-12": "C-12", "C-31": "C-31", "C-45": "C-45", "C-77": "C-77"}

EDAD_MINIMA = 21
PUNTAJE_MINIMO = 420
PUNTAJE_SIN_REVISION = 550
INGRESO_MINIMO = 1_500_000
CONVENIO_LIBRANZA = "C-12"
MONTO_ALTO = 80_000_000
PUNTAJE_MONTO_ALTO = 800
ANTIGUEDAD_MONTO_ALTO = 60
CAMPANA_CONVENIO = "C-45"
CAMPANA_MONTO_MINIMO = 48_000_000
CAMPANA_MONTO_MAXIMO = 50_000_000


@dataclass(frozen=True)
class Solicitud:
    edad: int
    ingreso_mensual: int
    monto: int
    plazo_meses: int
    puntaje_credito: int
    antiguedad_meses: int
    tipo_empleo: str
    codigo_convenio: str

    @classmethod
    def desde_registro(cls, registro: str) -> "Solicitud":
        if registro is None or len(registro) != 35:
            raise ValueError("El registro debe tener 35 posiciones.")
        return cls(
            edad=int(registro[0:3]),
            ingreso_mensual=int(registro[3:12]),
            monto=int(registro[12:21]),
            plazo_meses=int(registro[21:24]),
            puntaje_credito=int(registro[24:27]),
            antiguedad_meses=int(registro[27:30]),
            tipo_empleo=TIPOS_EMPLEO[registro[30:31]],
            codigo_convenio=CONVENIOS[registro[31:35]],
        )


def es_campana_independientes(s: Solicitud) -> bool:
    return (
        s.tipo_empleo == "INDEPENDIENTE"
        and s.codigo_convenio == CAMPANA_CONVENIO
        and CAMPANA_MONTO_MINIMO <= s.monto <= CAMPANA_MONTO_MAXIMO
    )


def ingreso_insuficiente(s: Solicitud) -> bool:
    return s.ingreso_mensual < INGRESO_MINIMO and s.codigo_convenio != CONVENIO_LIBRANZA


def evaluar(s: Solicitud) -> Decision:
    if s.edad < EDAD_MINIMA:
        return Decision.RECHAZADO
    if es_campana_independientes(s):
        return Decision.REVISION_MANUAL
    if s.puntaje_credito < PUNTAJE_MINIMO:
        return Decision.RECHAZADO
    if s.tipo_empleo == "DESEMPLEADO":
        return Decision.RECHAZADO
    if ingreso_insuficiente(s):
        return Decision.RECHAZADO
    if s.monto > MONTO_ALTO:
        if s.puntaje_credito >= PUNTAJE_MONTO_ALTO and s.antiguedad_meses >= ANTIGUEDAD_MONTO_ALTO:
            return Decision.APROBADO
        return Decision.REVISION_MANUAL
    if s.puntaje_credito < PUNTAJE_SIN_REVISION:
        return Decision.REVISION_MANUAL
    return Decision.APROBADO


def CRDAPR01(WK_REG: str) -> str:  # noqa: N802 - se conserva el nombre del contrato original
    """Punto de entrada compatible con el legacy."""
    try:
        solicitud = Solicitud.desde_registro(WK_REG)
    except (ValueError, KeyError, TypeError):
        return "ERR-REG"
    return evaluar(solicitud).value
