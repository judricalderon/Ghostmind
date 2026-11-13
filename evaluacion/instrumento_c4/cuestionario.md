# Cuestionario de utilidad del catálogo de GhostMind IA (criterio C4)

## Instrucciones para quien aplica el cuestionario

1. Participan entre 5 y 8 profesionales de software o especialistas del negocio que no hayan visto el código del sistema legacy ni las reglas verdaderas.
2. Cada participante abre el catálogo (`streamlit run app/catalogo.py`) con la ejecución de la semilla 42 y tiene 20 minutos para responder usando solo el catálogo.
3. Las respuestas se anotan en una copia de `plantilla_respuestas.csv` (una fila por participante) y se califican con `python -m evaluacion.instrumento_c4.puntuar respuestas.csv`.
4. Meta de C4, fijada antes de la prueba: al menos dos de cada tres respuestas correctas en total y una utilidad promedio (U1) de 4 o más sobre 5.

## Preguntas sobre el comportamiento del sistema

Para cada solicitud, indique qué decide el sistema: **A** Aprobado, **B** Rechazado, **C** Revisión manual.

**P1.** Solicitud con edad: 35 años; ingreso mensual: 3.000.000 pesos; monto solicitado: 20.000.000 pesos; plazo: 36 meses; puntaje de crédito: 380 puntos; antigüedad como cliente: 50 meses; tipo de empleo: empleado; código de convenio: ninguno.

Respuesta: A / B / C

**P2.** Solicitud con edad: 19 años; ingreso mensual: 3.000.000 pesos; monto solicitado: 20.000.000 pesos; plazo: 36 meses; puntaje de crédito: 300 puntos; antigüedad como cliente: 50 meses; tipo de empleo: empleado; código de convenio: C-77.

Respuesta: A / B / C

**P3.** Solicitud con edad: 35 años; ingreso mensual: 3.000.000 pesos; monto solicitado: 20.000.000 pesos; plazo: 36 meses; puntaje de crédito: 700 puntos; antigüedad como cliente: 150 meses; tipo de empleo: desempleado; código de convenio: ninguno.

Respuesta: A / B / C

**P4.** Solicitud con edad: 35 años; ingreso mensual: 1.200.000 pesos; monto solicitado: 20.000.000 pesos; plazo: 36 meses; puntaje de crédito: 700 puntos; antigüedad como cliente: 50 meses; tipo de empleo: empleado; código de convenio: C-12.

Respuesta: A / B / C

**P5.** Solicitud con edad: 35 años; ingreso mensual: 3.000.000 pesos; monto solicitado: 95.000.000 pesos; plazo: 36 meses; puntaje de crédito: 820 puntos; antigüedad como cliente: 72 meses; tipo de empleo: empleado; código de convenio: ninguno.

Respuesta: A / B / C

**P6.** Solicitud con edad: 35 años; ingreso mensual: 3.000.000 pesos; monto solicitado: 95.000.000 pesos; plazo: 36 meses; puntaje de crédito: 820 puntos; antigüedad como cliente: 30 meses; tipo de empleo: empleado; código de convenio: ninguno.

Respuesta: A / B / C

**P7.** Solicitud con edad: 35 años; ingreso mensual: 3.000.000 pesos; monto solicitado: 20.000.000 pesos; plazo: 36 meses; puntaje de crédito: 480 puntos; antigüedad como cliente: 50 meses; tipo de empleo: empleado; código de convenio: ninguno.

Respuesta: A / B / C

**P8.** Solicitud con edad: 35 años; ingreso mensual: 3.000.000 pesos; monto solicitado: 49.000.000 pesos; plazo: 36 meses; puntaje de crédito: 700 puntos; antigüedad como cliente: 50 meses; tipo de empleo: independiente; código de convenio: C-45.

Respuesta: A / B / C

**P9.** ¿El plazo del crédito cambia, por sí solo, la decisión del sistema en algún caso?

Respuesta: Sí / No

**P10.** Solicitud con edad: 20 años; ingreso mensual: 3.000.000 pesos; monto solicitado: 20.000.000 pesos; plazo: 36 meses; puntaje de crédito: 700 puntos; antigüedad como cliente: 50 meses; tipo de empleo: empleado; código de convenio: ninguno.

Respuesta: A / B / C

## Valoración del catálogo

Califique de 1 (nada) a 5 (totalmente).

**U1.** ¿Qué tan útil le resultó el catálogo para entender el comportamiento del sistema? (1 a 5)

**U2.** ¿Qué tan clara le resultó la redacción de las reglas? (1 a 5)

**U3.** ¿Qué tanto le ayudó la evidencia (casos y nivel de confianza) a decidir si una regla es correcta? (1 a 5)

**Comentario.** ¿Qué cambiaría del catálogo para que le sirviera más?
