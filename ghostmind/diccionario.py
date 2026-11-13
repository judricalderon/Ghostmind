"""Diccionario de campos del sistema y registro de ancho fijo.

Es todo lo que GhostMind sabe del sistema: nombre, tipo, rango o valores de cada entrada, su
posición en el registro y las decisiones posibles. No contiene reglas de negocio.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
RUTA_DICCIONARIO = RAIZ / "sistemas" / "diccionario_credito.json"

Solicitud = dict[str, int | str]


class SolicitudInvalida(ValueError):
    """La solicitud no cumple el diccionario de campos."""


@dataclass(frozen=True)
class ValorCategorico:
    valor: str
    codigo: str


@dataclass(frozen=True)
class Campo:
    nombre: str
    etiqueta: str
    tipo: str
    inicio: int
    longitud: int
    unidad: str | None = None
    minimo: int | None = None
    maximo: int | None = None
    valores: tuple[ValorCategorico, ...] = ()

    @property
    def es_numerico(self) -> bool:
        return self.tipo == "entero"

    @property
    def nombres_valores(self) -> tuple[str, ...]:
        return tuple(v.valor for v in self.valores)

    def es_valido(self, valor: Any) -> bool:
        if self.es_numerico:
            return (
                isinstance(valor, int)
                and not isinstance(valor, bool)
                and self.minimo <= valor <= self.maximo
            )
        return isinstance(valor, str) and valor in self.nombres_valores

    def codificar(self, valor: int | str) -> str:
        if self.es_numerico:
            return str(valor).zfill(self.longitud)
        for v in self.valores:
            if v.valor == valor:
                return v.codigo
        raise SolicitudInvalida(f"{self.nombre}: valor desconocido {valor!r}")

    def decodificar(self, texto: str) -> int | str:
        if self.es_numerico:
            return int(texto)
        for v in self.valores:
            if v.codigo == texto:
                return v.valor
        raise SolicitudInvalida(f"{self.nombre}: código desconocido {texto!r}")


class Diccionario:
    """Diccionario de campos validado."""

    def __init__(self, sistema: str, longitud_registro: int, decisiones: tuple[str, ...],
                 campos: tuple[Campo, ...]):
        self.sistema = sistema
        self.longitud_registro = longitud_registro
        self.decisiones = decisiones
        self.campos = campos
        self._por_nombre = {c.nombre: c for c in campos}
        self._verificar()

    @classmethod
    def cargar(cls, ruta: Path | str | None = None) -> "Diccionario":
        ruta = Path(ruta) if ruta else RUTA_DICCIONARIO
        return cls.desde_dict(json.loads(ruta.read_text(encoding="utf-8")))

    @classmethod
    def desde_dict(cls, datos: dict) -> "Diccionario":
        campos = []
        for c in datos["campos"]:
            campos.append(
                Campo(
                    nombre=c["nombre"],
                    etiqueta=c.get("etiqueta", c["nombre"]),
                    tipo=c["tipo"],
                    inicio=int(c["inicio"]),
                    longitud=int(c["longitud"]),
                    unidad=c.get("unidad"),
                    minimo=c.get("minimo"),
                    maximo=c.get("maximo"),
                    valores=tuple(ValorCategorico(v["valor"], v["codigo"]) for v in c.get("valores", [])),
                )
            )
        return cls(
            sistema=datos["sistema"],
            longitud_registro=int(datos["longitud_registro"]),
            decisiones=tuple(datos["decisiones"]),
            campos=tuple(campos),
        )

    def _verificar(self) -> None:
        if len(self._por_nombre) != len(self.campos):
            raise ValueError("Hay nombres de campo repetidos en el diccionario.")
        ocupadas: set[int] = set()
        for c in self.campos:
            if c.tipo not in ("entero", "categorico"):
                raise ValueError(f"{c.nombre}: tipo desconocido {c.tipo!r}")
            if c.es_numerico:
                if c.minimo is None or c.maximo is None or c.minimo > c.maximo:
                    raise ValueError(f"{c.nombre}: rango inválido")
                if c.minimo < 0 or len(str(c.maximo)) > c.longitud:
                    raise ValueError(f"{c.nombre}: el rango no cabe en {c.longitud} posiciones")
            else:
                if not c.valores:
                    raise ValueError(f"{c.nombre}: no tiene valores")
                if any(len(v.codigo) != c.longitud for v in c.valores):
                    raise ValueError(f"{c.nombre}: un código no coincide con la longitud")
                if len({v.valor for v in c.valores}) != len(c.valores):
                    raise ValueError(f"{c.nombre}: valores repetidos")
            posiciones = set(range(c.inicio, c.inicio + c.longitud))
            if ocupadas & posiciones:
                raise ValueError(f"{c.nombre}: se traslapa con otro campo en el registro")
            ocupadas |= posiciones
        if ocupadas != set(range(1, self.longitud_registro + 1)):
            raise ValueError("Los campos no cubren exactamente el registro.")
        if len(set(self.decisiones)) != len(self.decisiones) or not self.decisiones:
            raise ValueError("Decisiones inválidas.")

    # Consultas sobre el diccionario

    def campo(self, nombre: str) -> Campo:
        return self._por_nombre[nombre]

    @property
    def nombres(self) -> tuple[str, ...]:
        return tuple(c.nombre for c in self.campos)

    @property
    def numericos(self) -> tuple[Campo, ...]:
        return tuple(c for c in self.campos if c.es_numerico)

    @property
    def categoricos(self) -> tuple[Campo, ...]:
        return tuple(c for c in self.campos if not c.es_numerico)

    # Validación y registro

    def validar(self, solicitud: Solicitud) -> None:
        """Lanza ``SolicitudInvalida`` si la solicitud no cumple el diccionario."""
        if not isinstance(solicitud, dict):
            raise SolicitudInvalida("La solicitud debe ser un diccionario.")
        faltantes = [n for n in self.nombres if n not in solicitud]
        sobrantes = [n for n in solicitud if n not in self._por_nombre]
        if faltantes or sobrantes:
            raise SolicitudInvalida(f"Faltan {faltantes} o sobran {sobrantes}.")
        for campo in self.campos:
            if not campo.es_valido(solicitud[campo.nombre]):
                raise SolicitudInvalida(
                    f"{campo.nombre}: valor fuera del diccionario {solicitud[campo.nombre]!r}"
                )

    def armar_registro(self, solicitud: Solicitud) -> str:
        """Arma el registro de ancho fijo que espera el sistema."""
        self.validar(solicitud)
        texto = [" "] * self.longitud_registro
        for campo in self.campos:
            codigo = campo.codificar(solicitud[campo.nombre])
            texto[campo.inicio - 1: campo.inicio - 1 + campo.longitud] = list(codigo)
        return "".join(texto)

    def leer_registro(self, registro: str) -> Solicitud:
        """Convierte un registro de ancho fijo en una solicitud."""
        if len(registro) != self.longitud_registro:
            raise SolicitudInvalida("Longitud de registro incorrecta.")
        return {
            c.nombre: c.decodificar(registro[c.inicio - 1: c.inicio - 1 + c.longitud])
            for c in self.campos
        }
