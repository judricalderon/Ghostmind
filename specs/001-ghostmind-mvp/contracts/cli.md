# Contrato: órdenes de línea de comandos

Todas se ejecutan desde la raíz del repositorio con el entorno virtual activo. La base de datos por
defecto es `datos/ghostmind.sqlite` y se cambia con `--db`.

## GhostMind

```bash
python -m ghostmind descubrir --objetivo legacy --semilla 42 --presupuesto 20000
```

Imprime el id de la ejecución, las rondas, las consultas, el motivo de parada y la tabla de
reglas. Código de salida 0 si termina (aunque sea por presupuesto); 2 si los parámetros son
inválidos; 3 si se detiene por errores del sistema.

```bash
python -m ghostmind verificar --ejecucion 1 --objetivo modernizado
```

Repite los casos de la ejecución 1 sobre el objetivo y muestra las diferencias por regla.

```bash
python -m ghostmind exportar --ejecucion 1 --salida catalogo.json
```

Escribe el catálogo en JSON ([catalogo-json.md](catalogo-json.md)).

```bash
python -m ghostmind reglas --ejecucion 1
```

Lista las reglas de una ejecución en la terminal.

```bash
python -m ghostmind muestrear --objetivo legacy --semilla 42
```

Orden de diagnóstico de la Fase 3: crea una ejecución y corre solo el muestreo inicial.

## Catálogo

```bash
streamlit run app/catalogo.py
```

Abre el catálogo y el reporte de verificación en el navegador. Variables opcionales:
`GHOSTMIND_DB` (ruta de la base), `GHOSTMIND_LLM=1` y `ANTHROPIC_API_KEY` (redacción opcional).

## Evaluación (fuera de GhostMind)

```bash
python -m evaluacion.experimento
```

Ejecuta el descubrimiento con la semilla 42, la verificación contra el modernizado, calcula C1, C2,
C3 y C5, repite con las semillas 1 a 5 y escribe `resultados/`.

```bash
python -m evaluacion.capturas
```

Levanta el catálogo con la ejecución principal y guarda capturas en `resultados/capturas/`.

```bash
python -m evaluacion.instrumento_c4.puntuar respuestas.csv
```

Calcula el porcentaje de respuestas correctas y la calificación promedio de C4.
