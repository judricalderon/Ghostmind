# Guía de validación: MVP de GhostMind IA

Escenarios ejecutables que demuestran que el MVP funciona de punta a punta. Las órdenes están en
[contracts/cli.md](contracts/cli.md) y los formatos en [data-model.md](data-model.md).

## Requisitos previos

- Python 3.11 o superior y git.
- Entorno virtual con `pip install -r requirements.txt`.
- Para las capturas (Fase 7): `pip install -r requirements-capturas.txt` y Microsoft Edge instalado.
- Para la redacción opcional con modelo de lenguaje: `pip install anthropic`, `GHOSTMIND_LLM=1` y
  `ANTHROPIC_API_KEY` en el entorno. Sin esto todo funciona igual.

## Escenario 1: pruebas automáticas (todas las fases)

```bash
python -m pytest
```

Resultado esperado: todas las pruebas pasan, incluidas la de caja negra (GhostMind no referencia
`legacy` ni `evaluacion`) y la de concordancia entre el legacy y `reglas_verdaderas.json`.

## Escenario 2: descubrimiento (Historia 1)

```bash
python -m ghostmind descubrir --objetivo legacy --semilla 42 --presupuesto 20000
```

Resultado esperado: termina en menos de 10 minutos; imprime rondas, consultas (≤ 20.000), motivo
de parada y una tabla de reglas con decisión, respaldo, contraejemplos, confianza y estado.
Repetir la orden con la misma semilla produce la misma tabla y el mismo número de consultas.

## Escenario 3: catálogo (Historia 2)

```bash
streamlit run app/catalogo.py
```

Resultado esperado: se ven las reglas de la ejecución con su redacción de negocio y filtros; al
aprobar una regla y rechazar otra, sus estados cambian y se conservan al recargar la página; el
botón de exportar descarga un JSON con el formato de [contracts/catalogo-json.md](contracts/catalogo-json.md).

## Escenario 4: verificación diferencial (Historia 3)

```bash
python -m ghostmind verificar --ejecucion 1 --objetivo legacy
python -m ghostmind verificar --ejecucion 1 --objetivo modernizado
```

Resultado esperado: contra el mismo legacy, cero diferencias; contra el modernizado, diferencias
agrupadas por regla descubierta. El reporte también aparece en la pestaña de verificación del
catálogo.

## Escenario 5: evaluación del experimento (Historia 4)

```bash
python -m evaluacion.experimento
```

Resultado esperado: se crean `resultados/metricas.json`, `resultados/metricas.md`,
`resultados/robustez.json`, `resultados/robustez.md` y `resultados/catalogo_semilla42.json` con
C1, C2, C3, C5 y las consultas. Al repetir la orden, las métricas son idénticas (salvo fechas y
tiempos).

```bash
python -m evaluacion.capturas
```

Resultado esperado: imágenes del catálogo y del verificador en `resultados/capturas/`.

## Escenario 6: instrumento de C4

Abrir `evaluacion/instrumento_c4/cuestionario.md`, aplicarlo a los participantes, registrar sus
respuestas en una copia de `plantilla_respuestas.csv` y ejecutar:

```bash
python -m evaluacion.instrumento_c4.puntuar respuestas.csv
```

Resultado esperado: porcentaje de respuestas correctas y calificación promedio de utilidad.
