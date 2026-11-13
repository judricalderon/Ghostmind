"""Pruebas del explorador: bisección, contraejemplos, parada y determinismo (T026)."""

import numpy as np
import pytest

from ghostmind.__main__ import main
from ghostmind.explorador import Explorador, Parametros
from ghostmind.muestreo import solicitud_uniforme
from ghostmind.registro import Registro


def sistema_de_prueba(dic, funcion):
    """Convierte una función de solicitud en un sistema que recibe el registro de ancho fijo."""

    def punto_de_entrada(registro_texto):
        return funcion(dic.leer_registro(registro_texto))

    return punto_de_entrada


def un_umbral(s):
    return "RECHAZADO" if s["puntaje_credito"] < 437 else "APROBADO"


def dos_umbrales_y_categoria(s):
    if s["puntaje_credito"] < 437:
        return "RECHAZADO"
    if s["tipo_empleo"] == "INDEPENDIENTE" and s["monto"] > 90_000_000:
        return "REVISION_MANUAL"
    return "APROBADO"


def descubrir(dic, registro, objetivo, semilla=7, **parametros):
    return Explorador(dic, registro, objetivo, semilla, Parametros(**parametros)).descubrir()


def test_un_umbral_se_encuentra_exacto(dic, registro):
    resultado = descubrir(dic, registro, sistema_de_prueba(dic, un_umbral))
    assert resultado.motivo == "estable"
    assert len(resultado.reglas) == 2
    por_decision = {r.decision: r for r in resultado.reglas}
    assert por_decision["RECHAZADO"].caja.intervalos["puntaje_credito"] == (150, 436)
    assert por_decision["APROBADO"].caja.intervalos["puntaje_credito"] == (437, 950)
    assert all(r.estado == "corroborada" for r in resultado.reglas)
    assert {"campo": "puntaje_credito", "valor_cambio": 437} in por_decision["APROBADO"].umbrales_confirmados
    umbrales = registro.umbrales(resultado.ejecucion_id)
    assert ((umbrales["campo"] == "puntaje_credito") & (umbrales["valor_cambio"] == 437)).any()
    assert resultado.consultas == registro.contar_casos(resultado.ejecucion_id) <= 20_000


def test_dos_umbrales_y_categoria(dic, registro):
    funcion = dos_umbrales_y_categoria
    resultado = descubrir(dic, registro, sistema_de_prueba(dic, funcion))
    rng = np.random.default_rng(123)
    aciertos = sum(
        resultado.modelo.predecir_uno(s) == funcion(s)
        for s in (solicitud_uniforme(dic, rng) for _ in range(3000))
    )
    assert aciertos / 3000 >= 0.99
    umbrales = registro.umbrales(resultado.ejecucion_id)
    assert ((umbrales["campo"] == "monto") & (umbrales["valor_cambio"] == 90_000_001)).any()
    origenes = set(registro.casos(resultado.ejecucion_id)["origen"])
    assert {"aleatorio", "limite", "categoria", "biseccion", "contraejemplo"} <= origenes


def test_reglas_y_evidencia_quedan_en_el_registro(dic, registro):
    resultado = descubrir(dic, registro, sistema_de_prueba(dic, un_umbral))
    guardadas = registro.reglas(resultado.ejecucion_id)
    assert [r["codigo"] for r in guardadas] == [r.codigo for r in resultado.reglas]
    for regla in guardadas:
        enlaces = registro.casos_de_regla(regla["id"])
        assert len(enlaces) == regla["respaldo"] + regla["contraejemplos"]
    ejecucion = registro.ejecucion(resultado.ejecucion_id)
    assert ejecucion["motivo_parada"] == "estable"
    assert ejecucion["consultas"] == resultado.consultas
    assert len(registro.rondas(resultado.ejecucion_id)) == resultado.rondas + 1


def test_presupuesto_agotado(dic, registro):
    resultado = descubrir(dic, registro, "legacy", presupuesto=800)
    assert resultado.motivo == "presupuesto_agotado"
    assert resultado.consultas <= 800
    assert resultado.reglas


def test_presupuesto_menor_que_el_muestreo_inicial(dic, registro):
    with pytest.raises(ValueError):
        descubrir(dic, registro, "legacy", presupuesto=500)
    assert all(registro.contar_casos(e["id"]) == 0 for e in registro.ejecuciones())


def test_parada_por_errores(dic, registro):
    def inestable(s):
        return "???" if s["edad"] == 33 else un_umbral(s)

    resultado = descubrir(dic, registro, sistema_de_prueba(dic, inestable))
    assert resultado.motivo == "errores"


def test_maximo_de_rondas(dic, registro):
    resultado = descubrir(dic, registro, "legacy", max_rondas=1)
    assert resultado.rondas <= 1
    assert resultado.motivo in {"estable", "max_rondas"}


def test_determinismo_con_el_legacy(dic, tmp_path):
    textos = []
    for nombre in ("a", "b"):
        reg = Registro(tmp_path / f"{nombre}.sqlite", dic)
        resultado = descubrir(dic, reg, "legacy", semilla=42, presupuesto=4000)
        textos.append((resultado.consultas, resultado.motivo, [r.texto_tecnico() for r in resultado.reglas]))
        reg.cerrar()
    assert textos[0] == textos[1]


def test_ordenes_descubrir_y_reglas(tmp_path, capsys):
    ruta = str(tmp_path / "cli.sqlite")
    assert main(["descubrir", "--objetivo", "legacy", "--semilla", "42", "--presupuesto", "3000",
                 "--db", ruta]) == 0
    assert main(["reglas", "--ejecucion", "1", "--db", ruta]) == 0
    salida = capsys.readouterr().out
    assert "GM-01" in salida
    assert "Motivo de parada" in salida
    assert main(["descubrir", "--presupuesto", "100", "--db", ruta]) == 2


def test_descubrimiento_completo_del_legacy(dic, registro):
    """Ejecución con los parámetros por defecto: invariantes estructurales, sin mirar la verdad."""
    import time

    inicio = time.perf_counter()
    resultado = descubrir(dic, registro, "legacy", semilla=42)
    assert time.perf_counter() - inicio < 600  # SC-007: menos de 10 minutos
    assert resultado.motivo in {"estable", "presupuesto_agotado", "max_rondas"}
    assert resultado.consultas <= 20_000
    assert resultado.consultas == registro.contar_casos(resultado.ejecucion_id)
    assert all(not r.caja.vacia for r in resultado.reglas)
    assert all(r.estado in {"hipotesis", "corroborada"} for r in resultado.reglas)
    # Las reglas forman una partición: cada solicitud cae en exactamente una regla.
    rng = np.random.default_rng(2024)
    for _ in range(2000):
        s = solicitud_uniforme(dic, rng)
        assert sum(r.caja.contiene(s) for r in resultado.reglas) == 1
    # Ningún campo se restringe fuera de su dominio y los códigos son consecutivos.
    assert [r.codigo for r in resultado.reglas] == [f"GM-{i:02d}" for i in range(1, len(resultado.reglas) + 1)]
