"""Catálogo de reglas de GhostMind IA (Streamlit).

Ejecutar desde la raíz del repositorio:

    streamlit run app/catalogo.py

Variables de entorno opcionales: ``GHOSTMIND_DB`` (ruta de la base de evidencia),
``GHOSTMIND_LLM=1`` y ``ANTHROPIC_API_KEY`` (redacción asistida por modelo de lenguaje).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from ghostmind import redactor_llm  # noqa: E402
from ghostmind.adaptador import RUTA_OBJETIVOS  # noqa: E402
from ghostmind.catalogo import exportar, historial, revisar  # noqa: E402
from ghostmind.verificador import Verificador  # noqa: E402
from ghostmind.diccionario import Diccionario  # noqa: E402
from ghostmind.registro import Registro, ruta_por_defecto  # noqa: E402
from ghostmind.reglas import Caja, formato_miles  # noqa: E402

ESTADOS = {
    "hipotesis": "Hipótesis",
    "corroborada": "Corroborada",
    "validada": "Validada",
    "rechazada": "Rechazada",
}
COLOR_ESTADO = {"hipotesis": "gray", "corroborada": "blue", "validada": "green", "rechazada": "red"}
COLOR_DECISION = {"APROBADO": "green", "RECHAZADO": "red", "REVISION_MANUAL": "orange"}
MOTIVOS = {
    "estable": "Estable",
    "presupuesto_agotado": "Presupuesto",
    "max_rondas": "Máx. rondas",
    "errores": "Errores",
    "completa": "Completa",
}
ORIGENES = {
    "aleatorio": "Aleatorio",
    "limite": "Valores límite",
    "categoria": "Categorías",
    "biseccion": "Bisección",
    "contraejemplo": "Búsqueda de contraejemplos",
    "exploracion_local": "Exploración local",
    "verificacion": "Verificación",
}
COLOR_SERIE = "#2a78d6"  # un solo tono por gráfico (una serie, sin leyenda)
MILES = "replace(format(datum.value, ','), ',', '.')"  # separador de miles en español

st.set_page_config(page_title="GhostMind IA - Catálogo de reglas", page_icon=":material/fact_check:",
                   layout="wide")


def mostrar_mensaje_pendiente() -> None:
    mensaje = st.session_state.pop("mensaje", None)
    if mensaje:
        tipo, texto = mensaje
        (st.success if tipo == "ok" else st.warning)(texto)


def tabla_condiciones(regla: dict, dic: Diccionario) -> pd.DataFrame:
    caja = Caja.desde_condiciones(dic, regla["condiciones"])
    filas = []
    for nombre in caja.restringidos():
        campo = dic.campo(nombre)
        if campo.es_numerico:
            lo, hi = caja.intervalos[nombre]
            unidad = f" {campo.unidad}" if campo.unidad else ""
            if lo != campo.minimo and hi != campo.maximo:
                texto = f"entre {formato_miles(lo)} y {formato_miles(hi)}{unidad}"
            elif lo != campo.minimo:
                texto = f"{formato_miles(lo)}{unidad} o más"
            else:
                texto = f"{formato_miles(hi)}{unidad} o menos"
        else:
            texto = ", ".join(campo.etiqueta_valor(v) for v in caja.conjuntos[nombre])
        filas.append({"Campo": campo.etiqueta.capitalize(), "Condición": texto})
    return pd.DataFrame(filas, columns=["Campo", "Condición"])


def con_miles(tabla: pd.DataFrame, dic: Diccionario) -> pd.DataFrame:
    """Muestra con separador de miles los campos en pesos (solo para visualizar)."""
    tabla = tabla.copy()
    for campo in dic.numericos:
        if campo.unidad == "pesos" and campo.nombre in tabla:
            tabla[campo.nombre] = [formato_miles(int(v)) for v in tabla[campo.nombre]]
    return tabla


def tabla_casos(casos: pd.DataFrame, dic: Diccionario) -> pd.DataFrame:
    columnas = ["n_consulta", "ronda", "origen", *dic.nombres, "decision"]
    vista = casos[columnas].copy()
    vista["origen"] = vista["origen"].map(ORIGENES).fillna(vista["origen"])
    vista = con_miles(vista, dic)
    nombres = {"n_consulta": "Consulta", "ronda": "Ronda", "origen": "Origen", "decision": "Decisión"}
    nombres.update({c.nombre: c.etiqueta.capitalize() for c in dic.campos})
    return vista.rename(columns=nombres)


def grafico_linea(datos: pd.DataFrame, x: str, y: str, titulo_x: str, titulo_y: str) -> alt.Chart:
    datos = datos.assign(_texto=[formato_miles(int(v)) for v in datos[y]])
    base = alt.Chart(datos).encode(
        x=alt.X(f"{x}:O", title=titulo_x, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{y}:Q", title=titulo_y, axis=alt.Axis(labelExpr=MILES)),
        tooltip=[alt.Tooltip(f"{x}:O", title=titulo_x), alt.Tooltip("_texto:N", title=titulo_y)],
    )
    return (base.mark_line(color=COLOR_SERIE, strokeWidth=2)
            + base.mark_point(color=COLOR_SERIE, filled=True, size=70)).properties(height=260)


def grafico_barras(datos: pd.DataFrame, x: str, y: str, titulo_x: str, titulo_y: str,
                   horizontal: bool = False) -> alt.Chart:
    datos = datos.assign(_texto=[formato_miles(int(v)) for v in datos[y]])
    if horizontal:
        codificacion = dict(
            y=alt.Y(f"{x}:N", title=None, sort="-x", axis=alt.Axis(labelLimit=260)),
            x=alt.X(f"{y}:Q", title=titulo_y, axis=alt.Axis(labelExpr=MILES)),
        )
        esquinas = dict(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
    else:
        codificacion = dict(
            x=alt.X(f"{x}:O", title=titulo_x, axis=alt.Axis(labelAngle=0)),
            y=alt.Y(f"{y}:Q", title=titulo_y, axis=alt.Axis(labelExpr=MILES)),
        )
        esquinas = dict(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    base = alt.Chart(datos).encode(
        **codificacion,
        tooltip=[alt.Tooltip(f"{x}:N", title=titulo_x), alt.Tooltip("_texto:N", title=titulo_y)],
    )
    barras = base.mark_bar(color=COLOR_SERIE, **esquinas)
    if horizontal:
        etiquetas = base.mark_text(align="left", dx=4, color="#52514e").encode(text="_texto:N")
        return (barras + etiquetas).properties(height=36 * len(datos) + 20)
    return barras.properties(height=260)


def seccion_reglas(registro: Registro, dic: Diccionario, reglas: list[dict], filtros: dict) -> None:
    filtradas = [
        r for r in reglas
        if r["decision"] in filtros["decisiones"]
        and r["estado"] in filtros["estados"]
        and r["confianza"] * 100 >= filtros["confianza"]
    ]
    st.caption(f"{len(filtradas)} de {len(reglas)} reglas cumplen los filtros.")
    tabla = pd.DataFrame(
        [{
            "Código": r["codigo"],
            "Decisión": r["decision"],
            "Regla": r["texto_llm"] or r["texto_negocio"],
            "Confianza": round(r["confianza"] * 100, 1),
            "Estado": ESTADOS[r["estado"]],
            "Respaldo": r["respaldo"],
            "Contraejemplos": r["contraejemplos"],
        } for r in filtradas],
        columns=["Código", "Decisión", "Regla", "Confianza", "Estado", "Respaldo", "Contraejemplos"],
    )
    st.dataframe(
        tabla,
        hide_index=True,
        width="stretch",
        column_config={
            "Regla": st.column_config.TextColumn("Regla", width="large"),
            "Confianza": st.column_config.ProgressColumn("Confianza (%)", format="%.1f", min_value=0,
                                                         max_value=100),
        },
    )
    if not filtradas:
        st.info("Ninguna regla cumple los filtros.")
        return

    st.subheader("Detalle de la regla")
    por_codigo = {r["codigo"]: r for r in filtradas}
    pedida = st.query_params.get("regla")
    if "regla" not in st.session_state and pedida in por_codigo:
        st.session_state["regla"] = pedida
    codigo = st.selectbox("Regla", list(por_codigo), key="regla",
                          format_func=lambda c: f"{c} · {por_codigo[c]['decision']}")
    regla = por_codigo[codigo]

    st.markdown(f":{COLOR_DECISION[regla['decision']]}-badge[{regla['decision']}] "
                f":{COLOR_ESTADO[regla['estado']]}-badge[{ESTADOS[regla['estado']]}]")
    if regla["texto_llm"]:
        st.markdown(f"**{regla['texto_llm']}**")
        st.caption(f"Redacción asistida por modelo de lenguaje. Por plantilla: {regla['texto_negocio']}")
    else:
        st.markdown(f"**{regla['texto_negocio']}**")
    st.code(regla["texto_tecnico"], language=None, wrap_lines=True)

    izquierda, derecha = st.columns([3, 2])
    with izquierda:
        st.markdown("**Condiciones**")
        condiciones = tabla_condiciones(regla, dic)
        if condiciones.empty:
            st.write("Aplica a cualquier solicitud.")
        else:
            st.dataframe(condiciones, hide_index=True, width="stretch")
        if regla["umbrales_confirmados"]:
            st.markdown("**Umbrales confirmados por bisección**")
            for u in regla["umbrales_confirmados"]:
                campo = dic.campo(u["campo"])
                st.write(f"- {campo.etiqueta.capitalize()}: la decisión cambia en "
                         f"{formato_miles(u['valor_cambio'])} {campo.unidad or ''}".rstrip())
    with derecha:
        m1, m2 = st.columns(2)
        m1.metric("Confianza", f"{regla['confianza'] * 100:.1f} %".replace(".", ","))
        m2.metric("Pruebas de contraejemplo", regla["consultas_prueba"])
        m3, m4 = st.columns(2)
        m3.metric("Casos de respaldo", regla["respaldo"])
        m4.metric("Contraejemplos", regla["contraejemplos"])

    casos = registro.casos_de_regla(regla["id"])
    respaldo = casos[casos["tipo"] == "respaldo"]
    contra = casos[casos["tipo"] == "contraejemplo"]
    with st.expander(f"Casos que la respaldan ({len(respaldo)}; se muestran hasta 50)"):
        st.dataframe(tabla_casos(respaldo.head(50), dic), hide_index=True, width="stretch")
    with st.expander(f"Contraejemplos ({len(contra)})"):
        if contra.empty:
            st.write("No hay casos registrados que contradigan esta regla.")
        else:
            st.dataframe(tabla_casos(contra, dic), hide_index=True, width="stretch")

    st.markdown("**Revisión del especialista**")
    st.text_area("Nota (opcional)", key="nota", placeholder="Por qué se valida o se rechaza")
    b1, b2, b3 = st.columns([1, 1, 2])
    if b1.button("Validar regla", key="aprobar", type="primary", width="stretch"):
        revisar(registro, regla["id"], "validada", st.session_state.get("nota"))
        st.session_state["mensaje"] = ("ok", f"{codigo} quedó validada.")
        st.rerun()
    if b2.button("Rechazar regla", key="rechazar", width="stretch"):
        revisar(registro, regla["id"], "rechazada", st.session_state.get("nota"))
        st.session_state["mensaje"] = ("ok", f"{codigo} quedó rechazada.")
        st.rerun()
    habilitado = redactor_llm.llm_habilitado()
    if b3.button("Redactar con modelo de lenguaje", key="llm", disabled=not habilitado,
                 help=None if habilitado else "Desactivado: GHOSTMIND_LLM=1 y ANTHROPIC_API_KEY lo activan."):
        with st.spinner("Redactando..."):
            ok, texto = redactor_llm.redactar_y_guardar(registro, regla["id"], dic)
        st.session_state["mensaje"] = ("ok" if ok else "aviso", texto if not ok else f"{codigo}: redacción guardada.")
        st.rerun()

    pasos = historial(registro, regla["id"])
    if pasos:
        st.markdown("**Historial de revisiones**")
        st.dataframe(
            pd.DataFrame([{"Fecha": p["momento"].replace("T", " "), "Decisión": ESTADOS[p["decision"]],
                           "Nota": p["nota"] or ""} for p in pasos]),
            hide_index=True, width="stretch",
        )


def seccion_convergencia(registro: Registro, dic: Diccionario, eid: int) -> None:
    rondas = registro.rondas(eid)
    st.markdown("Cada ronda induce reglas con un árbol de decisión y genera casos dirigidos. "
                "El ciclo se detiene cuando una ronda no encuentra contradicciones ni umbrales nuevos.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Consultas acumuladas al sistema**")
        st.altair_chart(grafico_linea(rondas, "ronda", "consultas_acumuladas", "Ronda", "Consultas"),
                        width="stretch")
    with c2:
        st.markdown("**Contradicciones encontradas por ronda**")
        st.altair_chart(grafico_barras(rondas[rondas["ronda"] > 0], "ronda", "contradicciones", "Ronda",
                                       "Contradicciones"), width="stretch")
    st.dataframe(
        rondas.drop(columns=["ejecucion_id"]).rename(columns={
            "ronda": "Ronda", "consultas_acumuladas": "Consultas acumuladas", "reglas": "Reglas del árbol",
            "contradicciones": "Contradicciones", "umbrales_nuevos": "Umbrales nuevos"}),
        hide_index=True, width="stretch",
    )

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Casos registrados por origen**")
        casos = registro.casos(eid)
        conteo = casos["origen"].map(ORIGENES).fillna(casos["origen"]).value_counts().reset_index()
        conteo.columns = ["Origen", "Casos"]
        st.altair_chart(grafico_barras(conteo, "Origen", "Casos", "Origen", "Casos", horizontal=True),
                        width="stretch")
    with c4:
        st.markdown("**Umbrales confirmados por bisección**")
        umbrales = registro.umbrales(eid)
        if umbrales.empty:
            st.write("No se confirmaron umbrales.")
        else:
            st.dataframe(
                pd.DataFrame({
                    "Campo": [dic.campo(c).etiqueta.capitalize() for c in umbrales["campo"]],
                    "Cambia en": [formato_miles(int(v)) for v in umbrales["valor_cambio"]],
                    "Antes": umbrales["decision_baja"],
                    "Desde": umbrales["decision_alta"],
                    "Ronda": umbrales["ronda"],
                }),
                hide_index=True, width="stretch",
            )


def seccion_verificacion(registro: Registro, dic: Diccionario, eid: int, reglas: list[dict]) -> None:
    st.markdown("Repite los casos registrados en este descubrimiento sobre otra versión del sistema y "
                "muestra en qué reglas cambian las decisiones.")
    objetivos = list(json.loads(RUTA_OBJETIVOS.read_text(encoding="utf-8")))
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    objetivo = c1.selectbox("Versión a comparar", objetivos, key="objetivo_verificacion",
                            index=objetivos.index("modernizado") if "modernizado" in objetivos else 0)
    if c2.button("Ejecutar verificación", key="verificar", width="stretch"):
        with st.spinner("Repitiendo los casos registrados..."):
            resultado = Verificador(dic, registro, objetivo).verificar(eid)
        st.session_state["mensaje"] = (
            "ok", f"Verificación {resultado.ejecucion_id} terminada: {resultado.diferencias} diferencias.")
        st.session_state["verificacion"] = resultado.ejecucion_id
        st.rerun()

    verificaciones = {v["id"]: v for v in registro.ejecuciones("verificacion") if v["ejecucion_base_id"] == eid}
    if not verificaciones:
        st.info("Todavía no hay verificaciones de este descubrimiento. Usa el botón de arriba o ejecuta: "
                f"`python -m ghostmind verificar --ejecucion {eid} --objetivo modernizado`")
        return
    opciones = sorted(verificaciones, reverse=True)
    if st.session_state.get("verificacion") not in opciones:
        st.session_state["verificacion"] = opciones[0]
    vid = st.selectbox("Verificación", opciones, key="verificacion",
                       format_func=lambda i: (f"#{i} · {verificaciones[i]['objetivo']} · "
                                              f"{verificaciones[i]['inicio'][:16].replace('T', ' ')}"))
    diferencias = registro.diferencias(vid)
    errores = int(registro.casos(vid)["decision"].isna().sum())
    afectadas = diferencias["codigo"].dropna().nunique() if not diferencias.empty else 0
    m = st.columns(4)
    m[0].metric("Casos repetidos", formato_miles(verificaciones[vid]["consultas"]))
    m[1].metric("Diferencias", formato_miles(len(diferencias)))
    m[2].metric("Reglas con diferencias", f"{afectadas} de {len(reglas)}")
    m[3].metric("Errores del sistema", errores)
    if diferencias.empty:
        st.success("Ninguna decisión cambió: la versión comparada conserva todas las reglas observadas.")
        return

    por_codigo = {r["codigo"]: r for r in reglas}
    resumen = []
    for codigo, grupo in diferencias.groupby("codigo", sort=True):
        regla = por_codigo[codigo]
        cambios = (grupo["decision_original"] + " → " + grupo["decision_nueva"]).value_counts()
        resumen.append({
            "Código": codigo,
            "Decisión de la regla": regla["decision"],
            "Regla": regla["texto_llm"] or regla["texto_negocio"],
            "Casos de la regla": regla["respaldo"] + regla["contraejemplos"],
            "Diferencias": len(grupo),
            "Cambios": "; ".join(f"{c} ({formato_miles(int(n))})" for c, n in cambios.items()),
        })
    resumen = pd.DataFrame(resumen).sort_values("Diferencias", ascending=False, kind="stable")
    izquierda, derecha = st.columns([3, 2])
    with izquierda:
        st.markdown("**Reglas con diferencias**")
        st.dataframe(resumen, hide_index=True, width="stretch",
                     column_config={"Regla": st.column_config.TextColumn("Regla", width="large")})
    with derecha:
        st.markdown("**Diferencias por regla**")
        st.altair_chart(grafico_barras(resumen, "Código", "Diferencias", "Regla", "Diferencias", horizontal=True),
                        width="stretch")
    sin_regla = int(diferencias["codigo"].isna().sum())
    if sin_regla:
        st.warning(f"{sin_regla} diferencias en casos que no caen en ninguna regla.")
    with st.expander(f"Casos con diferencias ({formato_miles(len(diferencias))}; se muestran hasta 100)"):
        vista = con_miles(diferencias.head(100)[["codigo", *dic.nombres, "decision_original", "decision_nueva"]], dic)
        nombres = {"codigo": "Regla", "decision_original": "Antes", "decision_nueva": "Ahora"}
        nombres.update({c.nombre: c.etiqueta.capitalize() for c in dic.campos})
        st.dataframe(vista.rename(columns=nombres), hide_index=True, width="stretch")


def principal(registro: Registro, dic: Diccionario, ruta: Path) -> None:
    st.title("GhostMind IA")
    st.caption("Catálogo de reglas de negocio descubiertas observando el sistema legacy como caja negra. "
               "Ninguna regla se acepta sola: el especialista valida o rechaza cada una.")
    ejecuciones = registro.ejecuciones("descubrimiento")
    if not ejecuciones:
        st.info(f"Todavía no hay ejecuciones de descubrimiento en `{ruta}`. Para crear una, ejecuta en la "
                "raíz del repositorio: `python -m ghostmind descubrir --objetivo legacy --semilla 42`")
        st.stop()

    por_id = {e["id"]: e for e in ejecuciones}
    # Enlaces directos: ?ejecucion=1&regla=GM-05 abren esa ejecución y esa regla.
    pedida = st.query_params.get("ejecucion")
    if "ejecucion" not in st.session_state and pedida and pedida.isdigit() and int(pedida) in por_id:
        st.session_state["ejecucion"] = int(pedida)
    with st.sidebar:
        st.header("Ejecución")
        eid = st.selectbox(
            "Descubrimiento", sorted(por_id, reverse=True), key="ejecucion",
            format_func=lambda i: (f"#{i} · {por_id[i]['objetivo']} · semilla {por_id[i]['semilla']} · "
                                   f"{por_id[i]['inicio'][:16].replace('T', ' ')}"),
        )
        st.header("Filtros")
        filtros = {
            "decisiones": st.multiselect("Decisión", list(dic.decisiones), default=list(dic.decisiones),
                                         key="filtro_decision"),
            "estados": st.multiselect("Estado", list(ESTADOS), default=list(ESTADOS), format_func=ESTADOS.get,
                                      key="filtro_estado"),
            "confianza": st.slider("Confianza mínima (%)", 0, 100, 0, key="filtro_confianza"),
        }
        st.header("Exportar")
        st.download_button(
            "Descargar catálogo (JSON)",
            data=json.dumps(exportar(registro, eid), ensure_ascii=False, indent=2),
            file_name=f"catalogo_ejecucion_{eid}.json", mime="application/json", key="exportar",
            width="stretch",
        )
        st.header("Redacción asistida")
        if redactor_llm.llm_habilitado():
            st.caption(f"Activada con el modelo {redactor_llm.modelo()}.")
        else:
            st.caption("Desactivada; se usa la redacción por plantilla. Se activa con GHOSTMIND_LLM=1 y "
                       "ANTHROPIC_API_KEY.")

    ejecucion = registro.ejecucion(eid)
    reglas = registro.reglas(eid)
    m = st.columns(5)
    m[0].metric("Consultas al sistema", formato_miles(ejecucion["consultas"]))
    m[1].metric("Rondas", ejecucion["rondas"])
    m[2].metric("Motivo de parada", MOTIVOS.get(ejecucion["motivo_parada"], ejecucion["motivo_parada"] or "-"))
    m[3].metric("Reglas descubiertas", len(reglas))
    m[4].metric("Validadas por especialista", sum(r["estado"] == "validada" for r in reglas))
    mostrar_mensaje_pendiente()

    pestanas = st.tabs(["Reglas", "Convergencia", "Verificación"])
    with pestanas[0]:
        seccion_reglas(registro, dic, reglas, filtros)
    with pestanas[1]:
        seccion_convergencia(registro, dic, eid)
    with pestanas[2]:
        seccion_verificacion(registro, dic, eid, reglas)


dic = Diccionario.cargar()
ruta_db = Path(os.environ.get("GHOSTMIND_DB") or ruta_por_defecto())
registro = Registro(ruta_db, dic)
try:
    principal(registro, dic, ruta_db)
finally:
    registro.cerrar()
