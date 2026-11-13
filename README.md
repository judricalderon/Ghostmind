# GhostMind IA: prototipo (MVP)

Prototipo de GhostMind IA, una herramienta que descubre reglas de negocio ocultas en un sistema legacy observando su comportamiento como caja negra. Cada regla queda con su evidencia y un nivel de confianza para que un especialista la valide antes de modernizar el sistema.

Proyecto académico de la asignatura Gestión de Tecnología e Innovación, Universidad El Bosque, semestre 2026-2.

## Estado

En construcción por fases con un proceso dirigido por especificaciones ([Spec Kit](https://github.com/github/spec-kit) 1.4.0). La constitución, la especificación, el plan y las tareas quedan en `.specify/` y `specs/`.

| Fase | Contenido | Estado |
|------|-----------|--------|
| 0 | Preparación del repositorio y de Spec Kit | Lista |
| 1 | Constitución, especificación, plan y tareas | Pendiente |
| 2 | Sistema legacy simulado y reglas verdaderas | Pendiente |
| 3 | Adaptador, explorador y registro SQLite | Pendiente |
| 4 | Extractor de reglas, umbrales y confianza | Pendiente |
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

Las instrucciones para ejecutar el prototipo se completarán al cerrar la fase 7.
