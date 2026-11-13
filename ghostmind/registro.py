"""Registro de evidencia en SQLite.

Guarda cada ejecución, cada consulta al sistema (caso), los umbrales confirmados, el avance por
ronda, las reglas con su evidencia, las revisiones del especialista y las diferencias de la
verificación. El esquema sigue ``specs/001-ghostmind-mvp/data-model.md``.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from ghostmind.diccionario import RAIZ, Diccionario, Solicitud

RUTA_POR_DEFECTO = RAIZ / "datos" / "ghostmind.sqlite"

TIPOS_EJECUCION = ("descubrimiento", "verificacion")
MOTIVOS_PARADA = ("estable", "presupuesto_agotado", "max_rondas", "errores", "completa")
ORIGENES = (
    "aleatorio",
    "limite",
    "categoria",
    "biseccion",
    "contraejemplo",
    "exploracion_local",
    "verificacion",
)


def ruta_por_defecto() -> Path:
    """Ruta de la base: variable ``GHOSTMIND_DB`` o ``datos/ghostmind.sqlite``."""
    return Path(os.environ.get("GHOSTMIND_DB", RUTA_POR_DEFECTO))


def ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _esquema(dic: Diccionario) -> str:
    columnas_campos = ",\n    ".join(
        f"{c.nombre} {'INTEGER' if c.es_numerico else 'TEXT'} NOT NULL" for c in dic.campos
    )
    return f"""
CREATE TABLE IF NOT EXISTS ejecuciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL CHECK (tipo IN ('descubrimiento', 'verificacion')),
    objetivo TEXT NOT NULL,
    ejecucion_base_id INTEGER REFERENCES ejecuciones(id),
    semilla INTEGER,
    presupuesto INTEGER NOT NULL CHECK (presupuesto > 0),
    parametros TEXT NOT NULL DEFAULT '{{}}',
    version TEXT NOT NULL,
    inicio TEXT NOT NULL,
    fin TEXT,
    consultas INTEGER NOT NULL DEFAULT 0,
    rondas INTEGER NOT NULL DEFAULT 0,
    motivo_parada TEXT
);

CREATE TABLE IF NOT EXISTS casos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ejecucion_id INTEGER NOT NULL REFERENCES ejecuciones(id),
    n_consulta INTEGER NOT NULL,
    ronda INTEGER NOT NULL,
    origen TEXT NOT NULL,
    {columnas_campos},
    decision TEXT,
    error TEXT,
    caso_base_id INTEGER REFERENCES casos(id),
    momento TEXT NOT NULL,
    UNIQUE (ejecucion_id, n_consulta)
);
CREATE INDEX IF NOT EXISTS ix_casos_ronda ON casos (ejecucion_id, ronda);
CREATE INDEX IF NOT EXISTS ix_casos_origen ON casos (ejecucion_id, origen);

CREATE TABLE IF NOT EXISTS umbrales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ejecucion_id INTEGER NOT NULL REFERENCES ejecuciones(id),
    campo TEXT NOT NULL,
    valor_cambio INTEGER NOT NULL,
    caso_bajo_id INTEGER NOT NULL REFERENCES casos(id),
    caso_alto_id INTEGER NOT NULL REFERENCES casos(id),
    decision_baja TEXT NOT NULL,
    decision_alta TEXT NOT NULL CHECK (decision_alta <> decision_baja),
    ronda INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rondas (
    ejecucion_id INTEGER NOT NULL REFERENCES ejecuciones(id),
    ronda INTEGER NOT NULL,
    consultas_acumuladas INTEGER NOT NULL,
    reglas INTEGER NOT NULL,
    contradicciones INTEGER NOT NULL,
    umbrales_nuevos INTEGER NOT NULL,
    PRIMARY KEY (ejecucion_id, ronda)
);

CREATE TABLE IF NOT EXISTS reglas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ejecucion_id INTEGER NOT NULL REFERENCES ejecuciones(id),
    codigo TEXT NOT NULL,
    condiciones TEXT NOT NULL,
    decision TEXT NOT NULL,
    respaldo INTEGER NOT NULL CHECK (respaldo >= 0),
    contraejemplos INTEGER NOT NULL CHECK (contraejemplos >= 0),
    consultas_prueba INTEGER NOT NULL DEFAULT 0,
    umbrales_confirmados TEXT NOT NULL DEFAULT '[]',
    confianza REAL NOT NULL CHECK (confianza BETWEEN 0 AND 1),
    estado TEXT NOT NULL CHECK (estado IN ('hipotesis', 'corroborada', 'validada', 'rechazada')),
    texto_tecnico TEXT NOT NULL,
    texto_negocio TEXT NOT NULL,
    texto_llm TEXT,
    UNIQUE (ejecucion_id, codigo)
);

CREATE TABLE IF NOT EXISTS regla_casos (
    regla_id INTEGER NOT NULL REFERENCES reglas(id),
    caso_id INTEGER NOT NULL REFERENCES casos(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('respaldo', 'contraejemplo')),
    PRIMARY KEY (regla_id, caso_id)
);

CREATE TABLE IF NOT EXISTS revisiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regla_id INTEGER NOT NULL REFERENCES reglas(id),
    decision TEXT NOT NULL CHECK (decision IN ('validada', 'rechazada')),
    nota TEXT,
    momento TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diferencias (
    ejecucion_id INTEGER NOT NULL REFERENCES ejecuciones(id),
    caso_base_id INTEGER NOT NULL REFERENCES casos(id),
    caso_nuevo_id INTEGER NOT NULL REFERENCES casos(id),
    regla_id INTEGER REFERENCES reglas(id),
    decision_original TEXT NOT NULL,
    decision_nueva TEXT NOT NULL,
    PRIMARY KEY (ejecucion_id, caso_base_id)
);
"""


class Registro:
    """Acceso al registro de evidencia de GhostMind."""

    def __init__(self, ruta: Path | str | None = None, diccionario: Diccionario | None = None):
        self.diccionario = diccionario or Diccionario.cargar()
        self.ruta = Path(ruta) if ruta is not None else ruta_por_defecto()
        if str(self.ruta) != ":memory:":
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(self.ruta))
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self.con.execute("PRAGMA synchronous = NORMAL")
        self.con.executescript(_esquema(self.diccionario))
        self.con.commit()
        self._campos = self.diccionario.nombres

    # Conexión

    def confirmar(self) -> None:
        self.con.commit()

    def cerrar(self) -> None:
        self.con.commit()
        self.con.close()

    # Ejecuciones

    def crear_ejecucion(self, tipo: str, objetivo: str, semilla: int | None, presupuesto: int,
                        parametros: dict | None = None, ejecucion_base_id: int | None = None) -> int:
        if tipo not in TIPOS_EJECUCION:
            raise ValueError(f"Tipo de ejecución desconocido: {tipo!r}")
        from ghostmind import __version__

        cursor = self.con.execute(
            "INSERT INTO ejecuciones (tipo, objetivo, ejecucion_base_id, semilla, presupuesto,"
            " parametros, version, inicio) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (tipo, objetivo, ejecucion_base_id, semilla, presupuesto,
             json.dumps(parametros or {}, ensure_ascii=False, sort_keys=True), __version__, ahora()),
        )
        self.con.commit()
        return int(cursor.lastrowid)

    def cerrar_ejecucion(self, ejecucion_id: int, consultas: int, rondas: int, motivo_parada: str) -> None:
        if motivo_parada not in MOTIVOS_PARADA:
            raise ValueError(f"Motivo de parada desconocido: {motivo_parada!r}")
        self.con.execute(
            "UPDATE ejecuciones SET fin = ?, consultas = ?, rondas = ?, motivo_parada = ? WHERE id = ?",
            (ahora(), consultas, rondas, motivo_parada, ejecucion_id),
        )
        self.con.commit()

    def ejecucion(self, ejecucion_id: int) -> dict[str, Any]:
        fila = self.con.execute("SELECT * FROM ejecuciones WHERE id = ?", (ejecucion_id,)).fetchone()
        if fila is None:
            raise KeyError(f"No existe la ejecución {ejecucion_id}")
        datos = dict(fila)
        datos["parametros"] = json.loads(datos["parametros"])
        return datos

    def ejecuciones(self, tipo: str | None = None) -> list[dict[str, Any]]:
        consulta = "SELECT id FROM ejecuciones"
        argumentos: tuple = ()
        if tipo:
            consulta += " WHERE tipo = ?"
            argumentos = (tipo,)
        return [self.ejecucion(f["id"]) for f in self.con.execute(consulta + " ORDER BY id", argumentos)]

    # Casos

    def guardar_caso(self, ejecucion_id: int, n_consulta: int, ronda: int, origen: str,
                     solicitud: Solicitud, decision: str | None, error: str | None = None,
                     caso_base_id: int | None = None) -> int:
        if origen not in ORIGENES:
            raise ValueError(f"Origen de caso desconocido: {origen!r}")
        columnas = ", ".join(self._campos)
        marcas = ", ".join("?" for _ in self._campos)
        cursor = self.con.execute(
            f"INSERT INTO casos (ejecucion_id, n_consulta, ronda, origen, {columnas}, decision, error,"
            f" caso_base_id, momento) VALUES (?, ?, ?, ?, {marcas}, ?, ?, ?, ?)",
            (ejecucion_id, n_consulta, ronda, origen, *(solicitud[c] for c in self._campos),
             decision, error, caso_base_id, ahora()),
        )
        return int(cursor.lastrowid)

    def casos(self, ejecucion_id: int, solo_validos: bool = False) -> pd.DataFrame:
        consulta = "SELECT * FROM casos WHERE ejecucion_id = ?"
        if solo_validos:
            consulta += " AND decision IS NOT NULL"
        filas = self.con.execute(consulta + " ORDER BY n_consulta", (ejecucion_id,)).fetchall()
        columnas = [d[0] for d in self.con.execute("SELECT * FROM casos LIMIT 0").description]
        return pd.DataFrame([tuple(f) for f in filas], columns=columnas)

    def contar_casos(self, ejecucion_id: int) -> int:
        return int(self.con.execute(
            "SELECT COUNT(*) FROM casos WHERE ejecucion_id = ?", (ejecucion_id,)
        ).fetchone()[0])

    # Rondas y umbrales

    def guardar_ronda(self, ejecucion_id: int, ronda: int, consultas_acumuladas: int, reglas: int,
                      contradicciones: int, umbrales_nuevos: int) -> None:
        self.con.execute(
            "INSERT OR REPLACE INTO rondas VALUES (?, ?, ?, ?, ?, ?)",
            (ejecucion_id, ronda, consultas_acumuladas, reglas, contradicciones, umbrales_nuevos),
        )
        self.con.commit()

    def rondas(self, ejecucion_id: int) -> pd.DataFrame:
        filas = self.con.execute(
            "SELECT * FROM rondas WHERE ejecucion_id = ? ORDER BY ronda", (ejecucion_id,)
        ).fetchall()
        return pd.DataFrame(
            [dict(f) for f in filas],
            columns=["ejecucion_id", "ronda", "consultas_acumuladas", "reglas", "contradicciones",
                     "umbrales_nuevos"],
        )

    def guardar_umbral(self, ejecucion_id: int, campo: str, valor_cambio: int, caso_bajo_id: int,
                       caso_alto_id: int, decision_baja: str, decision_alta: str, ronda: int) -> int:
        cursor = self.con.execute(
            "INSERT INTO umbrales (ejecucion_id, campo, valor_cambio, caso_bajo_id, caso_alto_id,"
            " decision_baja, decision_alta, ronda) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ejecucion_id, campo, valor_cambio, caso_bajo_id, caso_alto_id, decision_baja,
             decision_alta, ronda),
        )
        return int(cursor.lastrowid)

    def umbrales(self, ejecucion_id: int) -> pd.DataFrame:
        filas = self.con.execute(
            "SELECT * FROM umbrales WHERE ejecucion_id = ? ORDER BY id", (ejecucion_id,)
        ).fetchall()
        return pd.DataFrame(
            [dict(f) for f in filas],
            columns=["id", "ejecucion_id", "campo", "valor_cambio", "caso_bajo_id", "caso_alto_id",
                     "decision_baja", "decision_alta", "ronda"],
        )

    # Reglas y evidencia

    def guardar_reglas(self, ejecucion_id: int, reglas: Iterable[Any]) -> None:
        """Guarda las reglas finales de una ejecución y sus enlaces con los casos."""
        for regla in reglas:
            cursor = self.con.execute(
                "INSERT INTO reglas (ejecucion_id, codigo, condiciones, decision, respaldo,"
                " contraejemplos, consultas_prueba, umbrales_confirmados, confianza, estado,"
                " texto_tecnico, texto_negocio) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ejecucion_id, regla.codigo, json.dumps(regla.caja.condiciones(), ensure_ascii=False),
                 regla.decision, regla.respaldo, regla.contraejemplos, regla.consultas_prueba,
                 json.dumps(regla.umbrales_confirmados, ensure_ascii=False), regla.confianza,
                 regla.estado, regla.texto_tecnico(), regla.texto_negocio()),
            )
            regla.id = int(cursor.lastrowid)
            enlaces = [(regla.id, c, "respaldo") for c in regla.casos_respaldo]
            enlaces += [(regla.id, c, "contraejemplo") for c in regla.casos_contraejemplo]
            self.con.executemany("INSERT INTO regla_casos VALUES (?, ?, ?)", enlaces)
        self.con.commit()

    def reglas(self, ejecucion_id: int) -> list[dict[str, Any]]:
        filas = self.con.execute(
            "SELECT * FROM reglas WHERE ejecucion_id = ? ORDER BY codigo", (ejecucion_id,)
        ).fetchall()
        salida = []
        for fila in filas:
            datos = dict(fila)
            datos["condiciones"] = json.loads(datos["condiciones"])
            datos["umbrales_confirmados"] = json.loads(datos["umbrales_confirmados"])
            salida.append(datos)
        return salida

    def regla(self, regla_id: int) -> dict[str, Any]:
        fila = self.con.execute("SELECT ejecucion_id FROM reglas WHERE id = ?", (regla_id,)).fetchone()
        if fila is None:
            raise KeyError(f"No existe la regla {regla_id}")
        return next(r for r in self.reglas(fila["ejecucion_id"]) if r["id"] == regla_id)

    def casos_de_regla(self, regla_id: int, tipo: str | None = None) -> pd.DataFrame:
        """Casos que respaldan o contradicen una regla, con la columna ``tipo``."""
        consulta = ("SELECT c.*, rc.tipo FROM regla_casos rc JOIN casos c ON c.id = rc.caso_id"
                    " WHERE rc.regla_id = ?")
        argumentos: tuple = (regla_id,)
        if tipo:
            consulta += " AND rc.tipo = ?"
            argumentos += (tipo,)
        cursor = self.con.execute(consulta + " ORDER BY c.n_consulta", argumentos)
        columnas = [d[0] for d in cursor.description]
        return pd.DataFrame([tuple(f) for f in cursor.fetchall()], columns=columnas)

    # Revisiones del especialista y redacción opcional

    def guardar_revision(self, regla_id: int, decision: str, nota: str | None) -> None:
        """Registra la decisión del especialista y actualiza el estado de la regla."""
        self.con.execute(
            "INSERT INTO revisiones (regla_id, decision, nota, momento) VALUES (?, ?, ?, ?)",
            (regla_id, decision, nota, ahora()),
        )
        self.con.execute("UPDATE reglas SET estado = ? WHERE id = ?", (decision, regla_id))
        self.con.commit()

    def revisiones(self, regla_id: int) -> list[dict[str, Any]]:
        filas = self.con.execute(
            "SELECT decision, nota, momento FROM revisiones WHERE regla_id = ? ORDER BY id", (regla_id,)
        ).fetchall()
        return [dict(f) for f in filas]

    def guardar_texto_llm(self, regla_id: int, texto: str) -> None:
        self.con.execute("UPDATE reglas SET texto_llm = ? WHERE id = ?", (texto, regla_id))
        self.con.commit()

    def ejecutar(self, sql: str, parametros: Iterable[Any] = ()) -> sqlite3.Cursor:
        """Acceso de bajo nivel para los módulos de GhostMind que guardan reglas y revisiones."""
        return self.con.execute(sql, tuple(parametros))
