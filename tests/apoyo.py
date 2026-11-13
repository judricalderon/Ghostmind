"""Sistemas de prueba y ejecuciones pequeñas reutilizables."""

from ghostmind.explorador import Explorador, Parametros


def sistema_de_prueba(dic, funcion):
    """Convierte una función de solicitud en un sistema que recibe el registro de ancho fijo."""

    def punto_de_entrada(registro_texto):
        return funcion(dic.leer_registro(registro_texto))

    punto_de_entrada.__name__ = funcion.__name__
    return punto_de_entrada


def dos_reglas(s):
    if s["puntaje_credito"] < 437:
        return "RECHAZADO"
    if s["tipo_empleo"] == "DESEMPLEADO":
        return "REVISION_MANUAL"
    return "APROBADO"


def ejecucion_pequena(dic, registro, funcion=dos_reglas, semilla=7):
    """Descubrimiento rápido sobre un sistema de prueba; devuelve el resultado."""
    return Explorador(dic, registro, sistema_de_prueba(dic, funcion), semilla, Parametros()).descubrir()
