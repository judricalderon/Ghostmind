"""Genera el cuestionario y la clave de respuestas del instrumento de C4.

Uso: ``python -m evaluacion.instrumento_c4.generar``. La clave se calcula con las reglas verdaderas,
nunca a mano, para que no pueda contradecir al sistema.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from evaluacion.verdad import Verdad
from ghostmind.diccionario import Diccionario
from ghostmind.reglas import formato_miles

CARPETA = Path(__file__).resolve().parent
OPCIONES = {"A": "APROBADO", "B": "RECHAZADO", "C": "REVISION_MANUAL"}
TEXTO_OPCION = {"APROBADO": "Aprobado", "RECHAZADO": "Rechazado", "REVISION_MANUAL": "Revisión manual"}


def cargar_preguntas() -> dict:
    return json.loads((CARPETA / "preguntas.json").read_text(encoding="utf-8"))


def solicitud_de(definicion: dict, pregunta: dict) -> dict:
    return {**definicion["solicitud_base"], **pregunta.get("cambios", {})}


def describir(dic: Diccionario, solicitud: dict) -> str:
    partes = []
    for campo in dic.campos:
        valor = solicitud[campo.nombre]
        if campo.es_numerico:
            texto = f"{formato_miles(valor)} {campo.unidad}" if campo.unidad else formato_miles(valor)
        else:
            texto = campo.etiqueta_valor(valor)
        partes.append(f"{campo.etiqueta}: {texto}")
    return "; ".join(partes)


def calcular_clave(definicion: dict, verdad: Verdad) -> dict:
    clave = {}
    for p in definicion["preguntas"]:
        if p["tipo"] == "decision":
            decision, regla = verdad.evaluar(solicitud_de(definicion, p))
            clave[p["id"]] = {"respuesta": decision, "regla": regla}
        elif p["tipo"] == "campo_influye":
            influye = any(p["campo"] in r.condiciones for r in verdad.reglas)
            clave[p["id"]] = {"respuesta": "SI" if influye else "NO", "regla": None}
        else:
            raise ValueError(f"Tipo de pregunta desconocido: {p['tipo']!r}")
    return clave


def escribir_cuestionario(definicion: dict, dic: Diccionario, ruta: Path) -> None:
    lineas = [
        "# Cuestionario de utilidad del catálogo de GhostMind IA (criterio C4)",
        "",
        "## Instrucciones para quien aplica el cuestionario",
        "",
        "1. Participan entre 5 y 8 profesionales de software o especialistas del negocio que no hayan visto "
        "el código del sistema legacy ni las reglas verdaderas.",
        "2. Cada participante abre el catálogo (`streamlit run app/catalogo.py`) con la ejecución de la "
        "semilla 42 y tiene 20 minutos para responder usando solo el catálogo.",
        "3. Las respuestas se anotan en una copia de `plantilla_respuestas.csv` (una fila por participante) "
        "y se califican con `python -m evaluacion.instrumento_c4.puntuar respuestas.csv`.",
        "4. Meta de C4, fijada antes de la prueba: al menos dos de cada tres respuestas correctas en total y "
        "una utilidad promedio (U1) de 4 o más sobre 5.",
        "",
        "## Preguntas sobre el comportamiento del sistema",
        "",
        "Para cada solicitud, indique qué decide el sistema: **A** Aprobado, **B** Rechazado, "
        "**C** Revisión manual.",
        "",
    ]
    for p in definicion["preguntas"]:
        if p["tipo"] == "decision":
            lineas.append(f"**{p['id']}.** Solicitud con {describir(dic, solicitud_de(definicion, p))}.")
            lineas.append("")
            lineas.append("Respuesta: A / B / C")
        else:
            lineas.append(f"**{p['id']}.** {p['enunciado']}")
            lineas.append("")
            lineas.append("Respuesta: Sí / No")
        lineas.append("")
    lineas += [
        "## Valoración del catálogo",
        "",
        "Califique de 1 (nada) a 5 (totalmente).",
        "",
    ]
    for u in definicion["valoraciones"]:
        lineas.append(f"**{u['id']}.** {u['enunciado']} (1 a 5)")
        lineas.append("")
    lineas += ["**Comentario.** ¿Qué cambiaría del catálogo para que le sirviera más?", ""]
    ruta.write_text("\n".join(lineas), encoding="utf-8")


def escribir_plantilla(definicion: dict, ruta: Path) -> None:
    columnas = ["participante", "perfil"] + [p["id"] for p in definicion["preguntas"]]
    columnas += [u["id"] for u in definicion["valoraciones"]] + ["comentario"]
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        csv.writer(archivo).writerow(columnas)


def generar(carpeta: Path = CARPETA) -> dict:
    definicion = cargar_preguntas()
    dic = Diccionario.cargar()
    clave = calcular_clave(definicion, Verdad.cargar())
    (carpeta / "clave.json").write_text(json.dumps(clave, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    escribir_cuestionario(definicion, dic, carpeta / "cuestionario.md")
    escribir_plantilla(definicion, carpeta / "plantilla_respuestas.csv")
    return clave


if __name__ == "__main__":
    clave = generar()
    print(f"Cuestionario, clave ({len(clave)} preguntas) y plantilla escritos en {CARPETA.name}/")
