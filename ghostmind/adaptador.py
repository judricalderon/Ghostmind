"""Adaptador: único punto de contacto entre GhostMind y un sistema.

Valida la solicitud contra el diccionario, arma el registro de ancho fijo, llama al punto de
entrada del sistema, guarda el caso en el registro de evidencia y cuenta la consulta. Ningún otro
módulo de GhostMind llama a un sistema (contracts/adaptador.md).
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Callable

from ghostmind.diccionario import Diccionario, Solicitud
from ghostmind.proyectos import PROYECTO_POR_DEFECTO, RUTA_PROYECTOS, obtener_proyecto
from ghostmind.registro import ORIGENES, Registro

PuntoDeEntrada = Callable[[str], str]


class PresupuestoAgotado(RuntimeError):
    """Se alcanzó el número máximo de consultas de la ejecución."""


class ErrorDelSistema(RuntimeError):
    """El sistema falló o devolvió una respuesta que no está entre las decisiones posibles."""


class ObjetivoDesconocido(KeyError):
    """La caja negra no está declarada en el proyecto (``sistemas/proyectos.json``)."""

    def __str__(self) -> str:  # KeyError muestra el mensaje entre comillas
        return str(self.args[0]) if self.args else ""


def listar_objetivos(proyecto: str = PROYECTO_POR_DEFECTO,
                     ruta_proyectos: Path | str = RUTA_PROYECTOS) -> dict[str, str]:
    """Cajas negras del proyecto (nombres válidos para ``--objetivo``) con su descripción."""
    cajas = obtener_proyecto(proyecto, ruta_proyectos).cajas_negras
    return {nombre: caja.descripcion for nombre, caja in cajas.items()}


def resolver_objetivo(nombre: str, proyecto: str = PROYECTO_POR_DEFECTO,
                      ruta_proyectos: Path | str = RUTA_PROYECTOS) -> PuntoDeEntrada:
    """Obtiene el punto de entrada declarado para una caja negra del proyecto, sin leer su código."""
    cajas = obtener_proyecto(proyecto, ruta_proyectos).cajas_negras
    if nombre not in cajas:
        raise ObjetivoDesconocido(
            f"Caja negra desconocida en el proyecto {proyecto!r}: {nombre!r}. Opciones: {list(cajas)}")
    modulo, funcion = cajas[nombre].punto_de_entrada.split(":")
    return getattr(importlib.import_module(modulo), funcion)


def comprobar_diccionario(diccionario: Diccionario, proyecto: str = PROYECTO_POR_DEFECTO) -> None:
    """Evita consultar las cajas negras de un proyecto con el diccionario de otro."""
    esperado = obtener_proyecto(proyecto).diccionario()
    if (diccionario.nombres, diccionario.longitud_registro) != (esperado.nombres, esperado.longitud_registro):
        raise ValueError(f"El diccionario recibido no es el del proyecto {proyecto!r}.")


class Adaptador:
    """Envía solicitudes a un sistema y registra cada respuesta."""

    def __init__(self, diccionario: Diccionario, objetivo: str | PuntoDeEntrada, registro: Registro,
                 ejecucion_id: int, presupuesto: int, proyecto: str = PROYECTO_POR_DEFECTO):
        if presupuesto <= 0:
            raise ValueError("El presupuesto debe ser positivo.")
        self.diccionario = diccionario
        self.registro = registro
        self.ejecucion_id = ejecucion_id
        self.presupuesto = presupuesto
        if callable(objetivo):
            self.objetivo = getattr(objetivo, "__name__", "personalizado")
            self._sistema = objetivo
        else:
            comprobar_diccionario(diccionario, proyecto)
            self.objetivo = objetivo
            self._sistema = resolver_objetivo(objetivo, proyecto)
        self.consultas = registro.contar_casos(ejecucion_id)
        self.errores = 0

    @property
    def restantes(self) -> int:
        return self.presupuesto - self.consultas

    def consultar(self, solicitud: Solicitud, ronda: int, origen: str,
                  caso_base_id: int | None = None) -> str:
        """Devuelve la decisión del sistema; el caso queda registrado antes de devolverla."""
        if origen not in ORIGENES:
            raise ValueError(f"Origen de caso desconocido: {origen!r}")
        texto = self.diccionario.armar_registro(solicitud)  # valida la solicitud
        if self.restantes <= 0:
            raise PresupuestoAgotado(f"Se agotaron las {self.presupuesto} consultas.")

        self.consultas += 1
        decision: str | None = None
        error: str | None = None
        try:
            respuesta = self._sistema(texto)
        except Exception as exc:  # el sistema bajo prueba puede fallar de cualquier forma
            error = f"{type(exc).__name__}: {exc}"
        else:
            if respuesta in self.diccionario.decisiones:
                decision = respuesta
            else:
                error = f"Respuesta inesperada: {respuesta!r}"

        caso_id = self.registro.guardar_caso(
            self.ejecucion_id, self.consultas, ronda, origen, solicitud, decision, error, caso_base_id
        )
        self.ultimo_caso_id = caso_id
        if error is not None:
            self.errores += 1
            raise ErrorDelSistema(error)
        return decision
