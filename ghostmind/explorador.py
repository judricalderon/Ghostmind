"""Explorador: ciclo de descubrimiento por rondas (research.md, D5 a D8).

Ronda 0: muestreo inicial. En cada ronda siguiente se induce un árbol con todos los casos
conocidos y se generan casos dirigidos:

1. bisección de los umbrales numéricos del árbol que aún no están confirmados;
2. búsqueda de contraejemplos dentro de cada hoja (25 solicitudes uniformes y una por borde);
3. exploración local alrededor de hasta 10 contraejemplos nuevos.

El ciclo termina cuando una ronda no encuentra contradicciones ni umbrales nuevos (estable), al
agotar el presupuesto, al llegar al máximo de rondas o si los errores del sistema superan el 1 %.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from ghostmind.adaptador import Adaptador, ErrorDelSistema, PresupuestoAgotado, resolver_objetivo
from ghostmind.diccionario import Diccionario, Solicitud
from ghostmind.extractor import Extractor, Hoja, Modelo
from ghostmind.muestreo import PARAMETROS_POR_DEFECTO, muestreo_inicial, tamano_muestreo_inicial
from ghostmind.registro import Registro
from ghostmind.reglas import Regla


@dataclass
class Parametros:
    presupuesto: int = 20_000
    max_rondas: int = 15
    min_casos_hoja: int = 3
    pares_biseccion: int = 3
    candidatos_por_lado: int = 5
    pruebas_por_hoja: int = 25
    max_exploraciones_locales: int = 10
    umbral_errores: float = 0.01
    min_consultas_errores: int = 100
    muestreo: dict = field(default_factory=lambda: dict(PARAMETROS_POR_DEFECTO))

    def como_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResultadoDescubrimiento:
    ejecucion_id: int
    motivo: str
    consultas: int
    rondas: int
    reglas: list[Regla]
    modelo: Modelo | None


class _Parada(Exception):
    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo


class Explorador:
    """Descubre las reglas de un sistema consultándolo solo por medio del adaptador."""

    def __init__(self, dic: Diccionario, registro: Registro, objetivo: str | Callable[[str], str],
                 semilla: int, parametros: Parametros | None = None):
        self.dic = dic
        self.registro = registro
        self.objetivo = objetivo
        self.semilla = semilla
        self.p = parametros or Parametros()
        self.rng = np.random.default_rng(semilla)
        self.extractor = Extractor(dic, semilla, self.p.min_casos_hoja)
        # Conocimiento acumulado: una entrada por solicitud distinta consultada
        self.conocidos: dict[tuple, str | None] = {}
        self.ids: dict[tuple, int] = {}
        self.origenes: dict[tuple, str] = {}
        self.confirmados: dict[str, set[int]] = defaultdict(set)
        self.intentos_biseccion: set[tuple] = set()
        self.cajas_probadas: set[tuple] = set()
        self.explorados: set[tuple] = set()
        self.ronda = 0
        self.modelo_vigente: Modelo | None = None
        self.contradicciones = 0
        self.umbrales_nuevos = 0

    # Consultas

    def _clave(self, solicitud: Solicitud) -> tuple:
        return tuple(solicitud[n] for n in self.dic.nombres)

    def _consultar(self, solicitud: Solicitud, origen: str) -> str | None:
        """Decisión del sistema; si la solicitud ya se conoce no se vuelve a consultar."""
        clave = self._clave(solicitud)
        if clave in self.conocidos:
            return self.conocidos[clave]
        try:
            decision = self.adaptador.consultar(solicitud, self.ronda, origen)
        except ErrorDelSistema:
            self.conocidos[clave] = None
            self.ids[clave] = self.adaptador.ultimo_caso_id
            self.origenes[clave] = origen
            self._revisar_errores()
            return None
        self.conocidos[clave] = decision
        self.ids[clave] = self.adaptador.ultimo_caso_id
        self.origenes[clave] = origen
        if self.modelo_vigente is not None and decision != self.modelo_vigente.predecir_uno(solicitud):
            self.contradicciones += 1
        return decision

    def _revisar_errores(self) -> None:
        a = self.adaptador
        if a.consultas >= self.p.min_consultas_errores and a.errores > self.p.umbral_errores * a.consultas:
            raise _Parada("errores")

    def _datos(self) -> pd.DataFrame:
        filas = [
            (*clave, decision, self.ids[clave], self.origenes[clave])
            for clave, decision in self.conocidos.items()
            if decision is not None
        ]
        return pd.DataFrame(filas, columns=[*self.dic.nombres, "decision", "caso_id", "origen"])

    def _solicitud(self, fila: pd.Series) -> Solicitud:
        return {n: (int(fila[n]) if self.dic.campo(n).es_numerico else str(fila[n])) for n in self.dic.nombres}

    # Ciclo principal

    def descubrir(self) -> ResultadoDescubrimiento:
        tamano = tamano_muestreo_inicial(self.dic, self.p.muestreo)
        if self.p.presupuesto < tamano:
            raise ValueError(
                f"El presupuesto ({self.p.presupuesto}) es menor que el muestreo inicial ({tamano})."
            )
        if isinstance(self.objetivo, str):
            nombre_objetivo, punto_de_entrada = self.objetivo, resolver_objetivo(self.objetivo)
        else:
            nombre_objetivo = getattr(self.objetivo, "__name__", "personalizado")
            punto_de_entrada = self.objetivo
        self.ejecucion_id = self.registro.crear_ejecucion(
            "descubrimiento", nombre_objetivo, self.semilla, self.p.presupuesto,
            parametros=self.p.como_dict(),
        )
        self.adaptador = Adaptador(self.dic, punto_de_entrada, self.registro, self.ejecucion_id,
                                   self.p.presupuesto)

        motivo: str | None = None
        modelo_final: Modelo | None = None
        rondas_completas = 0
        modelo: Modelo | None = None
        try:
            for origen, solicitud in muestreo_inicial(self.dic, self.rng, self.p.muestreo):
                self._consultar(solicitud, origen)
            self._revisar_errores()
            self.registro.guardar_ronda(self.ejecucion_id, 0, self.adaptador.consultas, 0, 0, 0)
            for ronda in range(1, self.p.max_rondas + 1):
                self.ronda = ronda
                modelo = self.extractor.ajustar(self._datos())
                self.modelo_vigente = modelo
                self.contradicciones = 0
                self.umbrales_nuevos = 0
                self._bisecciones(modelo)
                contraejemplos = self._buscar_contraejemplos(modelo)
                self._exploracion_local(contraejemplos)
                self._guardar_ronda(modelo)
                rondas_completas = ronda
                if self.contradicciones == 0 and self.umbrales_nuevos == 0:
                    motivo = "estable"
                    modelo_final = modelo
                    break
            else:
                motivo = "max_rondas"
        except PresupuestoAgotado:
            motivo = "presupuesto_agotado"
        except _Parada as parada:
            motivo = parada.motivo
        if motivo != "estable" and self.ronda > rondas_completas and modelo is not None:
            self._guardar_ronda(modelo)  # ronda interrumpida

        datos = self._datos()
        if modelo_final is None and len(datos):
            modelo_final = self.extractor.ajustar(datos)
        reglas = self._construir_reglas(modelo_final, datos) if modelo_final else []
        self.registro.guardar_reglas(self.ejecucion_id, reglas)
        self.registro.cerrar_ejecucion(self.ejecucion_id, self.adaptador.consultas, rondas_completas, motivo)
        return ResultadoDescubrimiento(self.ejecucion_id, motivo, self.adaptador.consultas,
                                       rondas_completas, reglas, modelo_final)

    def _guardar_ronda(self, modelo: Modelo) -> None:
        self.registro.guardar_ronda(self.ejecucion_id, self.ronda, self.adaptador.consultas,
                                    len(modelo.hojas()), self.contradicciones, self.umbrales_nuevos)

    # Paso 1: bisección de umbrales del árbol

    def _bisecciones(self, modelo: Modelo) -> None:
        datos = self._datos()
        for division in modelo.divisiones():
            campo, umbral = division.campo, division.umbral
            if math.floor(umbral) + 1 in self.confirmados[campo]:
                continue
            nodo = datos[division.caja.mascara(datos)]
            izquierda = nodo[nodo[campo] <= umbral]
            derecha = nodo[nodo[campo] > umbral]
            izquierda = izquierda.assign(distancia=umbral - izquierda[campo]).sort_values("distancia", kind="stable")
            derecha = derecha.assign(distancia=derecha[campo] - umbral).sort_values("distancia", kind="stable")
            pares = [
                (fila_a.distancia + fila_b.distancia, i, j, fila_a, fila_b)
                for i, fila_a in enumerate(izquierda.head(self.p.candidatos_por_lado).itertuples())
                for j, fila_b in enumerate(derecha.head(self.p.candidatos_por_lado).itertuples())
                if fila_a.decision != fila_b.decision
            ]
            pares.sort(key=lambda par: (par[0], par[1], par[2]))
            intentos = 0
            for _, _, _, fila_a, fila_b in pares:
                if intentos >= self.p.pares_biseccion:
                    break
                a = self._solicitud(pd.Series(fila_a._asdict()))
                b = self._solicitud(pd.Series(fila_b._asdict()))
                intento = (campo, umbral, self._clave(a), self._clave(b))
                if intento in self.intentos_biseccion:
                    continue
                self.intentos_biseccion.add(intento)
                intentos += 1
                if self._biseccion_desde(a, campo, b[campo]) is None:
                    self._biseccion_desde(b, campo, a[campo])
                if math.floor(umbral) + 1 in self.confirmados[campo]:
                    break

    def _biseccion_desde(self, base: Solicitud, campo: str, destino: int) -> int | None:
        """Varía solo ``campo`` desde la base hasta ``destino``; si la decisión cambia, bisecta."""
        decision_base = self.conocidos.get(self._clave(base))
        if decision_base is None:
            return None
        decision_destino = self._consultar({**base, campo: destino}, "biseccion")
        if decision_destino is None or decision_destino == decision_base:
            return None
        return self._biseccionar(base, campo, base[campo], decision_base, destino, decision_destino,
                                 "biseccion")

    def _biseccionar(self, base: Solicitud, campo: str, a: int, decision_a: str, b: int,
                     decision_b: str, origen: str) -> int | None:
        """Divide el intervalo por mitades hasta dos enteros consecutivos con decisiones distintas."""
        while abs(b - a) > 1:
            medio = (a + b) // 2
            decision = self._consultar({**base, campo: medio}, origen)
            if decision is None:
                return None
            if decision == decision_a:
                a = medio
            else:
                b, decision_b = medio, decision
        bajo, alto = (a, b) if a < b else (b, a)
        decision_baja, decision_alta = (decision_a, decision_b) if a < b else (decision_b, decision_a)
        self._registrar_umbral(base, campo, bajo, alto, decision_baja, decision_alta)
        return alto

    def _registrar_umbral(self, base: Solicitud, campo: str, bajo: int, alto: int,
                          decision_baja: str, decision_alta: str) -> None:
        if alto in self.confirmados[campo]:
            return
        self.confirmados[campo].add(alto)
        self.umbrales_nuevos += 1
        self.registro.guardar_umbral(
            self.ejecucion_id, campo, alto,
            self.ids[self._clave({**base, campo: bajo})], self.ids[self._clave({**base, campo: alto})],
            decision_baja, decision_alta, self.ronda,
        )

    # Paso 2: búsqueda de contraejemplos en cada hoja

    def _buscar_contraejemplos(self, modelo: Modelo) -> list[tuple[Solicitud, Hoja]]:
        encontrados: list[tuple[Solicitud, Hoja]] = []
        for hoja in modelo.hojas():
            marca = (hoja.caja.clave(), hoja.decision)
            if marca in self.cajas_probadas:
                continue
            self.cajas_probadas.add(marca)
            puntos = [hoja.caja.muestrear(self.rng) for _ in range(self.p.pruebas_por_hoja)]
            for campo in self.dic.numericos:
                lo, hi = hoja.caja.intervalos[campo.nombre]
                puntos.append(hoja.caja.muestrear(self.rng, {campo.nombre: lo}))
                puntos.append(hoja.caja.muestrear(self.rng, {campo.nombre: hi}))
            for solicitud in puntos:
                decision = self._consultar(solicitud, "contraejemplo")
                if decision is not None and decision != hoja.decision:
                    encontrados.append((solicitud, hoja))
        return encontrados

    # Paso 3: exploración local alrededor de contraejemplos

    def _exploracion_local(self, contraejemplos: list[tuple[Solicitud, Hoja]]) -> None:
        explorados_ronda = 0
        for solicitud, hoja in contraejemplos:
            clave = self._clave(solicitud)
            if clave in self.explorados:
                continue
            if explorados_ronda >= self.p.max_exploraciones_locales:
                break
            self.explorados.add(clave)
            explorados_ronda += 1
            decision = self.conocidos[clave]
            for campo in self.dic.numericos:
                for borde in hoja.caja.intervalos[campo.nombre]:
                    if borde == solicitud[campo.nombre]:
                        continue
                    decision_borde = self._consultar({**solicitud, campo.nombre: borde}, "exploracion_local")
                    if decision_borde is None or decision_borde == decision:
                        continue
                    self._biseccionar(solicitud, campo.nombre, solicitud[campo.nombre], decision, borde,
                                      decision_borde, "exploracion_local")
            for campo in self.dic.categoricos:
                for valor in campo.nombres_valores:
                    if valor != solicitud[campo.nombre]:
                        self._consultar({**solicitud, campo.nombre: valor}, "exploracion_local")

    # Reglas finales

    def _construir_reglas(self, modelo: Modelo, datos: pd.DataFrame) -> list[Regla]:
        reglas = []
        for hoja in modelo.hojas():
            dentro = datos[hoja.caja.mascara(datos)]
            respaldo = dentro[dentro["decision"] == hoja.decision]
            contra = dentro[dentro["decision"] != hoja.decision]
            umbrales = []
            for campo in self.dic.numericos:
                lo, hi = hoja.caja.intervalos[campo.nombre]
                if lo != campo.minimo and lo in self.confirmados[campo.nombre]:
                    umbrales.append({"campo": campo.nombre, "valor_cambio": lo})
                if hi != campo.maximo and hi + 1 in self.confirmados[campo.nombre]:
                    umbrales.append({"campo": campo.nombre, "valor_cambio": hi + 1})
            regla = Regla(
                codigo="",
                caja=hoja.caja,
                decision=hoja.decision,
                respaldo=len(respaldo),
                contraejemplos=len(contra),
                consultas_prueba=int((dentro["origen"] == "contraejemplo").sum()),
                umbrales_confirmados=umbrales,
                casos_respaldo=[int(x) for x in respaldo["caso_id"]],
                casos_contraejemplo=[int(x) for x in contra["caso_id"]],
            )
            regla.actualizar_estado()
            reglas.append(regla)
        reglas.sort(key=lambda r: (-r.respaldo, r.decision, r.texto_tecnico()))
        for i, regla in enumerate(reglas, start=1):
            regla.codigo = f"GM-{i:02d}"
        return reglas
