"""Pruebas del extractor de reglas con árbol de decisión (T025)."""

import numpy as np
import pandas as pd

from ghostmind.extractor import Extractor
from ghostmind.muestreo import solicitud_uniforme


def funcion(s):
    if s["puntaje_credito"] < 400:
        return "RECHAZADO"
    if s["tipo_empleo"] == "DESEMPLEADO":
        return "REVISION_MANUAL"
    return "APROBADO"


def datos_sinteticos(dic, n=400, semilla=0):
    rng = np.random.default_rng(semilla)
    filas = [solicitud_uniforme(dic, rng) for _ in range(n)]
    # pares en la frontera, como los que deja la bisección
    for tipo in ("EMPLEADO", "DESEMPLEADO"):
        for puntaje in (399, 400):
            for _ in range(3):
                filas.append(solicitud_uniforme(dic, rng, {"puntaje_credito": puntaje, "tipo_empleo": tipo}))
    tabla = pd.DataFrame(filas)
    tabla["decision"] = [funcion(f) for f in filas]
    return tabla


def test_hojas_reproducen_la_funcion(dic):
    modelo = Extractor(dic, semilla=1).ajustar(datos_sinteticos(dic))
    hojas = modelo.hojas()
    assert 3 <= len(hojas) <= 4
    rng = np.random.default_rng(99)
    for _ in range(2000):
        s = solicitud_uniforme(dic, rng)
        contenedoras = [h for h in hojas if h.caja.contiene(s)]
        assert len(contenedoras) == 1
        assert contenedoras[0].decision == funcion(s) == modelo.predecir_uno(s)


def test_umbral_exacto_en_las_cajas(dic):
    modelo = Extractor(dic, semilla=1).ajustar(datos_sinteticos(dic))
    limites = set()
    for hoja in modelo.hojas():
        lo, hi = hoja.caja.intervalos["puntaje_credito"]
        limites |= {lo, hi}
    assert {399, 400} <= limites
    assert any(d.campo == "puntaje_credito" and d.umbral == 399.5 for d in modelo.divisiones())


def test_categoria_como_conjunto(dic):
    modelo = Extractor(dic, semilla=1).ajustar(datos_sinteticos(dic))
    revision = [h for h in modelo.hojas() if h.decision == "REVISION_MANUAL"]
    assert len(revision) == 1
    assert revision[0].caja.conjuntos["tipo_empleo"] == ("DESEMPLEADO",)


def test_predecir_vectorizado_coincide(dic):
    datos = datos_sinteticos(dic)
    modelo = Extractor(dic, semilla=1).ajustar(datos)
    vector = modelo.predecir(datos)
    uno_a_uno = [modelo.predecir_uno(fila) for fila in datos[list(dic.nombres)].to_dict("records")]
    assert list(vector) == uno_a_uno


def test_determinismo(dic):
    datos = datos_sinteticos(dic)
    a = [(h.caja, h.decision) for h in Extractor(dic, semilla=5).ajustar(datos).hojas()]
    b = [(h.caja, h.decision) for h in Extractor(dic, semilla=5).ajustar(datos).hojas()]
    assert a == b


def test_umbrales_exactos_con_enteros_grandes(dic):
    """float32 no distingue 80.000.000 de 80.000.001; el extractor sí debe hacerlo."""
    rng = np.random.default_rng(3)
    filas = [solicitud_uniforme(dic, rng) for _ in range(200)]
    for monto in (80_000_000, 80_000_001):
        filas += [solicitud_uniforme(dic, rng, {"monto": monto}) for _ in range(5)]
    tabla = pd.DataFrame(filas)
    tabla["decision"] = np.where(tabla["monto"] > 80_000_000, "REVISION_MANUAL", "APROBADO")
    modelo = Extractor(dic, semilla=1).ajustar(tabla)
    limites = {h.caja.intervalos["monto"] for h in modelo.hojas()}
    assert limites == {(1_000_000, 80_000_000), (80_000_001, 150_000_000)}
    assert modelo.predecir_uno(dict(filas[0], monto=80_000_001)) == "REVISION_MANUAL"
    assert modelo.predecir_uno(dict(filas[0], monto=80_000_000)) == "APROBADO"
