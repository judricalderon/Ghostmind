"""Pruebas del verificador diferencial (T042)."""

import pytest

from apoyo import dos_reglas, ejecucion_pequena, sistema_de_prueba
from ghostmind.__main__ import main
from ghostmind.registro import Registro
from ghostmind.reglas import Caja
from ghostmind.verificador import Verificador


def umbral_movido(s):
    """Como dos_reglas, pero el rechazo llega hasta 449 (antes 436)."""
    if s["puntaje_credito"] < 450:
        return "RECHAZADO"
    if s["tipo_empleo"] == "DESEMPLEADO":
        return "REVISION_MANUAL"
    return "APROBADO"


@pytest.fixture
def base(dic, registro):
    return ejecucion_pequena(dic, registro)


def test_misma_version_cero_diferencias(dic, registro, base):
    resultado = Verificador(dic, registro, sistema_de_prueba(dic, dos_reglas)).verificar(base.ejecucion_id)
    assert resultado.diferencias == 0
    assert resultado.errores == 0
    unicos = registro.casos(base.ejecucion_id, solo_validos=True)
    assert resultado.casos_repetidos == len(unicos)
    ejecucion = registro.ejecucion(resultado.ejecucion_id)
    assert ejecucion["tipo"] == "verificacion"
    assert ejecucion["ejecucion_base_id"] == base.ejecucion_id
    assert ejecucion["consultas"] == resultado.consultas == len(unicos)
    casos = registro.casos(resultado.ejecucion_id)
    assert set(casos["origen"]) == {"verificacion"}
    assert casos["caso_base_id"].notna().all()


def test_umbral_movido_se_detecta_y_se_asocia_a_su_regla(dic, registro, base):
    resultado = Verificador(dic, registro, sistema_de_prueba(dic, umbral_movido)).verificar(base.ejecucion_id)
    assert resultado.diferencias > 0
    diferencias = registro.diferencias(resultado.ejecucion_id)
    assert len(diferencias) == resultado.diferencias
    assert set(diferencias["decision_nueva"]) == {"RECHAZADO"}
    assert (diferencias["puntaje_credito"] == 437).any()  # el par de la bisección delata el cambio
    reglas = {r["id"]: r for r in registro.reglas(base.ejecucion_id)}
    for fila in diferencias.itertuples():
        regla = reglas[fila.regla_id]
        caja = Caja.desde_condiciones(dic, regla["condiciones"])
        assert caja.contiene({n: getattr(fila, n) for n in dic.nombres})
        assert regla["decision"] == fila.decision_original
    por_regla = resultado.por_regla
    assert sum(r.diferencias for r in por_regla) == resultado.diferencias
    assert all(r.ejemplos for r in por_regla if r.diferencias)


def test_resumen_por_regla_incluye_todas_las_reglas(dic, registro, base):
    resultado = Verificador(dic, registro, sistema_de_prueba(dic, umbral_movido)).verificar(base.ejecucion_id)
    assert {r.codigo for r in resultado.por_regla} == {r.codigo for r in base.reglas}
    assert sum(r.casos for r in resultado.por_regla) + resultado.sin_regla == resultado.casos_repetidos


def test_orden_verificar(tmp_path, dic, capsys):
    ruta = tmp_path / "cli.sqlite"
    assert main(["descubrir", "--objetivo", "legacy", "--semilla", "42", "--presupuesto", "3000",
                 "--db", str(ruta)]) == 0
    assert main(["verificar", "--ejecucion", "1", "--objetivo", "legacy", "--db", str(ruta)]) == 0
    assert main(["verificar", "--ejecucion", "1", "--objetivo", "modernizado", "--db", str(ruta)]) == 0
    salida = capsys.readouterr().out
    assert "Diferencias: 0" in salida
    reg = Registro(ruta, dic)
    verificaciones = reg.ejecuciones("verificacion")
    assert [v["objetivo"] for v in verificaciones] == ["legacy", "modernizado"]
    assert len(reg.diferencias(verificaciones[1]["id"])) > 0
    reg.cerrar()
    assert main(["verificar", "--ejecucion", "99", "--objetivo", "legacy", "--db", str(ruta)]) == 2
