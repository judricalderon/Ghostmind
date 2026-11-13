"""Órdenes de línea de comandos de GhostMind (contracts/cli.md).

Uso: ``python -m ghostmind <orden> [opciones]``.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

import numpy as np

from ghostmind.adaptador import Adaptador, ErrorDelSistema, ObjetivoDesconocido
from ghostmind.diccionario import Diccionario
from ghostmind.muestreo import PARAMETROS_POR_DEFECTO, muestreo_inicial
from ghostmind.registro import Registro, ruta_por_defecto


def _orden_muestrear(args: argparse.Namespace) -> int:
    dic = Diccionario.cargar()
    registro = Registro(args.db, dic)
    muestras = muestreo_inicial(dic, np.random.default_rng(args.semilla))
    presupuesto = len(muestras)
    eid = registro.crear_ejecucion(
        "descubrimiento", args.objetivo, args.semilla, presupuesto,
        parametros={"orden": "muestrear", "muestreo": PARAMETROS_POR_DEFECTO},
    )
    try:
        adaptador = Adaptador(dic, args.objetivo, registro, eid, presupuesto)
    except ObjetivoDesconocido as exc:
        print(exc, file=sys.stderr)
        return 2

    vistas: set[tuple] = set()
    decisiones: Counter = Counter()
    for origen, solicitud in muestras:
        clave = tuple(solicitud[n] for n in dic.nombres)
        if clave in vistas:
            continue
        vistas.add(clave)
        try:
            decisiones[adaptador.consultar(solicitud, ronda=0, origen=origen)] += 1
        except ErrorDelSistema:
            decisiones["ERROR"] += 1
    registro.cerrar_ejecucion(eid, adaptador.consultas, rondas=0, motivo_parada="completa")
    casos = registro.casos(eid)
    registro.cerrar()

    print(f"Ejecución {eid}: muestreo inicial sobre '{args.objetivo}' con semilla {args.semilla}")
    print(f"Consultas al sistema: {adaptador.consultas}")
    print("Casos por origen:")
    for origen, n in casos["origen"].value_counts().sort_index().items():
        print(f"  {origen:12s} {n:5d}")
    print("Decisiones observadas:")
    for decision, n in sorted(decisiones.items()):
        print(f"  {decision:16s} {n:5d}")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ghostmind",
                                     description="GhostMind IA: descubrimiento de reglas por caja negra.")
    ordenes = parser.add_subparsers(dest="orden", required=True)

    muestrear = ordenes.add_parser("muestrear", help="Solo el muestreo inicial (diagnóstico).")
    muestrear.add_argument("--objetivo", default="legacy")
    muestrear.add_argument("--semilla", type=int, default=42)
    muestrear.add_argument("--db", default=str(ruta_por_defecto()))
    muestrear.set_defaults(funcion=_orden_muestrear)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    return args.funcion(args)


if __name__ == "__main__":
    sys.exit(main())
