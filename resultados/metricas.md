# Resultados del experimento de GhostMind IA

Generado por `python -m evaluacion.experimento` el 2026-11-12. Semilla principal 42; presupuesto de 20.000 consultas. Todas las cifras salen de esta ejecución y se repiten iguales al volver a ejecutar la orden (salvo fechas y tiempos).

## Criterios de éxito

| Criterio | Meta (fijada antes de las pruebas) | Resultado | ¿Cumple? |
|---|---|---|---|
| C1. Cobertura | Al menos 80 % de las 10 reglas plantadas | 90,0 % (9 de 10) | Sí |
| C2. Precisión | Al menos 90 % de las reglas reportadas existen | 100,0 % (24 de 24) | Sí |
| C3. Fidelidad | Al menos 95 % en 10.000 casos nuevos | 99,9 % (9.992 de 10.000) | Sí |
| C4. Utilidad para especialistas | 2 de cada 3 respuestas correctas y promedio de 4 o más | Pendiente: se mide con usuarios (evaluacion/instrumento_c4/) | Pendiente |
| C5. Detección de cambios | 100 % de las reglas alteradas | 100,0 % (3 de 3) | Sí |

## Costo en consultas

| Medida | Valor |
|---|---|
| Consultas al legacy en el descubrimiento | 5.559 de 20.000 |
| Rondas | 5 |
| Motivo de parada | estable |
| Tiempo del descubrimiento | 0,76 s |
| Consultas a la versión modernizada en la verificación | 5.559 |
| Reglas reportadas (corroboradas) | 24 (24) |

## C1. Recuperación de cada regla plantada

Una regla plantada se recupera si al menos una regla reportada que existe está asociada a ella y, en 2.000 solicitudes uniformes de su región efectiva, las reglas de GhostMind predicen su decisión en al menos 90,0 %.

| Regla | Tipo | Descripción | Reglas de GhostMind asociadas | Fidelidad local | Recuperada |
|---|---|---|---|---|---|
| R01 | Fósil | El convenio C-77 siempre aprueba (convenio antiguo que nunca se retiró). | GM-10, GM-24 | 100,0 % | Sí |
| R02 | General | Se rechazan los solicitantes menores de 21 años. | GM-01 | 100,0 % | Sí |
| R03 | Excepción rara | Los independientes del convenio C-45 que piden entre 48 y 50 millones van a revisión manual. | ninguna | 17,5 % | No |
| R04 | General | Se rechaza un puntaje de crédito menor que 400. | GM-07 | 100,0 % | Sí |
| R05 | Excepción | Excepción de R06: un desempleado con 120 meses o más de antigüedad va a revisión manual. | GM-02, GM-17 | 100,0 % | Sí |
| R06 | General | Se rechazan los desempleados. | GM-03, GM-09 | 100,0 % | Sí |
| R07 | General | Se rechaza un ingreso menor que 1.500.000, salvo con libranza C-12. | GM-04, GM-15, GM-18, GM-20 | 100,0 % | Sí |
| R08 | Excepción | Excepción de R09: los montos altos con puntaje de 800 o más y 60 meses o más de antigüedad se aprueban. | GM-16, GM-21 | 100,0 % | Sí |
| R09 | General | Los montos mayores que 80.000.000 van a revisión manual. | GM-08, GM-13, GM-14, GM-19 | 100,0 % | Sí |
| R10 | General | Un puntaje de crédito menor que 550 va a revisión manual. | GM-05, GM-11, GM-22, GM-23 | 100,0 % | Sí |

## C2. Precisión de cada regla reportada

Una regla reportada existe si en 2.000 solicitudes uniformes dentro de su región el legacy toma su decisión en al menos 95,0 % de los casos.

| Código | Decisión | Estado | Pureza | Existe | Asociada a |
|---|---|---|---|---|---|
| GM-01 | RECHAZADO | corroborada | 100,0 % | Sí | R02 |
| GM-02 | REVISION_MANUAL | corroborada | 100,0 % | Sí | R05 |
| GM-03 | RECHAZADO | corroborada | 100,0 % | Sí | R06 |
| GM-04 | RECHAZADO | corroborada | 100,0 % | Sí | R07 |
| GM-05 | REVISION_MANUAL | corroborada | 100,0 % | Sí | R10 |
| GM-06 | APROBADO | corroborada | 99,7 % | Sí | DEFECTO |
| GM-07 | RECHAZADO | corroborada | 100,0 % | Sí | R04 |
| GM-08 | REVISION_MANUAL | corroborada | 100,0 % | Sí | R09 |
| GM-09 | RECHAZADO | corroborada | 100,0 % | Sí | R06 |
| GM-10 | APROBADO | corroborada | 100,0 % | Sí | R01 |
| GM-11 | REVISION_MANUAL | corroborada | 100,0 % | Sí | R10 |
| GM-12 | APROBADO | corroborada | 100,0 % | Sí | DEFECTO |
| GM-13 | REVISION_MANUAL | corroborada | 100,0 % | Sí | R09 |
| GM-14 | REVISION_MANUAL | corroborada | 100,0 % | Sí | R09 |
| GM-15 | RECHAZADO | corroborada | 99,9 % | Sí | R07 |
| GM-16 | APROBADO | corroborada | 100,0 % | Sí | R08 |
| GM-17 | REVISION_MANUAL | corroborada | 100,0 % | Sí | R05 |
| GM-18 | RECHAZADO | corroborada | 100,0 % | Sí | R07 |
| GM-19 | REVISION_MANUAL | corroborada | 100,0 % | Sí | R09 |
| GM-20 | RECHAZADO | corroborada | 99,9 % | Sí | R07 |
| GM-21 | APROBADO | corroborada | 100,0 % | Sí | R08 |
| GM-22 | REVISION_MANUAL | corroborada | 100,0 % | Sí | R10 |
| GM-23 | REVISION_MANUAL | corroborada | 100,0 % | Sí | R10 |
| GM-24 | APROBADO | corroborada | 100,0 % | Sí | R01 |

## C3. Fidelidad en casos nuevos

10.000 solicitudes uniformes generadas con la semilla 20261112, distinta de la del descubrimiento. Coinciden 9.992. De esas solicitudes, 0 coinciden por azar con casos del registro.

## C5. Detección de las reglas alteradas

La verificación repitió 5.559 casos sobre la versión modernizada y encontró 1.124 diferencias en las reglas GM-02, GM-05, GM-10, GM-11, GM-17, GM-22, GM-23, GM-24. Una diferencia se atribuye a una alteración si esa alteración, aplicada sola, cambia la decisión del caso.

| Alteración | Regla | Descripción | Diferencias atribuidas | Detectada |
|---|---|---|---|---|
| A1 | R01 | Se elimina la regla fósil: el convenio C-77 sigue el flujo normal. | 245 | Sí |
| A2 | R04 | El umbral de rechazo por puntaje pasa de 400 a 420 puntos. | 159 | Sí |
| A3 | R05 | Se elimina la excepción: los desempleados con 120 meses o más de antigüedad se rechazan. | 754 | Sí |

## Umbrales confirmados por bisección

| Campo | Primer valor con la nueva decisión |
|---|---|
| Antigüedad como cliente | 60 |
| Antigüedad como cliente | 120 |
| Edad | 21 |
| Ingreso mensual | 1.500.000 |
| Monto solicitado | 80.000.001 |
| Puntaje de crédito | 400 |
| Puntaje de crédito | 550 |
| Puntaje de crédito | 800 |

## Configuración y versiones

| Parámetro | Valor |
|---|---|
| Semilla principal | 42 |
| Semillas de robustez | 1, 2, 3, 4, 5 |
| Presupuesto de consultas | 20.000 |
| Máximo de rondas | 15 |
| Solicitudes por regla (pureza y fidelidad local) | 2.000 |
| Casos nuevos para C3 (semilla) | 10.000 (20261112) |
| Umbral de pureza / de fidelidad local | 95,0 % / 90,0 % |
| Metas | C1 80,0 %, C2 90,0 %, C3 95,0 %, C5 100,0 % |
| Base de evidencia | datos/experimento.sqlite |
| Versión de GhostMind | 0.1.0 |
| Commit del código | 1ff8a45 |
| Python / numpy / pandas / scikit-learn / Streamlit | 3.11.9 / 2.4.6 / 3.1.1 / 1.9.1 / 1.67.0 |

La robustez con otras semillas está en `robustez.md`.
