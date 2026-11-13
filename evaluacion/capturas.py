"""Capturas del catálogo para el informe (FR-026).

Uso, después de ``python -m evaluacion.experimento``:

    pip install -r requirements-capturas.txt
    python -m evaluacion.capturas

Levanta el catálogo en Streamlit con la base del experimento, lo abre con Microsoft Edge sin
interfaz (Playwright, canal ``msedge``) y guarda imágenes en ``resultados/capturas/``. Las
imágenes muestran la ejecución real de la semilla principal; nada se edita a mano.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from evaluacion.experimento import BD_EXPERIMENTO, SALIDA, SEMILLA_PRINCIPAL
from ghostmind.diccionario import RAIZ, Diccionario
from ghostmind.registro import Registro

APP = RAIZ / "app" / "catalogo.py"
ANCHO, ALTO = 1440, 900


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def esperar_servidor(url: str, limite: float = 90) -> None:
    fin = time.time() + limite
    while time.time() < fin:
        try:
            with urllib.request.urlopen(url + "/_stcore/health", timeout=2) as r:
                if r.status == 200:
                    return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError("El catálogo no respondió a tiempo.")


def elegir_ejecucion_y_regla(db: Path, semilla: int) -> tuple[int, str]:
    """Ejecución de descubrimiento de la semilla y la regla con más umbrales confirmados."""
    registro = Registro(db, Diccionario.cargar())
    try:
        ejecucion = next(e for e in registro.ejecuciones("descubrimiento") if e["semilla"] == semilla)
        reglas = registro.reglas(ejecucion["id"])
    finally:
        registro.cerrar()
    regla = max(reglas, key=lambda r: (len(r["umbrales_confirmados"]), r["respaldo"]))
    return ejecucion["id"], regla["codigo"]


def capturar(db: Path = BD_EXPERIMENTO, salida: Path = SALIDA / "capturas", semilla: int = SEMILLA_PRINCIPAL) -> list[Path]:
    from playwright.sync_api import sync_playwright

    if not Path(db).exists():
        raise FileNotFoundError("No existe la base del experimento. Ejecuta primero: python -m evaluacion.experimento")
    salida.mkdir(parents=True, exist_ok=True)
    ejecucion, regla = elegir_ejecucion_y_regla(db, semilla)
    puerto = puerto_libre()
    url = f"http://127.0.0.1:{puerto}"
    entorno = {**os.environ, "GHOSTMIND_DB": str(db), "GHOSTMIND_LLM": "0"}
    servidor = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(APP), "--server.port", str(puerto),
         "--server.address", "127.0.0.1", "--server.headless", "true"],
        cwd=RAIZ, env=entorno, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    archivos: list[Path] = []
    try:
        esperar_servidor(url)
        with sync_playwright() as p:
            navegador = p.chromium.launch(channel="msedge", headless=True)
            pagina = navegador.new_page(viewport={"width": ANCHO, "height": ALTO}, device_scale_factor=1.5)

            def listo() -> None:
                pagina.get_by_text("GhostMind IA", exact=True).first.wait_for(timeout=60_000)
                pagina.wait_for_load_state("networkidle")
                pagina.wait_for_timeout(2500)

            def guardar(nombre: str) -> None:
                ruta = salida / nombre
                pagina.screenshot(path=str(ruta))
                archivos.append(ruta)

            pagina.goto(f"{url}/?ejecucion={ejecucion}&regla={regla}")
            listo()
            guardar("01_catalogo_reglas.png")

            pagina.get_by_text("Detalle de la regla", exact=True).first.scroll_into_view_if_needed()
            pagina.mouse.wheel(0, -60)
            pagina.wait_for_timeout(800)
            guardar("02_detalle_regla.png")

            pagina.get_by_text("Revisión del especialista", exact=True).first.scroll_into_view_if_needed()
            pagina.wait_for_timeout(800)
            guardar("03_evidencia_y_revision.png")

            pagina.evaluate("window.scrollTo(0, 0)")
            pagina.get_by_role("tab", name="Convergencia").click()
            pagina.wait_for_timeout(3000)
            guardar("04_convergencia.png")

            pagina.get_by_role("tab", name="Verificación").click()
            pagina.wait_for_timeout(3000)
            guardar("05_verificacion.png")
            navegador.close()
    finally:
        servidor.terminate()
        try:
            servidor.wait(timeout=15)
        except subprocess.TimeoutExpired:
            servidor.kill()
    return archivos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evaluacion.capturas")
    parser.add_argument("--db", default=str(BD_EXPERIMENTO))
    parser.add_argument("--salida", default=str(SALIDA / "capturas"))
    args = parser.parse_args(argv)
    try:
        archivos = capturar(Path(args.db), Path(args.salida))
    except ImportError:
        print("Falta Playwright: pip install -r requirements-capturas.txt", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    for ruta in archivos:
        print(f"Captura guardada: {ruta.relative_to(RAIZ).as_posix() if ruta.is_relative_to(RAIZ) else ruta.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
