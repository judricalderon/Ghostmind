# Guion de demostración en video (4 minutos aproximadamente)

Alternativa a la demostración en vivo. Cada escena indica qué se muestra en pantalla y qué se dice.
Antes de grabar, ejecutar `python -m evaluacion.experimento` y abrir el catálogo con la base del
experimento (ver README, sección "Demostración").

## Escena 1. El problema (0:00 a 0:30)

- **Pantalla**: el archivo `legacy/crdapr01.py` con sus condicionales anidados y variables `WS_A`, `WS_B`.
- **Narración**: "Este es un módulo legacy simulado de aprobación de créditos. Tiene diez reglas de negocio
  que nadie documentó. GhostMind no puede leer este código: solo conoce los nombres, tipos y rangos de los
  ocho campos de entrada, que están en `sistemas/diccionario_credito.json`."

## Escena 2. Descubrimiento por caja negra (0:30 a 1:15)

- **Pantalla**: terminal con `python -m ghostmind descubrir --objetivo legacy --semilla 42`.
- **Narración**: "GhostMind envía solicitudes al sistema por medio de un adaptador y registra cada respuesta.
  Primero hace un muestreo inicial; luego, en cada ronda, entrena un árbol de decisión, busca el valor exacto
  donde cambia la decisión dividiendo intervalos por mitades y busca contraejemplos. Se detuvo solo cuando
  las reglas dejaron de cambiar: cinco rondas y 5.559 consultas."

## Escena 3. Catálogo para el especialista (1:15 a 2:15)

- **Pantalla**: catálogo en el navegador (`resultados/capturas/01_catalogo_reglas.png` si es en imágenes).
- **Narración**: "Cada regla aparece en lenguaje de negocio, con su decisión, su nivel de confianza y su
  estado. Ninguna se acepta sola."
- **Pantalla**: detalle de una regla (captura 02), revisión (captura 03) y evidencia (captura 04).
- **Narración**: "Aquí están las condiciones exactas, los umbrales confirmados por bisección y los casos que
  la respaldan. El especialista la valida o la rechaza con una nota, y el catálogo se exporta en JSON."
- **Acción**: escribir una nota y pulsar "Validar regla".

## Escena 4. Cómo convergió (2:15 a 2:35)

- **Pantalla**: pestaña Convergencia (captura 05).
- **Narración**: "Las contradicciones bajan hasta cero en la última ronda; ahí el ciclo se detiene."

## Escena 5. Verificación de la versión modernizada (2:35 a 3:15)

- **Pantalla**: pestaña Verificación (captura 06) o `python -m ghostmind verificar --ejecucion 1 --objetivo modernizado`.
- **Narración**: "Un equipo modernizó el módulo y, sin saberlo, cambió tres reglas. GhostMind repite sobre la
  versión nueva los casos que ya registró y muestra en qué reglas cambian las decisiones. Las tres
  alteraciones quedan a la vista."

## Escena 6. Resultados y límites (3:15 a 4:00)

- **Pantalla**: `resultados/metricas.md`, tabla de criterios.
- **Narración**: "Los criterios se fijaron antes de las pruebas. GhostMind recuperó nueve de las diez reglas
  plantadas, todas las reglas que reportó existen, reproduce la decisión del sistema en el 99,9 % de 10.000
  casos nuevos y detectó las tres alteraciones. La regla que no encontró es la excepción muy poco frecuente
  que pusimos a propósito: afecta a menos del 0,1 % de las solicitudes. Ese es el límite del método y el
  punto de partida de la siguiente versión."

Las cifras de la narración corresponden a `resultados/metricas.md` de la semilla 42; si se vuelve a ejecutar
el experimento con otros parámetros, hay que leerlas de nuevo de ese archivo.
