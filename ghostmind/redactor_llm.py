"""Redacción opcional de reglas con un modelo de lenguaje (Claude) (FR-018, D9).

- Desactivada por defecto: se activa con ``GHOSTMIND_LLM=1``. El SDK toma la llave de
  ``ANTHROPIC_API_KEY``; la llave nunca se escribe en el repositorio.
- Solo reescribe el texto de negocio de una regla ya descubierta. Nunca cambia sus condiciones,
  su decisión, su confianza ni su estado; el resultado se guarda aparte (``texto_llm``).
- Si la redacción menciona números que no están en la regla o no expresa la misma decisión, se
  descarta y el catálogo sigue mostrando la redacción por plantilla.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from ghostmind.diccionario import Diccionario
from ghostmind.registro import Registro
from ghostmind.reglas import Caja

MODELO_POR_DEFECTO = "claude-opus-5-5"
BETA_RESPALDO = "server-side-fallback-2026-07-01"

PALABRA_DECISION = {
    "APROBADO": ("aprueba", "aprobad", "aprobar"),
    "RECHAZADO": ("rechaza", "rechazad", "rechazar"),
    "REVISION_MANUAL": ("revisión manual", "revision manual"),
}

INSTRUCCIONES = (
    "Redactas reglas de negocio para especialistas de crédito que van a validarlas. Recibes una "
    "regla descubierta observando un sistema: sus condiciones exactas y su decisión. Escribe una "
    "sola oración en español claro y natural que exprese exactamente la misma regla. No agregues, "
    "quites ni cambies condiciones, valores, unidades ni la decisión; puedes reordenar las "
    "condiciones para que se lean mejor y expresar un límite de forma equivalente (por ejemplo, "
    "'399 o menos' como 'menor que 400'). No uses viñetas, títulos ni formato. Responde solo con "
    "la oración."
)


class RedaccionRechazada(ValueError):
    """La redacción del modelo no respeta la regla y se descarta."""


class ErrorRedaccion(RuntimeError):
    """No se pudo obtener una redacción del modelo."""


def llm_habilitado() -> bool:
    return os.environ.get("GHOSTMIND_LLM", "").strip() == "1"


def modelo() -> str:
    return os.environ.get("GHOSTMIND_LLM_MODELO", "").strip() or MODELO_POR_DEFECTO


def crear_cliente():
    """Cliente oficial de Anthropic; la importación es perezosa porque el SDK es opcional."""
    import anthropic

    return anthropic.Anthropic()


def construir_peticion(regla: dict[str, Any], dic: Diccionario) -> dict[str, Any]:
    datos = {
        "decision": regla["decision"],
        "condiciones_exactas": regla["texto_tecnico"],
        "redaccion_por_plantilla": regla["texto_negocio"],
    }
    return {
        "model": modelo(),
        "max_tokens": 16000,
        "output_config": {"effort": "medium"},
        "betas": [BETA_RESPALDO],
        "fallbacks": "default",
        "system": INSTRUCCIONES,
        "messages": [{"role": "user", "content": json.dumps(datos, ensure_ascii=False, indent=2)}],
    }


def numeros_permitidos(regla: dict[str, Any], dic: Diccionario) -> set[int]:
    """Límites de la regla (y su forma equivalente con ±1) y números de los códigos categóricos."""
    permitidos: set[int] = set()
    caja = Caja.desde_condiciones(dic, regla["condiciones"])
    for campo in dic.numericos:
        lo, hi = caja.intervalos[campo.nombre]
        if lo != campo.minimo:
            permitidos |= {lo, lo - 1}
        if hi != campo.maximo:
            permitidos |= {hi, hi + 1}
    for campo in dic.categoricos:
        for valor in campo.nombres_valores:
            permitidos |= {int(n) for n in re.findall(r"\d+", valor)}
    return permitidos


def validar_texto(texto: str, regla: dict[str, Any], dic: Diccionario) -> None:
    if not texto.strip():
        raise RedaccionRechazada("la respuesta llegó vacía")
    minusculas = texto.lower()
    if not any(palabra in minusculas for palabra in PALABRA_DECISION[regla["decision"]]):
        raise RedaccionRechazada("no expresa la misma decisión")
    for decision, palabras in PALABRA_DECISION.items():
        if decision != regla["decision"] and any(p in minusculas for p in palabras):
            raise RedaccionRechazada(f"menciona otra decisión ({decision})")
    mencionados = {int(n.replace(".", "")) for n in re.findall(r"\d[\d.]*\d|\d", texto)}
    ajenos = mencionados - numeros_permitidos(regla, dic)
    if ajenos:
        raise RedaccionRechazada(f"menciona valores que no están en la regla: {sorted(ajenos)}")


def _llamar(cliente: Any, peticion: dict[str, Any]) -> Any:
    try:
        return cliente.beta.messages.create(**peticion)
    except Exception as exc:  # se traduce a un mensaje claro, del error más específico al más general
        try:
            import anthropic
        except ImportError:
            raise ErrorRedaccion(f"{type(exc).__name__}: {exc}") from exc
        if isinstance(exc, anthropic.AuthenticationError):
            mensaje = "la llave de la API no es válida o no está configurada (ANTHROPIC_API_KEY)"
        elif isinstance(exc, anthropic.PermissionDeniedError):
            mensaje = "la llave no tiene permiso para este modelo"
        elif isinstance(exc, anthropic.NotFoundError):
            mensaje = f"el modelo {peticion['model']!r} no existe o no está disponible"
        elif isinstance(exc, anthropic.RateLimitError):
            mensaje = "se alcanzó el límite de uso de la API; intenta más tarde"
        elif isinstance(exc, anthropic.BadRequestError):
            mensaje = f"la API rechazó la petición: {exc.message}"
        elif isinstance(exc, anthropic.APIStatusError):
            mensaje = f"error de la API ({exc.status_code})"
        elif isinstance(exc, anthropic.APIConnectionError):
            mensaje = "no hay conexión con la API"
        else:
            mensaje = f"{type(exc).__name__}: {exc}"
        raise ErrorRedaccion(mensaje) from exc


def redactar(regla: dict[str, Any], dic: Diccionario, cliente: Any) -> str:
    respuesta = _llamar(cliente, construir_peticion(regla, dic))
    if respuesta.stop_reason == "refusal":
        raise RedaccionRechazada("el modelo declinó la petición")
    if respuesta.stop_reason == "max_tokens":
        raise RedaccionRechazada("la respuesta quedó incompleta")
    texto = " ".join(b.text for b in respuesta.content if getattr(b, "type", "") == "text").strip()
    validar_texto(texto, regla, dic)
    return texto


def redactar_y_guardar(registro: Registro, regla_id: int, dic: Diccionario,
                       cliente: Any = None) -> tuple[bool, str]:
    """Pide la redacción y la guarda en ``texto_llm``. Devuelve (éxito, texto o motivo)."""
    if not llm_habilitado():
        return False, "La redacción con modelo de lenguaje está desactivada (GHOSTMIND_LLM=1 la activa)."
    regla = registro.regla(regla_id)
    if cliente is None:
        try:
            cliente = crear_cliente()
        except ImportError:
            return False, ("Falta el paquete opcional anthropic: pip install -r requirements-llm.txt. "
                           "Se mantiene la redacción por plantilla.")
    try:
        texto = redactar(regla, dic, cliente)
    except RedaccionRechazada as exc:
        return False, f"Se descartó la redacción del modelo ({exc}); se mantiene la plantilla."
    except ErrorRedaccion as exc:
        return False, f"No se pudo redactar con el modelo ({exc}); se mantiene la plantilla."
    registro.guardar_texto_llm(regla_id, texto)
    return True, texto


__all__ = [
    "MODELO_POR_DEFECTO", "RedaccionRechazada", "ErrorRedaccion", "llm_habilitado", "construir_peticion",
    "validar_texto", "redactar", "redactar_y_guardar", "crear_cliente",
]
