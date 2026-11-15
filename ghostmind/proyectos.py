"""Proyectos: cada sistema legacy con su diccionario, su base y sus cajas negras (Fase 9).

Lee ``sistemas/proyectos.json`` (contracts/proyectos.md). Un proyecto agrupa las cajas negras que
reciben el mismo registro, así que comparten diccionario de atributos y base de evidencia. Este
módulo solo lee la declaración; convertir un punto de entrada en una función es tarea exclusiva
del adaptador.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ghostmind.diccionario import RAIZ, Campo, Diccionario
from ghostmind.registro import ruta_por_defecto
from ghostmind.reglas import formato_miles

CARPETA_SISTEMAS = RAIZ / "sistemas"
RUTA_PROYECTOS = CARPETA_SISTEMAS / "proyectos.json"
PROYECTO_POR_DEFECTO = "credito"


class ProyectoDesconocido(KeyError):
    """El proyecto no está declarado en ``sistemas/proyectos.json``."""

    def __str__(self) -> str:  # KeyError muestra el mensaje entre comillas
        return str(self.args[0]) if self.args else ""


@dataclass(frozen=True)
class CajaNegra:
    nombre: str
    punto_de_entrada: str
    descripcion: str = ""


@dataclass(frozen=True)
class Proyecto:
    clave: str
    nombre: str
    descripcion: str
    ruta_diccionario: Path
    base: str | None
    cajas_negras: dict[str, CajaNegra]

    def diccionario(self) -> Diccionario:
        return Diccionario.cargar(self.ruta_diccionario)

    def ruta_base(self) -> Path:
        """Base principal si el proyecto no declara ``base``; si no, ese archivo junto a ella."""
        principal = ruta_por_defecto()
        return principal if self.base is None else principal.parent / self.base


def _caja_negra(nombre: str, valor: str | dict) -> CajaNegra:
    if isinstance(valor, str):
        return CajaNegra(nombre, valor)
    return CajaNegra(nombre, valor["punto_de_entrada"], valor.get("descripcion", ""))


def cargar_proyectos(ruta: Path | str = RUTA_PROYECTOS) -> dict[str, Proyecto]:
    """Proyectos declarados, en el orden del archivo, con sus validaciones."""
    ruta = Path(ruta)
    crudos = json.loads(ruta.read_text(encoding="utf-8"))
    if not crudos:
        raise ValueError(f"{ruta.name} no declara ningún proyecto.")
    proyectos: dict[str, Proyecto] = {}
    for clave, datos in crudos.items():
        cajas = {nombre: _caja_negra(nombre, valor) for nombre, valor in datos.get("cajas_negras", {}).items()}
        if not cajas:
            raise ValueError(f"El proyecto {clave!r} no tiene cajas negras.")
        ruta_diccionario = CARPETA_SISTEMAS / datos["diccionario"]
        if not ruta_diccionario.is_file():
            raise ValueError(f"El proyecto {clave!r} apunta a un diccionario que no existe: {datos['diccionario']}")
        proyectos[clave] = Proyecto(
            clave=clave,
            nombre=datos.get("nombre", clave),
            descripcion=datos.get("descripcion", ""),
            ruta_diccionario=ruta_diccionario,
            base=datos.get("base"),
            cajas_negras=cajas,
        )
    bases = [p.base for p in proyectos.values()]
    if bases.count(None) > 1 or len(set(bases)) != len(bases):
        raise ValueError("Cada proyecto necesita su propia base: solo uno puede usar la base principal "
                         "y dos proyectos no pueden compartir archivo.")
    return proyectos


def obtener_proyecto(clave: str = PROYECTO_POR_DEFECTO, ruta: Path | str = RUTA_PROYECTOS) -> Proyecto:
    proyectos = cargar_proyectos(ruta)
    if clave not in proyectos:
        raise ProyectoDesconocido(f"Proyecto desconocido: {clave!r}. Opciones: {list(proyectos)}")
    return proyectos[clave]


def limites(campo: Campo) -> str:
    """Rango con su unidad (enteros) o lista de valores permitidos (categóricos)."""
    if campo.es_numerico:
        return f"{formato_miles(campo.minimo)} a {formato_miles(campo.maximo)} {campo.unidad or ''}".strip()
    return ", ".join(campo.etiqueta_valor(v) for v in campo.nombres_valores)


def posicion(campo: Campo) -> str:
    fin = campo.inicio + campo.longitud - 1
    return str(campo.inicio) if fin == campo.inicio else f"{campo.inicio} a {fin}"


def atributos(dic: Diccionario) -> list[dict[str, str]]:
    """Lo único que GhostMind sabe de las cajas negras de un proyecto, atributo por atributo."""
    return [{
        "Atributo": campo.etiqueta[:1].upper() + campo.etiqueta[1:],
        "Nombre técnico": campo.nombre,
        "Tipo": "Entero" if campo.es_numerico else "Categórico",
        "Límites o valores": limites(campo),
        "Posición en el registro": posicion(campo),
    } for campo in dic.campos]
