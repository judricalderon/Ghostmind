# GhostMind IA: prototipo (MVP)

Prototipo de GhostMind IA, una herramienta que descubre reglas de negocio ocultas en un sistema legacy observando su comportamiento como caja negra. Cada regla queda con su evidencia y un nivel de confianza para que un especialista la valide antes de modernizar el sistema.

Proyecto académico de la asignatura Gestión de Tecnología e Innovación, Universidad El Bosque, semestre 2026-2.

## Estado

En construcción por fases con un proceso dirigido por especificaciones ([Spec Kit](https://github.com/github/spec-kit) 1.4.0). La constitución, la especificación, el plan y las tareas quedan en `.specify/` y `specs/`.

| Fase | Contenido | Estado |
|------|-----------|--------|
| 0 | Preparación del repositorio y de Spec Kit | Lista |
| 1 | Constitución, especificación, plan y tareas | Lista |
| 2 | Sistema legacy simulado y reglas verdaderas | Lista |
| 3 | Adaptador, explorador (muestreo inicial) y registro SQLite | Lista |
| 4 | Extractor de reglas, umbrales y confianza | Lista |
| 5 | Catálogo en Streamlit | Pendiente |
| 6 | Versión modernizada y verificador diferencial | Pendiente |
| 7 | Evaluación del experimento y resultados | Pendiente |

## Preparar el entorno

Requisitos: Python 3.11 o superior y git.

```bash
python -m venv .venv
```

En Windows (PowerShell):

```bash
.venv\Scripts\Activate.ps1
```

En Linux o macOS:

```bash
source .venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Ejecutar las pruebas

```bash
python -m pytest
```

## Descubrir reglas (disponible desde la fase 4)

```bash
python -m ghostmind descubrir --objetivo legacy --semilla 42 --presupuesto 20000
python -m ghostmind reglas --ejecucion 1
```

La base de evidencia queda en `datos/ghostmind.sqlite`; se puede cambiar con `--db` o con la variable `GHOSTMIND_DB`.

## Estructura actual

| Carpeta | Contenido |
|---------|-----------|
| `sistemas/` | Diccionario de campos y puntos de entrada: lo único que GhostMind conoce del sistema |
| `legacy/` | Sistema legacy simulado de aprobación de créditos (GhostMind no lo lee) |
| `ghostmind/` | El producto: diccionario, adaptador, registro SQLite, muestreo, extractor y explorador |
| `evaluacion/` | Reglas verdaderas y evaluador; solo los usa la evaluación del experimento |
| `tests/` | Pruebas automáticas |

Las instrucciones para ejecutar el prototipo se completarán al cerrar la fase 7.
