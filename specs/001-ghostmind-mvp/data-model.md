# Modelo de datos: MVP de GhostMind IA

Hay dos espacios de datos separados. El de GhostMind (diccionario, registro SQLite y catálogo) y el
de la evaluación (reglas verdaderas y alteraciones). GhostMind nunca lee el segundo.

## 1. Diccionario de campos (`sistemas/diccionario_credito.json`)

Lo único que GhostMind sabe del sistema. Formato en [contracts/diccionario.md](contracts/diccionario.md).

- `sistema`: nombre del sistema.
- `longitud_registro`: 35.
- `campos[]`: `nombre`, `etiqueta`, `tipo` (`entero` o `categorico`), `unidad`, `minimo` y
  `maximo` (enteros) o `valores[]` con `valor` y `codigo`; `inicio` y `longitud` dentro del
  registro.
- `decisiones[]`: `APROBADO`, `RECHAZADO`, `REVISION_MANUAL`.

Validaciones: los nombres son únicos; `minimo` ≤ `maximo`; los campos no se traslapan en el
registro; cada código cabe en su longitud.

## 2. Registro de evidencia (SQLite, `datos/ghostmind.sqlite`)

### `ejecuciones`

| Columna | Tipo | Regla |
|---------|------|-------|
| `id` | INTEGER PK | autoincremental |
| `tipo` | TEXT | `descubrimiento` o `verificacion` |
| `objetivo` | TEXT | nombre del sistema consultado (`legacy`, `modernizado`, ...) |
| `ejecucion_base_id` | INTEGER NULL | en una verificación, el descubrimiento cuyos casos se repiten |
| `semilla` | INTEGER | obligatoria en descubrimiento |
| `presupuesto` | INTEGER | > 0 |
| `parametros` | TEXT (JSON) | parámetros efectivos de D5 a D8 |
| `version` | TEXT | versión de GhostMind |
| `inicio`, `fin` | TEXT | fecha y hora ISO 8601 |
| `consultas` | INTEGER | consultas al sistema hechas por esta ejecución |
| `rondas` | INTEGER | rondas completadas |
| `motivo_parada` | TEXT | `estable`, `presupuesto_agotado`, `max_rondas`, `errores` o `completa` |

### `casos`

Una fila por consulta, escrita antes de devolver la decisión al explorador.

| Columna | Tipo | Regla |
|---------|------|-------|
| `id` | INTEGER PK | |
| `ejecucion_id` | INTEGER FK | |
| `n_consulta` | INTEGER | 1, 2, 3, ... dentro de la ejecución |
| `ronda` | INTEGER | 0 para el muestreo inicial |
| `origen` | TEXT | `aleatorio`, `limite`, `categoria`, `biseccion`, `contraejemplo`, `exploracion_local`, `verificacion` |
| 8 columnas de campos | INTEGER o TEXT | valores dentro del diccionario |
| `decision` | TEXT NULL | una de las 3 decisiones; NULL si hubo error |
| `error` | TEXT NULL | mensaje si el sistema falló o devolvió algo inesperado |
| `caso_base_id` | INTEGER NULL | en verificación, el caso original repetido |
| `momento` | TEXT | ISO 8601 |

Índices: (`ejecucion_id`, `ronda`), (`ejecucion_id`, `origen`).

### `umbrales`

| Columna | Tipo | Regla |
|---------|------|-------|
| `id` | INTEGER PK | |
| `ejecucion_id` | INTEGER FK | |
| `campo` | TEXT | campo numérico del diccionario |
| `valor_cambio` | INTEGER | primer valor con la nueva decisión (`c`) |
| `caso_bajo_id`, `caso_alto_id` | INTEGER FK | casos con valores `c - 1` y `c`, iguales en todo lo demás |
| `decision_baja`, `decision_alta` | TEXT | deben ser distintas |
| `ronda` | INTEGER | |

### `rondas`

| Columna | Tipo |
|---------|------|
| `ejecucion_id`, `ronda` | INTEGER (PK compuesta) |
| `consultas_acumuladas`, `reglas`, `contradicciones`, `umbrales_nuevos` | INTEGER |

Sirve para mostrar cómo convergió el descubrimiento.

### `reglas`

| Columna | Tipo | Regla |
|---------|------|-------|
| `id` | INTEGER PK | |
| `ejecucion_id` | INTEGER FK | |
| `codigo` | TEXT | `GM-01`, `GM-02`, ... en orden de respaldo descendente |
| `condiciones` | TEXT (JSON) | caja de la regla (ver abajo) |
| `decision` | TEXT | una de las 3 decisiones |
| `respaldo`, `contraejemplos` | INTEGER | ≥ 0 |
| `consultas_prueba` | INTEGER | consultas de búsqueda de contraejemplos dentro de la caja (D8) |
| `umbrales_confirmados` | TEXT (JSON) | lista de `{campo, valor_cambio}` de los bordes de la caja confirmados por bisección |
| `confianza` | REAL | 0 a 1, límite inferior de Wilson al 95 % |
| `estado` | TEXT | `hipotesis`, `corroborada`, `validada` o `rechazada` |
| `texto_tecnico`, `texto_negocio` | TEXT | redacción por plantilla |
| `texto_llm` | TEXT NULL | redacción opcional del modelo de lenguaje |

Formato de `condiciones` (solo aparecen los campos que restringen algo):

```json
{
  "puntaje_credito": {"min": 150, "max": 399},
  "edad": {"min": 21, "max": 80},
  "codigo_convenio": {"valores": ["NINGUNO", "C-12", "C-31", "C-45"]}
}
```

Transiciones de estado:

```text
hipotesis   -> corroborada   (automática, al cerrar el descubrimiento, D8)
hipotesis   -> validada | rechazada   (especialista)
corroborada -> validada | rechazada   (especialista)
validada    <-> rechazada             (el especialista puede cambiar de opinión; queda en el historial)
```

### `regla_casos`

| Columna | Tipo | Regla |
|---------|------|-------|
| `regla_id`, `caso_id` | INTEGER (PK compuesta) | |
| `tipo` | TEXT | `respaldo` o `contraejemplo` |

### `revisiones`

| Columna | Tipo | Regla |
|---------|------|-------|
| `id` | INTEGER PK | |
| `regla_id` | INTEGER FK | |
| `decision` | TEXT | `validada` o `rechazada` |
| `nota` | TEXT NULL | |
| `momento` | TEXT | ISO 8601 |

### `diferencias`

| Columna | Tipo | Regla |
|---------|------|-------|
| `ejecucion_id` | INTEGER FK | la verificación |
| `caso_base_id` | INTEGER FK | caso original del descubrimiento |
| `caso_nuevo_id` | INTEGER FK | consulta a la otra versión |
| `regla_id` | INTEGER NULL | regla descubierta cuya caja contiene el caso |
| `decision_original`, `decision_nueva` | TEXT | distintas |

## 3. Catálogo exportado (JSON)

Formato en [contracts/catalogo-json.md](contracts/catalogo-json.md): metadatos de la ejecución y
la lista de reglas con condiciones, decisión, evidencia resumida, confianza, estado, redacciones y
revisiones.

## 4. Datos de la evaluación (`evaluacion/`, fuera de GhostMind)

### `reglas_verdaderas.json`

- `version`, `decision_por_defecto` (`APROBADO`).
- `reglas[]` en orden de precedencia: `id` (R01 a R10), `tipo` (`fosil`, `general`, `excepcion`,
  `excepcion_rara`), `descripcion`, `condiciones` (mismo formato de caja que las reglas de
  GhostMind) y `decision`.

### `alteraciones.json`

- `alteraciones[]`: `id` (A1 a A3), `regla` (R01, R04, R05), `tipo` (`eliminar` o
  `cambiar_condicion`), `nueva_condicion` cuando aplica y `descripcion`.

### Resultados (`resultados/`)

- `metricas.json`: semilla, presupuesto, fecha, versiones, C1, C2, C3 y C5 con su detalle por regla,
  consultas de descubrimiento y de verificación, y tiempo de ejecución.
- `metricas.md`: las mismas cifras en tablas legibles.
- `robustez.json` y `robustez.md`: resultados de las semillas 1 a 5 con mínimo y promedio.
- `catalogo_semilla42.json`: catálogo exportado de la ejecución principal.
- `capturas/`: imágenes del catálogo y del verificador.
