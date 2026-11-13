"""Evaluación del experimento de GhostMind IA (FR-022 a FR-025).

Uso desde la raíz del repositorio:

    python -m evaluacion.experimento

1. Descubre las reglas del legacy con la semilla principal (42) y un presupuesto de 20.000 consultas.
2. Repite los casos registrados sobre la versión modernizada (verificador diferencial).
3. Calcula C1, C2, C3 y C5 con las definiciones de la especificación, más las consultas usadas.
4. Repite todo con las semillas de robustez (1 a 5).
5. Escribe ``resultados/metricas.json``, ``metricas.md``, ``robustez.json``, ``robustez.md`` y
   ``catalogo_semilla42.json``.

Ninguna cifra se escribe a mano: todo sale de esta ejecución y se repite igual con las mismas
semillas (salvo fechas y tiempos).
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
import streamlit

import ghostmind
from evaluacion.metricas import (
    CASOS_C3,
    METAS,
    MUESTRAS_POR_REGLA,
    SEMILLA_C3,
    UMBRAL_FIDELIDAD_LOCAL,
    UMBRAL_PUREZA,
    PredictorReglas,
    calcular_c1,
    calcular_c2,
    calcular_c3,
    calcular_c5,
    evaluar_regla_reportada,
)
from evaluacion.verdad import Verdad, cargar_alteraciones
from ghostmind.catalogo import exportar_json
from ghostmind.diccionario import RAIZ, Diccionario
from ghostmind.explorador import Explorador, Parametros
from ghostmind.registro import Registro
from ghostmind.reglas import Caja
from ghostmind.verificador import Verificador
from legacy.crdapr01 import CRDAPR01 as LEGACY

SEMILLA_PRINCIPAL = 42
SEMILLAS_ROBUSTEZ = (1, 2, 3, 4, 5)
PRESUPUESTO = 20_000
SALIDA = RAIZ / "resultados"
BD_EXPERIMENTO = RAIZ / "datos" / "experimento.sqlite"


def _relativa(ruta: Path) -> str:
    """Ruta relativa al repositorio, para no publicar rutas personales de la máquina."""
    try:
        return Path(ruta).resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return Path(ruta).name


def _git(*argumentos: str) -> str | None:
    try:
        salida = subprocess.run(["git", *argumentos], cwd=RAIZ, capture_output=True, text=True, timeout=10)
        return salida.stdout.strip() if salida.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _commit() -> str | None:
    return _git("rev-parse", "--short", "HEAD") or None


def _cambios_sin_commit() -> bool | None:
    """True si el código tiene cambios sin commit (sin contar resultados/)."""
    estado = _git("status", "--porcelain", "--", ".", ":(exclude)resultados")
    return None if estado is None else bool(estado)


def versiones() -> dict[str, Any]:
    return {
        "ghostmind": ghostmind.__version__,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
        "streamlit": streamlit.__version__,
        "commit": _commit(),
        "cambios_sin_commit": _cambios_sin_commit(),
    }


def evaluar_semilla(registro: Registro, dic: Diccionario, verdad: Verdad, alteraciones: list[dict],
                    semilla: int, presupuesto: int, n_muestras: int, n_c3: int) -> dict[str, Any]:
    """Descubrimiento, verificación y métricas para una semilla."""
    inicio = time.perf_counter()
    resultado = Explorador(dic, registro, "legacy", semilla, Parametros(presupuesto=presupuesto)).descubrir()
    duracion_descubrimiento = time.perf_counter() - inicio
    verificacion = Verificador(dic, registro, "modernizado").verificar(resultado.ejecucion_id)

    reglas = registro.reglas(resultado.ejecucion_id)
    rng_pureza = np.random.default_rng([semilla, 1])
    detalle_c2 = []
    for r in reglas:
        evaluacion = evaluar_regla_reportada(Caja.desde_condiciones(dic, r["condiciones"]), r["decision"],
                                             verdad, dic, rng_pureza, n_muestras)
        detalle_c2.append({"codigo": r["codigo"], "decision": r["decision"], "estado": r["estado"],
                           "confianza": round(r["confianza"], 4), "texto_negocio": r["texto_negocio"],
                           **evaluacion})
    c2 = calcular_c2(detalle_c2)
    c2["detalle"] = detalle_c2

    predecir = PredictorReglas(reglas, dic)
    c1 = calcular_c1(verdad, detalle_c2, predecir, dic, np.random.default_rng([semilla, 2]), n_muestras)
    casos = registro.casos(resultado.ejecucion_id)
    registrados = {tuple(fila) for fila in casos[list(dic.nombres)].itertuples(index=False)}
    c3 = calcular_c3(predecir, dic, LEGACY, n_c3, SEMILLA_C3, registrados)
    c5 = calcular_c5(registro.diferencias(verificacion.ejecucion_id), verdad, alteraciones)
    umbrales = registro.umbrales(resultado.ejecucion_id)

    return {
        "semilla": semilla,
        "descubrimiento": {
            "ejecucion_id": resultado.ejecucion_id,
            "consultas": resultado.consultas,
            "presupuesto": presupuesto,
            "rondas": resultado.rondas,
            "motivo_parada": resultado.motivo,
            "reglas_reportadas": len(reglas),
            "reglas_corroboradas": sum(r["estado"] == "corroborada" for r in reglas),
            "umbrales_confirmados": [
                {"campo": c, "valor_cambio": int(v)} for c, v in sorted(zip(umbrales["campo"], umbrales["valor_cambio"]))
            ],
            "duracion_s": round(duracion_descubrimiento, 2),
        },
        "verificacion": {
            "ejecucion_id": verificacion.ejecucion_id,
            "objetivo": verificacion.objetivo,
            "casos_repetidos": verificacion.casos_repetidos,
            "consultas": verificacion.consultas,
            "diferencias": verificacion.diferencias,
            "reglas_con_diferencias": [r.codigo for r in verificacion.reglas_con_diferencias],
        },
        "criterios": {
            "C1": c1,
            "C2": c2,
            "C3": c3,
            "C4": {"estado": "pendiente",
                   "nota": "Se mide con especialistas usando evaluacion/instrumento_c4/.",
                   "meta": "dos de cada tres respuestas correctas y promedio de utilidad de 4 o más"},
            "C5": c5,
        },
    }


# Formato en español

TIPOS = {"fosil": "Fósil", "general": "General", "excepcion": "Excepción", "excepcion_rara": "Excepción rara"}


def pct(valor: float) -> str:
    return f"{valor * 100:.1f} %".replace(".", ",")


def miles(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def si_no(valor: bool) -> str:
    return "Sí" if valor else "No"


def tabla_md(encabezados: list[str], filas: list[list[Any]]) -> str:
    lineas = ["| " + " | ".join(encabezados) + " |", "|" + "|".join("---" for _ in encabezados) + "|"]
    lineas += ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas]
    return "\n".join(lineas)


def escribir_metricas_md(datos: dict[str, Any], ruta: Path) -> None:
    p = datos["principal"]
    c = p["criterios"]
    d = p["descubrimiento"]
    v = p["verificacion"]
    partes = [
        "# Resultados del experimento de GhostMind IA",
        "",
        f"Generado por `python -m evaluacion.experimento` el {datos['generado'][:10]}. Semilla principal "
        f"{p['semilla']}; presupuesto de {miles(d['presupuesto'])} consultas. Todas las cifras salen de esta "
        "ejecución y se repiten iguales al volver a ejecutar la orden (salvo fechas y tiempos).",
        "",
        "## Criterios de éxito",
        "",
        tabla_md(
            ["Criterio", "Meta (fijada antes de las pruebas)", "Resultado", "¿Cumple?"],
            [
                ["C1. Cobertura", "Al menos 80 % de las 10 reglas plantadas",
                 f"{pct(c['C1']['valor'])} ({c['C1']['recuperadas']} de {c['C1']['total']})", si_no(c["C1"]["cumple"])],
                ["C2. Precisión", "Al menos 90 % de las reglas reportadas existen",
                 f"{pct(c['C2']['valor'])} ({c['C2']['existen']} de {c['C2']['reportadas']})", si_no(c["C2"]["cumple"])],
                ["C3. Fidelidad", f"Al menos 95 % en {miles(c['C3']['casos'])} casos nuevos",
                 f"{pct(c['C3']['valor'])} ({miles(c['C3']['coinciden'])} de {miles(c['C3']['casos'])})",
                 si_no(c["C3"]["cumple"])],
                ["C4. Utilidad para especialistas", "2 de cada 3 respuestas correctas y promedio de 4 o más",
                 "Pendiente: se mide con usuarios (evaluacion/instrumento_c4/)", "Pendiente"],
                ["C5. Detección de cambios", "100 % de las reglas alteradas",
                 f"{pct(c['C5']['valor'])} ({c['C5']['detectadas']} de {c['C5']['total']})", si_no(c["C5"]["cumple"])],
            ],
        ),
        "",
        "## Costo en consultas",
        "",
        tabla_md(
            ["Medida", "Valor"],
            [
                ["Consultas al legacy en el descubrimiento", f"{miles(d['consultas'])} de {miles(d['presupuesto'])}"],
                ["Rondas", d["rondas"]],
                ["Motivo de parada", d["motivo_parada"]],
                ["Tiempo del descubrimiento", f"{str(d['duracion_s']).replace('.', ',')} s"],
                ["Consultas a la versión modernizada en la verificación", miles(v["consultas"])],
                ["Reglas reportadas (corroboradas)", f"{d['reglas_reportadas']} ({d['reglas_corroboradas']})"],
            ],
        ),
        "",
        "## C1. Recuperación de cada regla plantada",
        "",
        f"Una regla plantada se recupera si al menos una regla reportada que existe está asociada a ella y, "
        f"en {miles(datos['configuracion']['muestras_por_regla'])} solicitudes uniformes de su región efectiva, "
        f"las reglas de GhostMind predicen su decisión en al menos {pct(UMBRAL_FIDELIDAD_LOCAL)}.",
        "",
        tabla_md(
            ["Regla", "Tipo", "Descripción", "Reglas de GhostMind asociadas", "Fidelidad local", "Recuperada"],
            [[x["regla"], TIPOS.get(x["tipo"], x["tipo"]), x["descripcion"], ", ".join(x["reglas_asociadas"]) or "ninguna",
              pct(x["fidelidad_local"]), si_no(x["recuperada"])] for x in c["C1"]["detalle"]],
        ),
        "",
        "## C2. Precisión de cada regla reportada",
        "",
        f"Una regla reportada existe si en {miles(datos['configuracion']['muestras_por_regla'])} solicitudes "
        f"uniformes dentro de su región el legacy toma su decisión en al menos {pct(UMBRAL_PUREZA)} de los casos.",
        "",
        tabla_md(
            ["Código", "Decisión", "Estado", "Pureza", "Existe", "Asociada a"],
            [[x["codigo"], x["decision"], x["estado"], pct(x["pureza"]), si_no(x["existe"]), x["asociada"]]
             for x in c["C2"]["detalle"]],
        ),
        "",
        "## C3. Fidelidad en casos nuevos",
        "",
        f"{miles(c['C3']['casos'])} solicitudes uniformes generadas con la semilla {c['C3']['semilla']}, "
        f"distinta de la del descubrimiento. Coinciden {miles(c['C3']['coinciden'])}. "
        f"De esas solicitudes, {c['C3']['casos_en_registro']} coinciden por azar con casos del registro.",
        "",
        "## C5. Detección de las reglas alteradas",
        "",
        f"La verificación repitió {miles(v['casos_repetidos'])} casos sobre la versión modernizada y encontró "
        f"{miles(v['diferencias'])} diferencias en las reglas {', '.join(v['reglas_con_diferencias']) or 'ninguna'}. "
        "Una diferencia se atribuye a una alteración si esa alteración, aplicada sola, cambia la decisión del caso.",
        "",
        tabla_md(
            ["Alteración", "Regla", "Descripción", "Diferencias atribuidas", "Detectada"],
            [[x["alteracion"], x["regla"], x["descripcion"], miles(x["diferencias_atribuidas"]), si_no(x["detectada"])]
             for x in c["C5"]["detalle"]],
        ),
        "",
        "## Umbrales confirmados por bisección",
        "",
        tabla_md(["Campo", "Primer valor con la nueva decisión"],
                 [[datos["etiquetas"].get(u["campo"], u["campo"]), miles(u["valor_cambio"])]
                  for u in d["umbrales_confirmados"]]),
        "",
        "## Configuración y versiones",
        "",
        tabla_md(["Parámetro", "Valor"], filas_configuracion(datos)),
        "",
        "La robustez con otras semillas está en `robustez.md`.",
        "",
    ]
    ruta.write_text("\n".join(partes), encoding="utf-8")


def filas_configuracion(datos: dict[str, Any]) -> list[list[Any]]:
    k = datos["configuracion"]
    v = datos["versiones"]
    commit = f"{v['commit']} (con cambios sin commit)" if v.get("cambios_sin_commit") else str(v["commit"])
    return [
        ["Semilla principal", k["semilla_principal"]],
        ["Semillas de robustez", ", ".join(str(s) for s in k["semillas_robustez"]) or "ninguna"],
        ["Presupuesto de consultas", miles(k["presupuesto"])],
        ["Máximo de rondas", k["max_rondas"]],
        ["Solicitudes por regla (pureza y fidelidad local)", miles(k["muestras_por_regla"])],
        ["Casos nuevos para C3 (semilla)", f"{miles(k['casos_c3'])} ({k['semilla_c3']})"],
        ["Umbral de pureza / de fidelidad local", f"{pct(k['umbral_pureza'])} / {pct(k['umbral_fidelidad_local'])}"],
        ["Metas", ", ".join(f"{c} {pct(m)}" for c, m in k["metas"].items())],
        ["Base de evidencia", k["base_de_evidencia"]],
        ["Versión de GhostMind", v["ghostmind"]],
        ["Commit del código", commit],
        ["Python / numpy / pandas / scikit-learn / Streamlit",
         f"{v['python']} / {v['numpy']} / {v['pandas']} / {v['scikit_learn']} / {v['streamlit']}"],
    ]


def fila_resumen(r: dict[str, Any]) -> dict[str, Any]:
    c = r["criterios"]
    rara = next(x for x in c["C1"]["detalle"] if x["tipo"] == "excepcion_rara")
    return {
        "semilla": r["semilla"],
        "consultas": r["descubrimiento"]["consultas"],
        "rondas": r["descubrimiento"]["rondas"],
        "motivo_parada": r["descubrimiento"]["motivo_parada"],
        "reglas_reportadas": r["descubrimiento"]["reglas_reportadas"],
        "C1": c["C1"]["valor"],
        "C2": c["C2"]["valor"],
        "C3": c["C3"]["valor"],
        "C5": c["C5"]["valor"],
        "regla_rara_recuperada": rara["recuperada"],
    }


def escribir_robustez(datos: dict[str, Any], ruta_json: Path, ruta_md: Path) -> None:
    filas = [fila_resumen(datos["principal"])] + [fila_resumen(r) for r in datos["robustez"]]
    resumen = {}
    for clave in ("consultas", "rondas", "reglas_reportadas", "C1", "C2", "C3", "C5"):
        valores = [f[clave] for f in filas]
        resumen[clave] = {"minimo": min(valores), "promedio": float(np.mean(valores)), "maximo": max(valores)}
    contenido = {"generado": datos["generado"], "semillas": [f["semilla"] for f in filas], "filas": filas,
                 "resumen": resumen,
                 "nota": "Información de robustez. Las metas se evalúan sobre la semilla principal."}
    ruta_json.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    nombres = {"consultas": "Consultas", "rondas": "Rondas", "reglas_reportadas": "Reglas reportadas"}

    def celda(clave, valor):
        if clave.startswith("C"):
            return pct(valor)
        if clave == "consultas":
            return miles(int(round(valor)))
        return str(round(valor, 1)).replace(".", ",")

    md = [
        "# Robustez del experimento con otras semillas",
        "",
        f"Generado por `python -m evaluacion.experimento` el {datos['generado'][:10]}. Es información "
        "complementaria: las metas de los criterios se evalúan sobre la semilla principal (42).",
        "",
        tabla_md(
            ["Semilla", "Consultas", "Rondas", "Motivo de parada", "Reglas", "C1", "C2", "C3", "C5",
             "Regla rara (R03) recuperada"],
            [[f["semilla"] if f["semilla"] != SEMILLA_PRINCIPAL else f"{f['semilla']} (principal)",
              miles(f["consultas"]), f["rondas"], f["motivo_parada"], f["reglas_reportadas"], pct(f["C1"]),
              pct(f["C2"]), pct(f["C3"]), pct(f["C5"]), si_no(f["regla_rara_recuperada"])] for f in filas],
        ),
        "",
        "## Resumen",
        "",
        tabla_md(
            ["Medida", "Mínimo", "Promedio", "Máximo"],
            [[nombres.get(clave, clave), celda(clave, r["minimo"]), celda(clave, r["promedio"]),
              celda(clave, r["maximo"])] for clave, r in resumen.items()],
        ),
        "",
    ]
    ruta_md.write_text("\n".join(md), encoding="utf-8")


def ejecutar_experimento(salida: Path | str = SALIDA, db: Path | str = BD_EXPERIMENTO,
                         presupuesto: int = PRESUPUESTO, semilla: int = SEMILLA_PRINCIPAL,
                         semillas_robustez: tuple[int, ...] = SEMILLAS_ROBUSTEZ,
                         n_muestras: int = MUESTRAS_POR_REGLA, n_c3: int = CASOS_C3,
                         informar=print) -> dict[str, Any]:
    salida, db = Path(salida), Path(db)
    salida.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()  # base nueva: el experimento es reproducible desde cero
    inicio = time.perf_counter()
    dic = Diccionario.cargar()
    verdad = Verdad.cargar()
    alteraciones = cargar_alteraciones()
    registro = Registro(db, dic)
    try:
        informar(f"Semilla principal {semilla}: descubrimiento, verificación y métricas...")
        principal = evaluar_semilla(registro, dic, verdad, alteraciones, semilla, presupuesto, n_muestras, n_c3)
        exportar_json(registro, principal["descubrimiento"]["ejecucion_id"], salida / f"catalogo_semilla{semilla}.json")
        robustez = []
        for s in semillas_robustez:
            informar(f"Semilla de robustez {s}...")
            robustez.append(evaluar_semilla(registro, dic, verdad, alteraciones, s, presupuesto, n_muestras, n_c3))
    finally:
        registro.cerrar()

    datos = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "duracion_total_s": round(time.perf_counter() - inicio, 1),
        "configuracion": {
            "semilla_principal": semilla,
            "semillas_robustez": list(semillas_robustez),
            "presupuesto": presupuesto,
            "max_rondas": Parametros().max_rondas,
            "muestras_por_regla": n_muestras,
            "casos_c3": n_c3,
            "semilla_c3": SEMILLA_C3,
            "umbral_pureza": UMBRAL_PUREZA,
            "umbral_fidelidad_local": UMBRAL_FIDELIDAD_LOCAL,
            "metas": METAS,
            "base_de_evidencia": _relativa(db),
        },
        "versiones": versiones(),
        "etiquetas": {c.nombre: c.etiqueta.capitalize() for c in dic.campos},
        "principal": principal,
        "robustez": robustez,
    }
    (salida / "metricas.json").write_text(
        json.dumps({k: v for k, v in datos.items() if k != "robustez"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    escribir_metricas_md(datos, salida / "metricas.md")
    escribir_robustez(datos, salida / "robustez.json", salida / "robustez.md")
    return datos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evaluacion.experimento",
                                     description="Evalúa GhostMind con los criterios C1, C2, C3 y C5.")
    parser.add_argument("--salida", default=str(SALIDA))
    parser.add_argument("--db", default=str(BD_EXPERIMENTO))
    parser.add_argument("--presupuesto", type=int, default=PRESUPUESTO)
    parser.add_argument("--semilla", type=int, default=SEMILLA_PRINCIPAL)
    parser.add_argument("--robustez", type=int, nargs="*", default=list(SEMILLAS_ROBUSTEZ))
    parser.add_argument("--muestras", type=int, default=MUESTRAS_POR_REGLA)
    parser.add_argument("--casos-c3", type=int, default=CASOS_C3)
    args = parser.parse_args(argv)
    datos = ejecutar_experimento(args.salida, args.db, args.presupuesto, args.semilla, tuple(args.robustez),
                                 args.muestras, args.casos_c3)
    c = datos["principal"]["criterios"]
    print()
    print(f"C1 cobertura: {pct(c['C1']['valor'])} | C2 precisión: {pct(c['C2']['valor'])} | "
          f"C3 fidelidad: {pct(c['C3']['valor'])} | C5 detección: {pct(c['C5']['valor'])}")
    print(f"Consultas del descubrimiento: {miles(datos['principal']['descubrimiento']['consultas'])}")
    print(f"Resultados escritos en {_relativa(Path(args.salida))}/ ({datos['duracion_total_s']} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
