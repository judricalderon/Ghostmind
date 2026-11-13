"""Prueba de punta a punta del experimento con parámetros reducidos (T049)."""

import json

from evaluacion.experimento import ejecutar_experimento

ARCHIVOS = {"metricas.json", "metricas.md", "robustez.json", "robustez.md", "catalogo_semilla42.json"}


def sin_tiempos(objeto):
    """Quita fechas, duraciones y ids de ejecución para comparar dos corridas."""
    if isinstance(objeto, dict):
        return {k: sin_tiempos(v) for k, v in objeto.items()
                if k not in {"generado", "duracion_s", "duracion_total_s", "commit"}}
    if isinstance(objeto, list):
        return [sin_tiempos(v) for v in objeto]
    return objeto


def correr(tmp_path, nombre):
    salida = tmp_path / nombre
    datos = ejecutar_experimento(salida=salida, db=tmp_path / f"{nombre}.sqlite", presupuesto=2500,
                                 semillas_robustez=(1,), n_muestras=150, n_c3=400, informar=lambda *_: None)
    return salida, datos


def test_experimento_genera_resultados_reproducibles(tmp_path):
    salida, datos = correr(tmp_path, "a")
    assert ARCHIVOS <= {p.name for p in salida.iterdir()}
    metricas = json.loads((salida / "metricas.json").read_text(encoding="utf-8"))
    criterios = metricas["principal"]["criterios"]
    for clave in ("C1", "C2", "C3", "C5"):
        assert 0.0 <= criterios[clave]["valor"] <= 1.0
    assert criterios["C1"]["total"] == 10
    assert criterios["C4"]["estado"] == "pendiente"
    assert metricas["principal"]["descubrimiento"]["consultas"] <= 2500
    assert metricas["configuracion"]["base_de_evidencia"].endswith("a.sqlite")
    texto = (salida / "metricas.md").read_text(encoding="utf-8")
    assert "C1. Cobertura" in texto and "C5. Detección de cambios" in texto
    robustez = json.loads((salida / "robustez.json").read_text(encoding="utf-8"))
    assert robustez["semillas"] == [42, 1]

    _, otra = correr(tmp_path, "b")
    assert sin_tiempos(datos["principal"]) == sin_tiempos(otra["principal"])
    assert sin_tiempos(datos["robustez"]) == sin_tiempos(otra["robustez"])
