---
description: "Tareas del MVP de GhostMind IA, agrupadas por las fases del encargo"
---

# Tareas: MVP de GhostMind IA

**Entrada**: documentos de diseño en `specs/001-ghostmind-mvp/`

**Prerrequisitos**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Pruebas**: obligatorias. La constitución (principio V) exige que cada fase termine con pruebas
automáticas que pasan; dentro de cada fase las pruebas se escriben antes que la implementación.

**Organización**: las fases de este archivo siguen las fases 0 a 7 del encargo. La historia 1 se
reparte entre las fases 3 y 4; las demás historias tienen una fase cada una.

## Formato: `[Id] [P?] [Historia] Descripción`

- **[P]**: puede hacerse en paralelo (archivos distintos, sin dependencias pendientes)
- **[US1] a [US4]**: historia de usuario de la especificación
- Las rutas son relativas a la raíz del repositorio

---

## Fase 0: Preparación (lista)

**Propósito**: repositorio, Spec Kit y entorno

- [X] T001 Inicializar git y Spec Kit 1.4.0 para Claude Code en `.specify/` y `.claude/skills/`
- [X] T002 [P] Crear `.gitignore`, `requirements.txt` y `README.md` base
- [X] T003 Crear entorno virtual con las dependencias fijadas en `requirements.txt`

## Fase 1: Especificación (lista al aprobarse)

- [X] T004 Constitución en `.specify/memory/constitution.md`
- [X] T005 Especificación, plan, investigación, modelo de datos, contratos y guía en `specs/001-ghostmind-mvp/`
- [X] T006 Tareas en `specs/001-ghostmind-mvp/tasks.md`

---

## Fase 2: Escenario controlado (fundacional)

**Propósito**: el sistema legacy simulado, lo que GhostMind puede saber de él y la verdad que solo
conoce la evaluación. Bloquea todas las historias.

### Pruebas de la Fase 2

- [X] T007 [P] Pruebas del diccionario en `tests/test_diccionario.py`: nombres únicos, `minimo` ≤ `maximo`, campos sin traslape en las 35 posiciones, códigos que caben en su longitud, armado y lectura del registro de ancho fijo (ejemplo de contracts/diccionario.md)
- [X] T008 [P] Pruebas del legacy en `tests/test_legacy.py`: solo devuelve `APROBADO`, `RECHAZADO` o `REVISION_MANUAL`; coincide con el evaluador declarativo en 50.000 solicitudes uniformes (semilla fija) y en todas las combinaciones de valores límite y categorías; cada regla R01 a R10 tiene al menos un caso propio; la fracción efectiva de R03 es menor que 0,1 %
- [X] T009 [P] Pruebas del evaluador declarativo en `tests/test_verdad.py`: precedencia, comportamiento por defecto, identificación de la regla que decide, y ejemplos escritos a mano para cada regla

### Implementación de la Fase 2

- [X] T010 [P] Crear `sistemas/diccionario_credito.json` y `sistemas/objetivos.json` según contracts/diccionario.md (8 campos, rangos de D3, registro de 35 posiciones)
- [X] T011 [P] Implementar `ghostmind/diccionario.py`: cargar y validar el diccionario, solicitudes válidas, armar y leer el registro de ancho fijo
- [X] T012 [P] Implementar el legacy en `legacy/crdapr01.py` con estilo antiguo (condicionales anidados, nombres crípticos, números fijos), punto de entrada `CRDAPR01(WK_REG)` y las 10 reglas de D4 en su orden de precedencia
- [X] T013 [P] Crear `evaluacion/reglas_verdaderas.json` con R01 a R10 en formato de caja y la decisión por defecto `APROBADO` (data-model.md, sección 4)
- [X] T014 Implementar `evaluacion/verdad.py`: evaluador declarativo que devuelve la decisión y la regla que decide (depende de T013)
- [X] T015 Medir y registrar en la salida de la prueba la fracción efectiva de cada regla con muestreo uniforme (en `tests/test_legacy.py`)

**Punto de control**: `python -m pytest` pasa; legacy y reglas verdaderas coinciden.

---

## Fase 3: Historia 1, parte A: adaptador, registro y muestreo inicial (P1)

**Objetivo**: GhostMind consulta el legacy solo por el adaptador, registra cada consulta y hace el
muestreo inicial.

**Prueba independiente**: con la semilla 42, el muestreo inicial produce 720 casos registrados,
contados y reproducibles.

### Pruebas de la Fase 3

- [X] T016 [P] [US1] Prueba de caja negra en `tests/test_arquitectura.py`: ningún archivo de `ghostmind/` importa `legacy` ni `evaluacion` ni menciona `reglas_verdaderas` o `alteraciones`; solo `ghostmind/adaptador.py` resuelve puntos de entrada
- [X] T017 [P] [US1] Pruebas del adaptador en `tests/test_adaptador.py`: rechaza solicitudes inválidas sin contar; `PresupuestoAgotado` al llegar al límite; registra error y lanza `ErrorDelSistema` ante respuestas inesperadas; `consultas` coincide con las filas de `casos`
- [X] T018 [P] [US1] Pruebas del registro en `tests/test_registro.py`: esquema de data-model.md, escritura de ejecuciones, casos, rondas y lectura por ejecución
- [X] T019 [P] [US1] Pruebas del muestreo en `tests/test_muestreo.py`: 400 aleatorios, 120 de límites (mínimo y máximo de cada campo numérico), 200 de categorías (las 20 combinaciones); todo dentro del diccionario; misma semilla, mismas solicitudes

### Implementación de la Fase 3

- [X] T020 [P] [US1] Implementar `ghostmind/registro.py` con las tablas `ejecuciones`, `casos`, `umbrales`, `rondas`, `reglas`, `regla_casos`, `revisiones` y `diferencias` de data-model.md
- [X] T021 [US1] Implementar `ghostmind/adaptador.py` según contracts/adaptador.md (depende de T011 y T020)
- [X] T022 [P] [US1] Implementar `ghostmind/muestreo.py` con el muestreo inicial de D5
- [X] T023 [US1] Orden preliminar `python -m ghostmind muestrear` en `ghostmind/__main__.py` que crea la ejecución y corre el muestreo inicial

**Punto de control**: 720 consultas registradas con origen y ronda 0; pruebas pasando.

---

## Fase 4: Historia 1, parte B: extractor, rondas, confianza y estados (P1) 🎯 MVP

**Objetivo**: GhostMind entrega reglas legibles con evidencia, confianza y estado, deteniéndose por
estabilidad o por presupuesto.

**Prueba independiente**: `python -m ghostmind descubrir --semilla 42` termina en menos de 10
minutos, es determinista y no supera el presupuesto.

### Pruebas de la Fase 4

- [ ] T024 [P] [US1] Pruebas de reglas en `tests/test_reglas.py`: conversión de umbrales a enteros (`x <= t` a `x ≤ floor(t)`, `x > t` a `x ≥ floor(t) + 1`), pertenencia de un caso a una caja, confianza de Wilson con los ejemplos de D8, reglas de estado, redacción técnica y de negocio sin condiciones de dominio
- [ ] T025 [P] [US1] Pruebas del extractor en `tests/test_extractor.py`: con datos sintéticos de una regla simple, el árbol produce la caja esperada; respaldo y contraejemplos correctos
- [ ] T026 [P] [US1] Pruebas del explorador en `tests/test_explorador.py`: la bisección encuentra el punto exacto de cambio en un sistema de prueba con umbral conocido; la búsqueda de contraejemplos los registra; parada por estabilidad, por presupuesto, por máximo de rondas y por errores; un presupuesto menor que el muestreo inicial da error antes de consultar; misma semilla, mismo resultado

### Implementación de la Fase 4

- [ ] T027 [P] [US1] Implementar `ghostmind/reglas.py`: caja, regla, confianza de Wilson al 95 %, estados (`hipotesis`, `corroborada`, `validada`, `rechazada`) y redacción por plantilla (D8, D9)
- [ ] T028 [US1] Implementar `ghostmind/extractor.py`: `DecisionTreeClassifier(criterion="entropy", min_samples_leaf=3, random_state=semilla)` con variables indicadoras y conversión de hojas a reglas (D6)
- [ ] T029 [US1] Implementar en `ghostmind/explorador.py` la bisección de umbrales con caché de umbrales confirmados y registro en `umbrales` (D7, paso 1)
- [ ] T030 [US1] Implementar en `ghostmind/explorador.py` la búsqueda de contraejemplos (25 por hoja más bordes) y la exploración local alrededor de hasta 10 contraejemplos por ronda (D7, pasos 2 y 3)
- [ ] T031 [US1] Implementar en `ghostmind/explorador.py` el ciclo de rondas, la tabla `rondas`, el criterio de parada y el motivo (D7, paso 4; FR-008), incluida la parada con motivo `errores` si las respuestas inválidas del sistema superan el 1 % de las consultas
- [ ] T032 [US1] Guardar las reglas finales con evidencia (`regla_casos`), confianza y estado `corroborada` según D8 en `ghostmind/registro.py`
- [ ] T033 [US1] Órdenes `descubrir` y `reglas` en `ghostmind/__main__.py` según contracts/cli.md, con tabla de reglas en la terminal

**Punto de control**: historia 1 completa y demostrable de forma independiente.

---

## Fase 5: Historia 2: catálogo para revisión (P2)

**Objetivo**: el especialista revisa, aprueba, rechaza y exporta reglas.

**Prueba independiente**: con una ejecución guardada, aprobar y rechazar reglas, recargar y
exportar a JSON.

### Pruebas de la Fase 5

- [ ] T034 [P] [US2] Pruebas del catálogo en `tests/test_catalogo.py`: revisiones solo `validada` o `rechazada`, historial en `revisiones`, estado persistente, exportación con el formato de contracts/catalogo-json.md
- [ ] T035 [P] [US2] Pruebas de la interfaz en `tests/test_app.py` con `streamlit.testing.v1.AppTest`: carga sin ejecuciones (mensaje de ayuda), lista de reglas, filtros, aprobar y rechazar
- [ ] T036 [P] [US2] Pruebas del redactor opcional en `tests/test_redactor_llm.py`: desactivado por defecto; sin llave usa la plantilla; nunca altera condiciones ni decisión (con un cliente simulado, sin red)

### Implementación de la Fase 5

- [ ] T037 [P] [US2] Implementar `ghostmind/catalogo.py`: registrar revisiones y exportar JSON (FR-016, FR-017)
- [ ] T038 [US2] Implementar `app/catalogo.py` en Streamlit: selector de ejecución, resumen, tabla de reglas con filtros por decisión, estado y confianza, detalle con condiciones, umbrales confirmados y muestra de casos, botones de aprobar y rechazar con nota, descarga de JSON (FR-014 a FR-017)
- [ ] T039 [US2] Implementar `ghostmind/redactor_llm.py` con el SDK de Anthropic, activado solo con `GHOSTMIND_LLM=1` y `ANTHROPIC_API_KEY`, consultando antes la referencia de la API para el modelo y los parámetros; guardar el texto en `reglas.texto_llm` (FR-018)
- [ ] T040 [US2] Orden `exportar` en `ghostmind/__main__.py`

**Punto de control**: historias 1 y 2 funcionan juntas y por separado.

---

## Fase 6: Historia 3: verificación diferencial (P3)

**Objetivo**: repetir los casos registrados sobre la versión modernizada y reportar diferencias por
regla.

**Prueba independiente**: cero diferencias contra el legacy; diferencias contra el modernizado.

### Pruebas de la Fase 6

- [ ] T041 [P] [US3] Pruebas del modernizado en `tests/test_moderno.py`: coincide con el evaluador declarativo con las alteraciones A1 a A3 aplicadas en 50.000 solicitudes y difiere del legacy solo en regiones alteradas
- [ ] T042 [P] [US3] Pruebas del verificador en `tests/test_verificador.py`: contra el mismo legacy da cero diferencias; contra una versión con un umbral movido detecta la diferencia y la asocia a la regla correcta; las consultas se cuentan en una ejecución de tipo `verificacion`

### Implementación de la Fase 6

- [ ] T043 [P] [US3] Crear `evaluacion/alteraciones.json` con A1, A2 y A3 de D11
- [ ] T044 [P] [US3] Implementar `legacy/crdapr_moderno.py` en estilo actual con el mismo contrato `CRDAPR01(WK_REG)` y las tres alteraciones
- [ ] T045 [US3] Extender `evaluacion/verdad.py` para aplicar alteraciones (depende de T043)
- [ ] T046 [US3] Implementar `ghostmind/verificador.py`: repetir casos únicos, comparar, agrupar por regla y guardar en `diferencias` (D10, FR-019)
- [ ] T047 [US3] Orden `verificar` en `ghostmind/__main__.py` y pestaña de verificación en `app/catalogo.py` (FR-021)

**Punto de control**: historias 1 a 3 funcionan.

---

## Fase 7: Historia 4: evaluación del experimento y cierre (P4)

**Objetivo**: métricas reales en `resultados/`, instrumento de C4, capturas y README final.

**Prueba independiente**: `python -m evaluacion.experimento` regenera `resultados/` con las mismas
métricas.

### Pruebas de la Fase 7

- [ ] T048 [P] [US4] Pruebas de métricas en `tests/test_metricas.py`: pureza y cobertura con reglas construidas a mano (una regla exacta da pureza 1; una regla mezclada da pureza menor que 0,95); C1, C2, C3 y C5 con casos pequeños conocidos
- [ ] T049 [P] [US4] Prueba de punta a punta en `tests/test_experimento.py` con presupuesto reducido: genera los archivos esperados y las métricas se repiten con la misma semilla

### Implementación de la Fase 7

- [ ] T050 [US4] Implementar `evaluacion/metricas.py`: pureza (2.000 solicitudes por regla, umbral 95 %), asociación a regla plantada, cobertura (2.000 solicitudes por región efectiva, umbral 90 %), C1, C2, C3 (10.000 solicitudes, semilla 20261112, conteo de coincidencias con el registro) y C5 por atribución de diferencias
- [ ] T051 [US4] Implementar `evaluacion/experimento.py`: descubrimiento con semilla 42, verificación contra el modernizado, métricas, exportación del catálogo, robustez con semillas 1 a 5, y escritura de `resultados/metricas.json`, `metricas.md`, `robustez.json`, `robustez.md` y `catalogo_semilla42.json` (FR-022, FR-023, FR-025)
- [ ] T052 [P] [US4] Crear el instrumento de C4 en `evaluacion/instrumento_c4/`: `cuestionario.md`, `clave.json` generada desde las reglas verdaderas, `plantilla_respuestas.csv` y `puntuar.py` (FR-024)
- [ ] T053 [US4] Implementar `evaluacion/capturas.py` con Playwright y Edge, y `requirements-capturas.txt` (FR-026)
- [ ] T054 [US4] Ejecutar la evaluación real y las capturas; versionar `resultados/`
- [ ] T055 Completar `README.md`: instalación, ejecución de cada parte, resultados, demostración con capturas y guion de video (FR-027)
- [ ] T056 Revisión final: buscar llaves, contraseñas y datos personales en el repositorio; verificar la constitución; correr `python -m pytest` completo

**Punto de control**: todo el MVP terminado.

---

## Dependencias y orden de ejecución

### Dependencias entre fases

- Fase 2 bloquea todas las demás.
- Fase 3 depende de la Fase 2. Fase 4 depende de la Fase 3.
- Fase 5 y Fase 6 dependen de la Fase 4. Son independientes entre sí, pero se hacen en orden
  porque el encargo pide revisión entre fases y la pestaña de verificación vive en el catálogo.
- Fase 7 depende de todas.

### Dentro de cada fase

- Primero las pruebas, que deben fallar antes de implementar.
- Luego modelos y datos, después servicios y al final las órdenes y la interfaz.
- Cada fase cierra con `python -m pytest`, commit local y resumen al usuario.

### Oportunidades de paralelismo

- Fase 2: T007, T008, T009, T010, T011, T012 y T013 tocan archivos distintos.
- Fase 3: T016 a T019 en paralelo; T020 y T022 en paralelo.
- Fase 4: T024 a T026 en paralelo; T027 antes de T028.

## Ejemplo de paralelismo: Fase 3

```text
Tarea: "Prueba de caja negra en tests/test_arquitectura.py"
Tarea: "Pruebas del adaptador en tests/test_adaptador.py"
Tarea: "Pruebas del registro en tests/test_registro.py"
Tarea: "Pruebas del muestreo en tests/test_muestreo.py"
```

## Estrategia de implementación

### MVP primero

1. Fases 2, 3 y 4: al terminar la Fase 4 ya existe un descubrimiento de reglas funcional
   (historia 1), que es la hipótesis central.
2. Detenerse y revisar con el usuario.

### Entrega incremental

1. Fase 5 agrega el catálogo (historia 2).
2. Fase 6 agrega la verificación (historia 3).
3. Fase 7 mide el experimento (historia 4) y cierra el repositorio.

## Notas

- [P] significa archivos distintos y sin dependencias pendientes.
- Ninguna cifra de `resultados/` se escribe a mano.
- Las reglas plantadas (D4), las alteraciones (D11), las semillas y los umbrales de las métricas
  no cambian sin una enmienda aprobada por el usuario.
