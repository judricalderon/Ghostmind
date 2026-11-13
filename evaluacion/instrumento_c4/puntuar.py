"""Califica las respuestas del instrumento de C4.

Uso: ``python -m evaluacion.instrumento_c4.puntuar respuestas.csv [--salida c4.json]``

C4 se cumple si la proporción total de respuestas correctas es de al menos 2/3 y la utilidad
promedio (U1) es de 4 o más sobre 5. Una respuesta vacía cuenta como incorrecta.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
from pathlib import Path

from evaluacion.instrumento_c4.generar import CARPETA, OPCIONES, cargar_preguntas

META_CORRECTAS = 2 / 3
META_UTILIDAD = 4.0


def normalizar(respuesta: str) -> str:
    texto = unicodedata.normalize("NFKD", (respuesta or "").strip().upper())
    texto = "".join(c for c in texto if not unicodedata.combining(c)).replace(" ", "_")
    return OPCIONES.get(texto, texto)


def puntuar(ruta_csv: Path | str, clave: dict | None = None) -> dict:
    definicion = cargar_preguntas()
    clave = clave or json.loads((CARPETA / "clave.json").read_text(encoding="utf-8"))
    preguntas = [p["id"] for p in definicion["preguntas"]]
    valoraciones = [u["id"] for u in definicion["valoraciones"]]
    utilidad = next(u["id"] for u in definicion["valoraciones"] if u["metrica_c4"])
    with Path(ruta_csv).open(encoding="utf-8-sig", newline="") as archivo:
        filas = [f for f in csv.DictReader(archivo) if any((v or "").strip() for v in f.values())]
    if not filas:
        raise ValueError("El archivo no tiene respuestas.")

    participantes = []
    aciertos_por_pregunta = {p: 0 for p in preguntas}
    for fila in filas:
        correctas = 0
        for p in preguntas:
            if normalizar(fila.get(p, "")) == clave[p]["respuesta"]:
                correctas += 1
                aciertos_por_pregunta[p] += 1
        notas = {}
        for u in valoraciones:
            valor = (fila.get(u) or "").strip()
            if valor:
                numero = int(valor)
                if not 1 <= numero <= 5:
                    raise ValueError(f"{fila.get('participante')}: {u} debe estar entre 1 y 5")
                notas[u] = numero
        participantes.append({"participante": fila.get("participante", ""), "correctas": correctas,
                              "proporcion": correctas / len(preguntas), "valoraciones": notas})

    total_correctas = sum(p["correctas"] for p in participantes)
    proporcion = total_correctas / (len(preguntas) * len(participantes))
    promedios = {}
    for u in valoraciones:
        valores = [p["valoraciones"][u] for p in participantes if u in p["valoraciones"]]
        promedios[u] = sum(valores) / len(valores) if valores else None
    media_utilidad = promedios[utilidad]
    return {
        "participantes": len(participantes),
        "proporcion_correctas": proporcion,
        "utilidad_promedio": media_utilidad,
        "valoraciones_promedio": promedios,
        "aciertos_por_pregunta": {p: n / len(participantes) for p, n in aciertos_por_pregunta.items()},
        "cumple": proporcion >= META_CORRECTAS and media_utilidad is not None and media_utilidad >= META_UTILIDAD,
        "metas": {"proporcion_correctas": META_CORRECTAS, "utilidad_promedio": META_UTILIDAD},
        "detalle": participantes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evaluacion.instrumento_c4.puntuar")
    parser.add_argument("respuestas")
    parser.add_argument("--salida")
    args = parser.parse_args(argv)
    resultado = puntuar(args.respuestas)
    print(f"Participantes: {resultado['participantes']}")
    print(f"Respuestas correctas: {resultado['proporcion_correctas'] * 100:.1f} % (meta: 66,7 %)".replace(".", ",", 1))
    if resultado["utilidad_promedio"] is not None:
        print(f"Utilidad promedio (U1): {resultado['utilidad_promedio']:.2f} sobre 5 (meta: 4)".replace(".", ",", 1))
    print("C4 cumplido" if resultado["cumple"] else "C4 no cumplido")
    if args.salida:
        Path(args.salida).write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
