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
| 5 | Catálogo en Streamlit | Lista |
| 6 | Versión modernizada y verificador diferencial | Lista |
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

## Catálogo para el especialista (disponible desde la fase 5)

```bash
streamlit run app/catalogo.py
```

Muestra las reglas de cada ejecución con su redacción de negocio, condiciones, umbrales confirmados, confianza, estado y evidencia (casos que la respaldan y contraejemplos). El especialista valida o rechaza cada regla con una nota, y el catálogo se descarga en JSON. También se puede exportar desde la terminal:

```bash
python -m ghostmind exportar --ejecucion 1 --salida catalogo.json
```

### Redacción con modelo de lenguaje (opcional, desactivada por defecto)

GhostMind puede pedir a Claude una redacción más natural de cada regla. Nunca cambia condiciones ni decisiones, y si la redacción menciona valores que no están en la regla o cambia la decisión, se descarta y se mantiene la redacción por plantilla. Para activarla:

```bash
pip install -r requirements-llm.txt
```

Luego define las variables de entorno `GHOSTMIND_LLM=1` y `ANTHROPIC_API_KEY` (la llave nunca se guarda en el repositorio). Opcionalmente, `GHOSTMIND_LLM_MODELO` cambia el modelo (por defecto `claude-opus-5-5`).

## Verificar una versión modernizada (disponible desde la fase 6)

```bash
python -m ghostmind verificar --ejecucion 1 --objetivo modernizado
```

Repite sobre la versión modernizada (`legacy/crdapr_moderno.py`) todos los casos registrados en el descubrimiento y agrupa las diferencias por regla descubierta. Con `--objetivo legacy` sirve de control: debe dar cero diferencias. El reporte también se ve en la pestaña Verificación del catálogo, que permite lanzar la verificación con un botón.

## Estructura actual

| Carpeta | Contenido |
|---------|-----------|
| `sistemas/` | Diccionario de campos y puntos de entrada: lo único que GhostMind conoce del sistema |
| `legacy/` | Sistema legacy simulado de aprobación de créditos y su versión modernizada (GhostMind no los lee) |
| `ghostmind/` | El producto: diccionario, adaptador, registro SQLite, muestreo, extractor, explorador, catálogo, redacción opcional y verificador |
| `app/` | Interfaz del catálogo en Streamlit |
| `evaluacion/` | Reglas verdaderas, alteraciones de la versión modernizada y evaluador; solo los usa la evaluación del experimento |
| `tests/` | Pruebas automáticas |

Las instrucciones para ejecutar el prototipo se completarán al cerrar la fase 7.
