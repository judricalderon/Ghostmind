"""Órdenes de línea de comandos de GhostMind (contracts/cli.md).

Uso: ``python -m ghostmind <orden> [opciones]``.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter

import numpy as np

from ghostmind.adaptador import Adaptador, ErrorDelSistema, ObjetivoDesconocido
from ghostmind.catalogo import exportar_json
from ghostmind.diccionario import Diccionario
from ghostmind.explorador import Explorador, Parametros
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


def _porcentaje(valor: float) -> str:
    return f"{valor * 100:5.1f} %".replace(".", ",")


def _imprimir_reglas(reglas: list[dict]) -> None:
    print(f"{'Código':7s} {'Decisión':16s} {'Respaldo':>8s} {'Contra':>6s} {'Confianza':>9s}  "
          f"{'Estado':12s} Regla")
    for r in reglas:
        print(f"{r['codigo']:7s} {r['decision']:16s} {r['respaldo']:8d} {r['contraejemplos']:6d} "
              f"{_porcentaje(r['confianza']):>9s}  {r['estado']:12s} {r['texto_tecnico']}")


def _resumen_ejecucion(registro: Registro, eid: int) -> None:
    e = registro.ejecucion(eid)
    reglas = registro.reglas(eid)
    estados = Counter(r["estado"] for r in reglas)
    print(f"Ejecución {eid}: {e['tipo']} sobre '{e['objetivo']}' (semilla {e['semilla']}, "
          f"presupuesto {e['presupuesto']})")
    print(f"Rondas: {e['rondas']} | Consultas: {e['consultas']} | Motivo de parada: {e['motivo_parada']}")
    detalle = ", ".join(f"{estado}: {n}" for estado, n in sorted(estados.items()))
    print(f"Reglas: {len(reglas)} ({detalle})")
    print()
    _imprimir_reglas(reglas)


def _orden_descubrir(args: argparse.Namespace) -> int:
    dic = Diccionario.cargar()
    registro = Registro(args.db, dic)
    parametros = Parametros(presupuesto=args.presupuesto, max_rondas=args.max_rondas)
    inicio = time.perf_counter()
    try:
        resultado = Explorador(dic, registro, args.objetivo, args.semilla, parametros).descubrir()
    except ValueError as exc:
        print(f"Parámetros inválidos: {exc}", file=sys.stderr)
        registro.cerrar()
        return 2
    except ObjetivoDesconocido as exc:
        print(exc, file=sys.stderr)
        registro.cerrar()
        return 2
    duracion = time.perf_counter() - inicio
    _resumen_ejecucion(registro, resultado.ejecucion_id)
    print(f"\nTiempo de ejecución: {duracion:.1f} s")
    registro.cerrar()
    return 3 if resultado.motivo == "errores" else 0


def _orden_reglas(args: argparse.Namespace) -> int:
    registro = Registro(args.db)
    try:
        _resumen_ejecucion(registro, args.ejecucion)
    except KeyError as exc:
        print(exc, file=sys.stderr)
        return 2
    finally:
        registro.cerrar()
    return 0


def _orden_exportar(args: argparse.Namespace) -> int:
    registro = Registro(args.db)
    try:
        ruta = exportar_json(registro, args.ejecucion, args.salida)
    except KeyError as exc:
        print(exc, file=sys.stderr)
        return 2
    finally:
        registro.cerrar()
    print(f"Catálogo de la ejecución {args.ejecucion} exportado en {ruta}")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ghostmind",
                                     description="GhostMind IA: descubrimiento de reglas por caja negra.")
    ordenes = parser.add_subparsers(dest="orden", required=True)

    descubrir = ordenes.add_parser("descubrir", help="Descubre las reglas de un sistema.")
    descubrir.add_argument("--objetivo", default="legacy")
    descubrir.add_argument("--semilla", type=int, default=42)
    descubrir.add_argument("--presupuesto", type=int, default=20_000)
    descubrir.add_argument("--max-rondas", type=int, default=15)
    descubrir.add_argument("--db", default=str(ruta_por_defecto()))
    descubrir.set_defaults(funcion=_orden_descubrir)

    reglas = ordenes.add_parser("reglas", help="Muestra las reglas de una ejecución.")
    reglas.add_argument("--ejecucion", type=int, required=True)
    reglas.add_argument("--db", default=str(ruta_por_defecto()))
    reglas.set_defaults(funcion=_orden_reglas)

    exportar = ordenes.add_parser("exportar", help="Exporta el catálogo de una ejecución a JSON.")
    exportar.add_argument("--ejecucion", type=int, required=True)
    exportar.add_argument("--salida", required=True)
    exportar.add_argument("--db", default=str(ruta_por_defecto()))
    exportar.set_defaults(funcion=_orden_exportar)

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
