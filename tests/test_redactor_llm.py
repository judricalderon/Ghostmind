"""Pruebas de la redacción opcional con modelo de lenguaje (T036), sin red ni llave."""

from types import SimpleNamespace

import pytest

from apoyo import ejecucion_pequena
from ghostmind import redactor_llm
from ghostmind.redactor_llm import (
    MODELO_POR_DEFECTO,
    RedaccionRechazada,
    llm_habilitado,
    redactar_y_guardar,
    validar_texto,
)


class ClienteFalso:
    """Imita ``client.beta.messages.create`` y guarda la petición recibida."""

    def __init__(self, texto=None, stop_reason="end_turn", error=None):
        self.texto = texto
        self.stop_reason = stop_reason
        self.error = error
        self.peticiones = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._crear))

    def _crear(self, **kwargs):
        self.peticiones.append(kwargs)
        if self.error:
            raise self.error
        bloques = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=self.texto)]
        return SimpleNamespace(content=bloques, stop_reason=self.stop_reason)


@pytest.fixture
def regla_rechazo(dic, registro):
    resultado = ejecucion_pequena(dic, registro)
    regla = next(r for r in registro.reglas(resultado.ejecucion_id) if r["decision"] == "RECHAZADO")
    return regla


@pytest.fixture
def activado(monkeypatch):
    monkeypatch.setenv("GHOSTMIND_LLM", "1")


def test_desactivado_por_defecto(monkeypatch, dic, registro, regla_rechazo):
    monkeypatch.delenv("GHOSTMIND_LLM", raising=False)
    assert not llm_habilitado()
    cliente = ClienteFalso("Se rechaza la solicitud si el puntaje es de 436 puntos o menos.")
    ok, mensaje = redactar_y_guardar(registro, regla_rechazo["id"], dic, cliente)
    assert not ok
    assert "desactivada" in mensaje
    assert cliente.peticiones == []
    assert registro.regla(regla_rechazo["id"])["texto_llm"] is None


def test_redaccion_valida_se_guarda_sin_tocar_la_regla(activado, dic, registro, regla_rechazo):
    texto = "Se rechaza toda solicitud con un puntaje de crédito de 436 puntos o menos."
    cliente = ClienteFalso(texto)
    ok, mensaje = redactar_y_guardar(registro, regla_rechazo["id"], dic, cliente)
    assert ok, mensaje
    despues = registro.regla(regla_rechazo["id"])
    assert despues["texto_llm"] == texto
    for clave in ("condiciones", "decision", "texto_tecnico", "texto_negocio", "estado", "confianza"):
        assert despues[clave] == regla_rechazo[clave]


def test_peticion_a_la_api(activado, dic, registro, regla_rechazo):
    cliente = ClienteFalso("Se rechaza la solicitud cuando el puntaje de crédito es menor que 437 puntos.")
    redactar_y_guardar(registro, regla_rechazo["id"], dic, cliente)
    peticion = cliente.peticiones[0]
    assert peticion["model"] == MODELO_POR_DEFECTO == "claude-opus-5-5"
    assert peticion["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in peticion["betas"]
    assert "temperature" not in peticion
    assert "436" in peticion["messages"][0]["content"]


@pytest.mark.parametrize(
    "texto",
    [
        "Se rechaza la solicitud cuando el puntaje de crédito es de 500 puntos o menos.",  # número inventado
        "Se aprueba la solicitud cuando el puntaje de crédito es de 436 puntos o menos.",  # decisión cambiada
        "",
    ],
)
def test_redaccion_que_altera_la_regla_se_descarta(activado, dic, registro, regla_rechazo, texto):
    ok, mensaje = redactar_y_guardar(registro, regla_rechazo["id"], dic, ClienteFalso(texto))
    assert not ok
    assert "plantilla" in mensaje
    assert registro.regla(regla_rechazo["id"])["texto_llm"] is None


def test_rechazo_del_modelo(activado, dic, registro, regla_rechazo):
    ok, _ = redactar_y_guardar(registro, regla_rechazo["id"], dic,
                               ClienteFalso("No puedo ayudar.", stop_reason="refusal"))
    assert not ok


def test_error_de_conexion(activado, dic, registro, regla_rechazo):
    ok, mensaje = redactar_y_guardar(registro, regla_rechazo["id"], dic,
                                     ClienteFalso(error=RuntimeError("sin red")))
    assert not ok
    assert "plantilla" in mensaje
    assert registro.regla(regla_rechazo["id"])["texto_llm"] is None


def test_validar_texto_acepta_limites_equivalentes(dic, regla_rechazo):
    # "menor que 437" es lo mismo que "436 o menos"
    validar_texto("Se rechaza la solicitud si el puntaje de crédito es menor que 437.", regla_rechazo, dic)
    with pytest.raises(RedaccionRechazada):
        validar_texto("Se rechaza la solicitud si el puntaje es menor que 450.", regla_rechazo, dic)


def test_sin_sdk_instalado(activado, monkeypatch, dic, registro, regla_rechazo):
    def sin_sdk():
        raise ImportError("No module named 'anthropic'")

    monkeypatch.setattr(redactor_llm, "crear_cliente", sin_sdk)
    ok, mensaje = redactar_y_guardar(registro, regla_rechazo["id"], dic)
    assert not ok
    assert "anthropic" in mensaje
