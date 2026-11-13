# Plan de implementación: MVP de GhostMind IA

**Rama**: `main` | **Fecha**: 2026-11-12 | **Especificación**: [spec.md](spec.md)

**Entrada**: especificación de `specs/001-ghostmind-mvp/spec.md`

## Resumen

Se construye un experimento controlado en Python. Un módulo legacy simulado de aprobación de
créditos aplica 10 reglas plantadas (D4) detrás de una interfaz de registro de ancho fijo (D2).
GhostMind lo explora como caja negra: el adaptador es su único contacto; el explorador combina
muestreo inicial (D5) con rondas de bisección de umbrales, búsqueda de contraejemplos y
exploración local (D7); el extractor induce un árbol de decisión y convierte cada hoja en una regla
con evidencia, confianza de Wilson y estado (D6, D8). Todo queda en SQLite. Un catálogo en
Streamlit permite revisar, aprobar, rechazar y exportar reglas, y muestra el verificador
diferencial (D10), que repite los casos sobre una versión modernizada con tres alteraciones (D11).
Un módulo de evaluación, separado de GhostMind, es el único que lee las reglas verdaderas y calcula
C1, C2, C3 y C5 (D12).

## Contexto técnico

**Lenguaje y versión**: Python 3.11 (probado con 3.11.9)

**Dependencias principales**: pandas 3.1.1, scikit-learn 1.9.1, numpy 2.4.6, Streamlit 1.67.0.
Opcionales: `anthropic` (redacción con modelo de lenguaje) y Playwright con Edge (capturas).

**Almacenamiento**: SQLite en un archivo local (`datos/ghostmind.sqlite`)

**Pruebas**: pytest 9.2

**Plataforma**: computador personal con Windows, Linux o macOS; sin servidor

**Tipo de proyecto**: biblioteca con interfaz de línea de comandos y aplicación local en Streamlit

**Metas de desempeño**: descubrimiento completo en menos de 10 minutos; evaluación con 6 semillas
en menos de 30 minutos

**Restricciones**: determinismo por semilla; presupuesto de 20.000 consultas; sin red salvo el
modelo de lenguaje opcional; sin llaves ni datos personales en el repositorio

**Escala**: 8 campos, 3 decisiones, 10 reglas plantadas, del orden de 10.000 a 20.000 casos por
ejecución

## Verificación de la constitución

*Compuerta: debe cumplirse antes de investigar y revisarse después del diseño.*

| Principio | Cómo lo cumple el diseño | Estado |
|-----------|--------------------------|--------|
| I. Caja negra estricta | GhostMind recibe solo `sistemas/diccionario_credito.json`; el adaptador resuelve el punto de entrada desde `sistemas/objetivos.json`; prueba de arquitectura que falla si `ghostmind/` importa `legacy` o `evaluacion` o menciona sus archivos | Cumple |
| II. Evidencia y trazabilidad | Cada consulta se guarda en `casos` antes de devolverse; `umbrales`, `regla_casos` y `rondas` enlazan reglas y evidencia; el adaptador cuenta las consultas | Cumple |
| III. Honestidad experimental | Métricas y umbrales fijados en la especificación; reglas, alteraciones y semillas fijadas en D4, D11 y la especificación; `resultados/` solo se escribe desde `evaluacion.experimento` | Cumple |
| IV. Humano en el ciclo | GhostMind asigna solo `hipotesis` y `corroborada`; `validada` y `rechazada` solo desde el catálogo, con historial en `revisiones` | Cumple |
| V. Reproducibilidad y simplicidad | Semillas en todo el flujo; árbol de decisión interpretable; modelo de lenguaje opcional y desactivado; complejidad extra justificada abajo | Cumple |
| Restricciones técnicas | Herramientas de la Tabla 3 del informe; llave por variable de entorno; datos sintéticos | Cumple |
| Flujo por fases | Las tareas se agrupan en las fases 2 a 7 del encargo, cada una con pruebas y commit | Cumple |

Revisión después del diseño (data-model y contratos): sin cambios; sigue cumpliendo.

## Estructura del proyecto

### Documentación (esta funcionalidad)

```text
specs/001-ghostmind-mvp/
├── spec.md              # especificación
├── plan.md              # este archivo
├── research.md          # decisiones D1 a D14 (incluye reglas plantadas y alteraciones)
├── data-model.md        # SQLite, catálogo JSON y datos de evaluación
├── quickstart.md        # escenarios de validación
├── contracts/           # diccionario, adaptador, CLI y catálogo JSON
├── checklists/          # lista de calidad de la especificación
└── tasks.md             # tareas por fase
```

### Código fuente (raíz del repositorio)

```text
sistemas/                       # lo que GhostMind sí conoce
├── diccionario_credito.json    # campos, tipos, rangos, registro y decisiones
└── objetivos.json              # nombre de objetivo -> punto de entrada

legacy/                         # sistemas bajo prueba (GhostMind no los lee)
├── __init__.py
├── crdapr01.py                 # legacy simulado, estilo antiguo (Fase 2)
└── crdapr_moderno.py           # versión modernizada con 3 alteraciones (Fase 6)

ghostmind/                      # el producto
├── __init__.py
├── __main__.py                 # órdenes descubrir, verificar, exportar, reglas
├── diccionario.py              # carga y valida el diccionario; arma registros
├── adaptador.py                # único contacto con el sistema; cuenta consultas
├── registro.py                 # SQLite: esquema, escritura y consultas
├── muestreo.py                 # muestreo inicial (D5)
├── reglas.py                   # caja, regla, confianza de Wilson, estados, redacción por plantilla
├── extractor.py                # árbol de decisión -> reglas (D6)
├── explorador.py               # rondas: bisección, contraejemplos, exploración local, parada (D7)
├── catalogo.py                 # revisiones del especialista y exportación JSON
├── redactor_llm.py             # redacción opcional con modelo de lenguaje (Fase 5)
└── verificador.py              # verificación diferencial (Fase 6)

app/
└── catalogo.py                 # interfaz Streamlit: catálogo, evidencia, verificación

evaluacion/                     # fuera de GhostMind; único lector de las reglas verdaderas
├── __init__.py
├── reglas_verdaderas.json
├── alteraciones.json
├── verdad.py                   # evaluador declarativo de reglas verdaderas y alteraciones
├── metricas.py                 # pureza, cobertura, C1, C2, C3, C5
├── experimento.py              # orquesta la evaluación y escribe resultados/
├── capturas.py                 # capturas del catálogo con Playwright y Edge
└── instrumento_c4/             # cuestionario, clave, plantilla y puntuar.py

resultados/                     # generado por evaluacion.experimento (se versiona)
datos/                          # SQLite local (excluido de git)

tests/
├── test_diccionario.py
├── test_legacy.py              # legacy contra reglas verdaderas y fracciones efectivas
├── test_verdad.py              # evaluador declarativo
├── test_arquitectura.py        # caja negra estricta
├── test_adaptador.py
├── test_registro.py
├── test_muestreo.py
├── test_reglas.py
├── test_extractor.py
├── test_explorador.py
├── test_catalogo.py
├── test_app.py                 # prueba de la interfaz con streamlit.testing
├── test_redactor_llm.py        # con cliente simulado, sin red
├── test_moderno.py
├── test_verificador.py
├── test_metricas.py
└── test_experimento.py
```

**Decisión de estructura**: proyecto único. La separación en carpetas refleja la frontera del
experimento: `sistemas/` es lo que GhostMind puede leer; `legacy/` y `evaluacion/` quedan fuera de
su alcance y una prueba lo comprueba.

## Fases de implementación

| Fase | Contenido | Historias | Cierre |
|------|-----------|-----------|--------|
| 2 | Diccionario, legacy simulado, reglas verdaderas, evaluador declarativo y pruebas de concordancia | Fundacional | Legacy y `reglas_verdaderas.json` coinciden en 50.000 casos y en los bordes |
| 3 | Adaptador, registro SQLite, muestreo inicial, prueba de caja negra | US1 (parte A) | 720 consultas registradas y contadas con la semilla 42 |
| 4 | Extractor, bisección, contraejemplos, exploración local, confianza, estados, orden `descubrir` | US1 (parte B) | Descubrimiento completo, determinista y bajo presupuesto |
| 5 | Catálogo en Streamlit, revisiones, exportación JSON, redacción opcional | US2 | Aprobar, rechazar y exportar funcionan y persisten |
| 6 | Versión modernizada, verificador, pestaña de verificación | US3 | Cero diferencias contra el legacy y diferencias contra el modernizado |
| 7 | Métricas, experimento, robustez, instrumento C4, capturas, README | US4 | `resultados/` generado por ejecución real |
| 8 | Elegir la caja negra y descubrir desde el catálogo (agregada el 2026-11-13) | US1 y US2 | Descubrimiento lanzado desde la interfaz, con pruebas |

## Seguimiento de complejidad

| Elemento | Por qué hace falta | Alternativa más simple descartada |
|----------|--------------------|-----------------------------------|
| Registro de ancho fijo entre adaptador y legacy | Representa una interfaz legacy real y obliga a que GhostMind dependa solo del documento de interfaz | Argumentos con nombre: más simple, pero acerca el código de GhostMind al del legacy |
| Exploración local alrededor de contraejemplos | Sin ella, una región pequeña hallada por azar no reúne casos suficientes para separarse en el árbol | Solo bisección de umbrales del árbol: no explora lo que el árbol todavía no ve |
| Evaluador declarativo de reglas verdaderas | Permite calcular pureza, cobertura y C5 por región y comprobar el legacy contra una segunda implementación | Consultar solo el legacy: no dice qué regla decidió cada caso |
