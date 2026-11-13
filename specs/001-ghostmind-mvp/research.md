# Investigación y decisiones de diseño: MVP de GhostMind IA

Cada decisión tiene la forma Decisión, Razón y Alternativas consideradas. Las decisiones D3, D4 y
D11 fijan el diseño del experimento; por el principio III de la constitución no se cambian después
de ver resultados.

## D1. Plataforma y herramientas

- **Decisión**: Python 3.11, SQLite (módulo estándar `sqlite3`), pandas 3.1, scikit-learn 1.9,
  Streamlit 1.67, pytest 9.2. Modelo de lenguaje opcional: Claude por medio del SDK oficial de
  Anthropic, que se instala aparte y solo si se activa.
- **Razón**: son las herramientas declaradas en la Tabla 3 del informe; son gratuitas y funcionan
  en un computador personal sin servidor.
- **Alternativas**: DuckDB para el registro (innecesario para unas decenas de miles de filas);
  una interfaz en React (más trabajo sin beneficio para el experimento).

## D2. Interfaz del legacy: registro de ancho fijo

- **Decisión**: el legacy expone una sola función `CRDAPR01(WK_REG)` que recibe un registro de
  texto de ancho fijo (35 posiciones, al estilo de un copybook COBOL) y devuelve la decisión como
  texto. El diccionario de campos que recibe GhostMind incluye la posición y longitud de cada campo
  y el código de cada categoría, igual que un documento de interfaz real. El adaptador arma el
  registro a partir de la solicitud.
- **Razón**: refleja cómo se integra un sistema legacy (se conoce su interfaz, no su lógica) y da
  al adaptador un trabajo real. La versión modernizada conserva el mismo contrato, así que el
  verificador usa el mismo adaptador.
- **Alternativas**: llamar una función de Python con argumentos con nombre (menos realista y
  facilita que el código de GhostMind dependa del legacy).

## D3. Diccionario de campos

| Campo | Tipo | Rango o valores | Posición en el registro |
|-------|------|-----------------|--------------------------|
| `edad` | entero (años) | 18 a 80 | 1 a 3 |
| `ingreso_mensual` | entero (pesos) | 0 a 20.000.000 | 4 a 12 |
| `monto` | entero (pesos) | 1.000.000 a 150.000.000 | 13 a 21 |
| `plazo_meses` | entero (meses) | 6 a 120 | 22 a 24 |
| `puntaje_credito` | entero (puntos) | 150 a 950 | 25 a 27 |
| `antiguedad_meses` | entero (meses) | 0 a 240 | 28 a 30 |
| `tipo_empleo` | categórico | EMPLEADO (E), INDEPENDIENTE (I), PENSIONADO (P), DESEMPLEADO (D) | 31 |
| `codigo_convenio` | categórico | NINGUNO (espacios), C-12, C-31, C-45, C-77 | 32 a 35 |

Decisiones posibles: `APROBADO`, `RECHAZADO`, `REVISION_MANUAL`.

## D4. Reglas plantadas (solo para el legacy y la evaluación)

Se evalúan en orden; decide la primera que se cumple. Si ninguna se cumple, la decisión es
`APROBADO` (comportamiento por defecto, que no cuenta entre las 10).

| Id | Tipo | Condición | Decisión | Fracción efectiva (uniforme) |
|----|------|-----------|----------|------------------------------|
| R01 | Fósil | `codigo_convenio` = C-77 | APROBADO | 19,9 % |
| R02 | General | `edad` < 21 | RECHAZADO | 3,8 % |
| R03 | Excepción rara | `tipo_empleo` = INDEPENDIENTE y `codigo_convenio` = C-45 y 48.000.000 ≤ `monto` ≤ 50.000.000 | REVISION_MANUAL | 0,066 % |
| R04 | General | `puntaje_credito` < 400 | RECHAZADO | 23,8 % |
| R05 | Excepción de R06 | `tipo_empleo` = DESEMPLEADO y `antiguedad_meses` ≥ 120 | REVISION_MANUAL | 6,6 % |
| R06 | General | `tipo_empleo` = DESEMPLEADO | RECHAZADO | 6,5 % |
| R07 | General con excepción | `ingreso_mensual` < 1.500.000 y `codigo_convenio` ≠ C-12 (la libranza C-12 queda exenta) | RECHAZADO | 2,2 % |
| R08 | Excepción de R09 | `monto` > 80.000.000 y `puntaje_credito` ≥ 800 y `antiguedad_meses` ≥ 60 | APROBADO | 3,6 % |
| R09 | General | `monto` > 80.000.000 | REVISION_MANUAL | 13,9 % |
| R10 | General | `puntaje_credito` < 550 | REVISION_MANUAL | 5,4 % |
| Defecto | | ninguna de las anteriores | APROBADO | 14,3 % |

Notas de diseño:

- Hay una regla fósil (R01), tres excepciones que producen su propia decisión (R03, R05 y R08) y
  una excepción incrustada en una condición (C-12 en R07).
- R03 es la excepción rara: afecta cerca del 0,066 % de las solicitudes posibles (menos del 0,1 %
  que exige FR-002). Se espera que GhostMind tenga dificultad para encontrarla.
- `plazo_meses` no participa en ninguna regla a propósito: permite ver si GhostMind inventa
  condiciones sobre un campo irrelevante.
- Las fracciones se estimaron con 2.000.000 de solicitudes uniformes (semilla 0) sobre esta tabla;
  la Fase 2 las vuelve a medir sobre el legacy implementado.

## D5. Muestreo inicial

- **Decisión**: 720 consultas: 400 solicitudes uniformes; 120 de valores límite (para cada uno de
  los 6 campos numéricos, su mínimo y su máximo sobre 10 solicitudes base aleatorias); y 200 de
  categorías (las 20 combinaciones de `tipo_empleo` y `codigo_convenio`, cada una con 10 valores
  numéricos aleatorios).
- **Razón**: cubre todo el espacio, todos los bordes y todas las categorías con un costo bajo
  frente al presupuesto de 20.000.
- **Alternativas**: diseño factorial completo (crece demasiado); hipercubo latino (mejor
  cobertura uniforme, pero no aporta bordes ni categorías por sí solo).

## D6. Inducción de reglas con árbol de decisión

- **Decisión**: `DecisionTreeClassifier(criterion="entropy", min_samples_leaf=3,
  random_state=semilla)`. Entradas: los 6 campos numéricos tal cual y los 2 categóricos en
  variables indicadoras (9 columnas). Cada hoja es una regla: una caja con un intervalo entero por
  campo numérico y un conjunto de valores por campo categórico. Los umbrales del árbol (puntos
  medios) se convierten a enteros: `x <= t` pasa a `x ≤ floor(t)` y `x > t` a `x ≥ floor(t) + 1`.
- **Razón**: es interpretable y reproducible, y cada condición se rastrea hasta casos concretos.
  `min_samples_leaf=3` evita hojas de uno o dos casos; los casos que no alcanzan a separarse quedan
  como contraejemplos visibles de la regla en vez de convertirse en reglas sueltas.
- **Alternativas**: listas de decisión o RIPPER (no están en scikit-learn); árboles sin mínimo de
  casos por hoja (los contraejemplos desaparecen y aparecen reglas de un solo caso).

## D7. Exploración dirigida por rondas

En cada ronda, con el árbol vigente:

1. **Bisección de umbrales**: para cada división numérica del árbol (campo `f`, umbral `t`) que
   aún no esté confirmada, se toman hasta 3 pares de casos del nodo que caen a lados distintos y
   tienen decisiones distintas, empezando por los más cercanos a `t`. Con la base `a`, se consulta
   `a` cambiando solo `f` al valor de `b`. Si la decisión cambia, se divide el intervalo por mitades
   (valores enteros) hasta encontrar `c`, el primer valor con la nueva decisión. El umbral queda
   confirmado con los casos `c - 1` y `c`.
2. **Búsqueda de contraejemplos**: para cada hoja se consultan 25 solicitudes uniformes dentro de
   su caja y una solicitud en cada borde numérico de la caja (a lo sumo 12). Un contraejemplo es
   una respuesta distinta de la que predice la hoja.
3. **Exploración local**: para hasta 10 contraejemplos nuevos por ronda, se varía cada campo
   numérico desde el contraejemplo hacia los dos bordes de la hoja con bisección, y cada campo
   categórico a sus demás valores. Así se delimita la región desconocida.
4. **Parada**: si en la ronda ninguna consulta contradijo al árbol vigente y no apareció un umbral
   nuevo, las reglas son estables y el ciclo termina. También termina al agotar el presupuesto
   (20.000) o al llegar a 15 rondas. Las reglas finales son las hojas del último árbol probado.

- **Razón**: es la búsqueda dirigida que describe el informe en lugar del aprendizaje por refuerzo
  de BlackBoxToBlueprint; concentra consultas donde el comportamiento todavía no es claro.
- **Alternativas**: aprendizaje activo por incertidumbre del modelo (no aplica bien a un árbol
  puro); aprendizaje por refuerzo (más complejo de implementar y de explicar).

## D8. Evidencia, confianza y estados

- **Respaldo** de una regla: casos del registro dentro de su caja con su misma decisión.
  **Contraejemplos**: casos dentro de su caja con otra decisión.
- **Confianza**: límite inferior del intervalo de Wilson al 95 % para la proporción
  `respaldo / (respaldo + contraejemplos)`. Ejemplos: 10 casos sin contraejemplos dan 72 %; 30 dan
  89 %; 100 dan 96 %; 100 con 2 contraejemplos dan 93 %.
- **Estados**: `hipótesis` al nacer. `corroborada` si tiene al menos 30 casos de respaldo, ningún
  contraejemplo y recibió al menos 20 consultas de búsqueda de contraejemplos en la ronda final sin
  ser contradicha. `validada` y `rechazada` solo desde el catálogo.
- **Razón**: la confianza crece con el respaldo y baja con cada contraejemplo, como pide FR-010, y
  castiga las reglas con poca evidencia.
- **Alternativas**: proporción simple (da 100 % con un solo caso); Laplace (menos conservadora).

## D9. Redacción de las reglas

- **Decisión**: una redacción técnica (`SI ... ENTONCES ...`) y una redacción de negocio por
  plantilla, con etiquetas, unidades y separador de miles, por ejemplo: "Se rechaza la solicitud
  cuando el puntaje de crédito es de 399 o menos (convenio distinto de C-77; 21 años o más)".
  Se omiten las condiciones iguales a los límites del dominio. El modelo de lenguaje opcional
  reescribe solo el texto de negocio a partir de la regla estructurada; se activa con
  `GHOSTMIND_LLM=1` y la llave `ANTHROPIC_API_KEY`, y su salida se guarda junto a la redacción
  por plantilla. El modelo concreto se define en la Fase 5 según la referencia de la API.
- **Alternativas**: redactar todo con el modelo de lenguaje (rompe la reproducibilidad).

## D10. Verificador diferencial

- **Decisión**: el verificador lee los casos de una ejecución de descubrimiento, elimina entradas
  repetidas, los envía a otra versión por medio del mismo adaptador (ejecución de tipo
  `verificacion`), compara decisiones y agrupa las diferencias por la regla descubierta cuya caja
  contiene el caso.
- **Razón**: es lo que describe el informe (H3). Los pares de bisección (`c - 1`, `c`) hacen que
  cualquier corrimiento de un umbral confirmado cambie la decisión de al menos un caso registrado.

## D11. Versión modernizada y alteraciones (solo para la evaluación)

La versión modernizada reescribe la lógica en estilo actual (funciones con nombre, constantes
nombradas) y altera exactamente tres reglas, que representan errores típicos de modernización:

| Id | Regla | Alteración | Error que representa |
|----|-------|------------|----------------------|
| A1 | R01 | Se elimina la regla fósil: C-77 sigue el flujo normal | Se descarta una regla no documentada que parecía obsoleta |
| A2 | R04 | El umbral de rechazo pasa de 400 a 420 puntos | Un umbral mal transcrito |
| A3 | R05 | Se elimina la excepción: los desempleados con 120 meses o más se rechazan | Se pierde una excepción |

## D12. Cálculo de las métricas

- **Decisión**: la evaluación (`evaluacion/`) interpreta `reglas_verdaderas.json` y
  `alteraciones.json` con un evaluador propio y calcula las métricas como define la especificación:
  pureza y cobertura con 2.000 solicitudes uniformes por regla (semillas fijas derivadas de la
  semilla principal), C3 con 10.000 solicitudes de semilla 20261112, y C5 atribuyendo cada
  diferencia reportada a la alteración que, aplicada sola, cambia la decisión de ese caso.
- **Razón**: el muestreo da métricas exactas de calcular, reproducibles y fáciles de explicar sin
  comparar condiciones simbólicas.
- **Alternativas**: comparar condiciones de forma simbólica (frágil ante reglas fragmentadas).

## D13. Capturas para el informe

- **Decisión**: Playwright para Python con el canal `msedge` (usa el Edge instalado, sin descargar
  navegadores) para abrir el catálogo en Streamlit y guardar capturas en `resultados/capturas/`.
  Es una dependencia solo de la Fase 7 (`requirements-capturas.txt`).
- **Alternativas**: capturas manuales (no reproducibles); Edge sin interfaz con `--screenshot`
  (no espera a que Streamlit termine de cargar).

## D14. Entorno local y repositorio

- **Decisión**: dependencias fijadas en `requirements.txt`; la base SQLite se guarda en `datos/`
  (excluida de git) y se regenera con una orden. `resultados/` sí se versiona.
- **Razón**: el registro se regenera en minutos y es determinista; versionar resultados permite
  revisarlos sin ejecutar nada.
