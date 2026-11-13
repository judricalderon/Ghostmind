# Especificación: MVP de GhostMind IA para descubrir reglas de un sistema legacy

**Rama**: `main` (Spec Kit sin extensión de git; carpeta `specs/001-ghostmind-mvp`)

**Creada**: 2026-11-12

**Estado**: Borrador para revisión del usuario

**Entrada**: diseño del MVP descrito en las secciones 3 y 4 del informe final: un legacy simulado
de aprobación de créditos con 10 reglas plantadas; GhostMind lo explora como caja negra, extrae
reglas con evidencia y confianza para que un especialista las valide, y verifica una versión
modernizada. El éxito se mide con los criterios C1 a C5 fijados antes de las pruebas.

## Escenarios de usuario y pruebas *(obligatorio)*

### Historia de usuario 1: Descubrir las reglas de un sistema legacy observándolo (Prioridad: P1)

Un analista del área de modernización necesita saber qué reglas de negocio aplica un módulo legacy
de aprobación de créditos que nadie documentó. Solo tiene el diccionario de campos de entrada
(nombres, tipos y rangos) y la posibilidad de enviarle solicitudes. Ejecuta GhostMind con una
semilla y un presupuesto de consultas; GhostMind prueba entradas, observa las decisiones y entrega
un conjunto de reglas legibles, cada una con la evidencia que la sustenta, su nivel de confianza y
su estado.

**Por qué esta prioridad**: es la hipótesis central del proyecto (H1). Si las reglas no pueden
recuperarse observando el comportamiento, el resto del producto no tiene sentido.

**Prueba independiente**: se ejecuta el descubrimiento contra el legacy simulado y se revisa que
produzca reglas con evidencia, confianza y estado, y que cuente las consultas. Por sí sola ya
entrega valor: un inventario de reglas que antes no existía.

**Escenarios de aceptación**:

1. **Dado** el legacy simulado accesible solo por medio del adaptador y el diccionario de campos,
   **cuando** el analista ejecuta el descubrimiento con una semilla y un presupuesto,
   **entonces** GhostMind entrega reglas con condiciones legibles, decisión, casos que la
   respaldan, contraejemplos, nivel de confianza y estado (`hipótesis` o `corroborada`), junto con
   el número de consultas usadas y el motivo de parada.
2. **Dada** una regla con una condición numérica, **cuando** termina el descubrimiento,
   **entonces** el umbral reportado indica si quedó confirmado por bisección (dos valores enteros
   consecutivos con decisiones distintas, variando solo ese campo).
3. **Dadas** dos ejecuciones con la misma semilla y el mismo presupuesto, **cuando** terminan,
   **entonces** producen las mismas consultas, las mismas reglas y el mismo conteo.
4. **Dado** un presupuesto que se agota antes de que las reglas se estabilicen, **cuando** se
   alcanza el límite, **entonces** el descubrimiento se detiene, entrega las reglas que tiene y
   reporta "presupuesto agotado" como motivo.
5. **Dada** cualquier consulta hecha al legacy, **cuando** se revisa el registro de evidencia,
   **entonces** aparece con su entrada, su decisión, la ronda y el origen del caso.

---

### Historia de usuario 2: Revisar y validar las reglas en un catálogo (Prioridad: P2)

Un especialista del negocio revisa las reglas descubiertas en un catálogo. Para cada regla lee una
redacción en lenguaje de negocio, ve la decisión, el nivel de confianza, el estado y los casos que
la respaldan o la contradicen. Decide si la aprueba (validada) o la rechaza, con una nota opcional,
y exporta el catálogo para usarlo como base del sistema nuevo.

**Por qué esta prioridad**: corresponde a la hipótesis H2 (un catálogo con evidencia y confianza
ayuda a entender el sistema) y al principio de humano en el ciclo.

**Prueba independiente**: con una ejecución de descubrimiento ya guardada, se abre el catálogo, se
aprueba una regla, se rechaza otra, se cierra y se vuelve a abrir, y se exporta el resultado.

**Escenarios de aceptación**:

1. **Dada** una ejecución de descubrimiento guardada, **cuando** el especialista abre el catálogo,
   **entonces** ve todas las reglas con redacción de negocio, decisión, confianza, estado y número
   de casos de respaldo y contraejemplos, y puede filtrarlas por decisión, estado y confianza.
2. **Dada** una regla, **cuando** el especialista abre su detalle, **entonces** ve las condiciones
   exactas, los umbrales confirmados y una muestra de los casos que la respaldan y la contradicen.
3. **Dada** una regla en `hipótesis` o `corroborada`, **cuando** el especialista la aprueba o la
   rechaza, **entonces** su estado pasa a `validada` o `rechazada` con fecha y nota, y se conserva
   al volver a abrir el catálogo.
4. **Dado** el catálogo revisado, **cuando** el especialista lo exporta, **entonces** obtiene un
   archivo JSON con las reglas, sus condiciones, decisión, confianza, estado, evidencia resumida y
   decisiones del especialista.
5. **Dado** que el asistente de redacción está desactivado (valor por defecto) o no hay llave
   configurada, **cuando** se muestra una regla, **entonces** aparece la redacción por plantilla y
   el catálogo funciona sin conexión.

---

### Historia de usuario 3: Verificar una versión modernizada contra el legacy (Prioridad: P3)

El analista recibe una versión modernizada del módulo y quiere saber si conserva las reglas del
original. GhostMind vuelve a ejecutar sobre la versión modernizada los casos registrados durante el
descubrimiento, compara las decisiones y reporta las diferencias agrupadas por regla descubierta.

**Por qué esta prioridad**: corresponde a la hipótesis H3 (los casos generados sirven para
verificar una modernización) y cierra el ciclo propuesto en el informe.

**Prueba independiente**: se ejecuta la verificación contra una copia idéntica del legacy (cero
diferencias) y contra la versión modernizada con alteraciones (diferencias en las reglas
alteradas).

**Escenarios de aceptación**:

1. **Dados** los casos registrados de una ejecución y una versión modernizada, **cuando** el
   analista ejecuta la verificación, **entonces** cada caso registrado se ejecuta sobre la versión
   modernizada y se reportan las diferencias por regla descubierta, con conteos y casos de ejemplo.
2. **Dada** una versión idéntica al legacy, **cuando** se verifica, **entonces** el reporte indica
   cero diferencias.
3. **Dada** una verificación, **cuando** termina, **entonces** sus consultas se cuentan aparte de
   las del descubrimiento y el reporte puede verse en la misma interfaz del catálogo.

---

### Historia de usuario 4: Evaluar el experimento con los criterios fijados (Prioridad: P4)

El equipo del proyecto, o un evaluador externo, ejecuta la evaluación para medir los criterios C1,
C2, C3 y C5 y el número de consultas, y deja preparado el instrumento para medir C4 con
especialistas. Los resultados quedan en `resultados/` en JSON y en markdown, generados por una
ejecución real.

**Por qué esta prioridad**: produce la evidencia que el informe necesita; depende de las tres
historias anteriores.

**Prueba independiente**: se ejecuta la evaluación de punta a punta y se revisa que los archivos de
`resultados/` coincidan con lo que imprime la ejecución y que se puedan regenerar con la misma
semilla.

**Escenarios de aceptación**:

1. **Dada** una ejecución de descubrimiento, **cuando** se corre la evaluación, **entonces** se
   calculan C1, C2, C3 y C5 según las definiciones de esta especificación y se guardan con la
   semilla, el presupuesto, la fecha y las versiones usadas.
2. **Dado** el criterio C3, **cuando** se mide, **entonces** se usan 10.000 casos nuevos generados
   con una semilla distinta, que no se usaron en el descubrimiento.
3. **Dado** el criterio C4, **cuando** se prepara el instrumento, **entonces** quedan el
   cuestionario, la clave de respuestas, la plantilla de respuestas y el cálculo del puntaje, sin
   respuestas inventadas.
4. **Dadas** las reglas verdaderas, **cuando** se revisa el código, **entonces** solo el módulo de
   evaluación las lee.

---

### Casos límite

- La regla rara nunca aparece en las consultas: GhostMind no la reporta y la evaluación la marca
  como no recuperada; el resultado se publica tal cual, como límite del método.
- El legacy devuelve un valor fuera de las tres decisiones o falla: el adaptador registra el error,
  el caso no se usa para inducir reglas y, si los errores superan el 1 % de las consultas, el
  descubrimiento se detiene con un mensaje claro.
- Una solicitud con valores fuera del diccionario: el adaptador la rechaza sin consultar al legacy y
  no la cuenta como consulta.
- El presupuesto es menor que el muestreo inicial: se informa el error antes de consultar.
- Una condición sobre un campo entero: el umbral se presenta como entero con su sentido explícito
  (por ejemplo, "puntaje de crédito de 399 o menos").
- El catálogo se abre sin ejecuciones guardadas: muestra cómo ejecutar el descubrimiento.
- El especialista valida una regla que en realidad es incorrecta: el sistema lo permite; la
  evaluación es independiente de las decisiones del especialista.
- El asistente de redacción está activado pero falla la conexión o falta la llave: se usa la
  redacción por plantilla y se avisa en pantalla.
- La verificación encuentra diferencias en casos que no caen en ninguna regla reportada (no debería
  pasar, porque las reglas cubren todo el espacio): se agrupan como "sin regla asociada".

## Requisitos *(obligatorio)*

### Requisitos funcionales

**Escenario controlado**

- **FR-001**: Debe existir un módulo legacy simulado de aprobación de créditos que reciba 8 datos
  de una solicitud (edad, ingreso mensual, monto, plazo, puntaje de crédito, antigüedad como
  cliente, tipo de empleo y código de convenio) y devuelva solo una de tres decisiones:
  `APROBADO`, `RECHAZADO` o `REVISION_MANUAL`, sin motivo. Su código debe tener estilo antiguo:
  condicionales anidados, nombres crípticos y números fijos en el código.
- **FR-002**: El legacy debe implementar exactamente 10 reglas plantadas con precedencia, más un
  comportamiento por defecto. Entre ellas: una regla fósil (el convenio C-77 siempre aprueba), al
  menos tres excepciones a otras reglas y una excepción muy poco frecuente que afecte a menos del
  0,1 % de las solicitudes posibles bajo distribución uniforme.
- **FR-003**: Las reglas plantadas deben quedar descritas en un archivo separado, legible por
  máquina, que solo usa la evaluación. Una prueba automática debe comprobar que ese archivo y el
  legacy deciden igual en al menos 50.000 solicitudes y en todos los valores límite.
- **FR-004**: Debe existir un diccionario de campos con nombre, tipo, rango o valores permitidos de
  cada entrada y las decisiones posibles. Es el único conocimiento previo de GhostMind.

**Descubrimiento**

- **FR-005**: El adaptador debe ser el único punto de contacto con el sistema: valida la solicitud
  contra el diccionario, la envía, recibe la decisión, la registra y cuenta la consulta.
- **FR-006**: El muestreo inicial debe combinar valores aleatorios, valores límite de cada campo
  numérico y todas las categorías de cada campo categórico.
- **FR-007**: Después del muestreo inicial, GhostMind debe repetir rondas en las que induce reglas
  con un modelo interpretable y genera casos dirigidos: varía un campo a la vez y divide el
  intervalo por mitades hasta hallar el valor exacto donde cambia la decisión, y busca
  contraejemplos dentro de la región de cada regla.
- **FR-008**: El ciclo debe detenerse cuando una ronda completa no encuentra contraejemplos ni
  nuevos puntos de cambio (reglas estables), cuando se agota el presupuesto de consultas o cuando
  se alcanza el número máximo de rondas, y debe reportar cuál fue el motivo.
- **FR-009**: Cada regla debe tener condiciones legibles, decisión, número de casos que la
  respaldan, número de contraejemplos, nivel de confianza entre 0 % y 100 %, estado, umbrales
  confirmados y vínculo con los casos del registro.
- **FR-010**: La confianza debe calcularse a partir de los casos que respaldan la regla y de sus
  contraejemplos: crece con el respaldo y baja con cada contraejemplo. La fórmula queda
  documentada en el plan.
- **FR-011**: Toda regla nace como `hipótesis`; pasa a `corroborada` de forma automática cuando
  cumple los requisitos del plan (respaldo mínimo y ningún contraejemplo tras la búsqueda dirigida).
  Solo un especialista puede marcarla `validada` o `rechazada`.
- **FR-012**: El descubrimiento debe ser determinista dada su semilla.
- **FR-013**: El registro de evidencia debe guardarse en un único archivo local persistente con
  todas las consultas de cada ejecución, su ronda y su origen.

**Catálogo**

- **FR-014**: El catálogo debe listar las reglas de una ejecución con redacción de negocio,
  decisión, confianza, estado y evidencia resumida, con filtros por decisión, estado y confianza.
- **FR-015**: El detalle de una regla debe mostrar sus condiciones exactas, los umbrales
  confirmados y una muestra de los casos de respaldo y de los contraejemplos.
- **FR-016**: El especialista debe poder aprobar o rechazar cada regla con una nota opcional; la
  decisión se guarda con fecha y persiste.
- **FR-017**: El catálogo debe exportarse a JSON.
- **FR-018**: Puede usarse un modelo de lenguaje externo solo para redactar reglas en lenguaje de
  negocio. Está desactivado por defecto, toma la llave de una variable de entorno, nunca cambia
  condiciones ni decisiones y, si no está disponible, se usa la redacción por plantilla.

**Verificación diferencial**

- **FR-019**: El verificador debe ejecutar todos los casos registrados de una ejecución sobre otra
  versión del sistema y reportar las diferencias agrupadas por regla descubierta, con conteos y
  casos de ejemplo.
- **FR-020**: Debe existir una versión modernizada del legacy con exactamente tres reglas
  alteradas a propósito, descritas en un archivo que solo usa la evaluación.
- **FR-021**: El reporte de verificación debe poder consultarse en la interfaz del catálogo.

**Evaluación del experimento**

- **FR-022**: La evaluación debe calcular C1, C2, C3 y C5 y el número de consultas según las
  definiciones de esta especificación, y guardar los resultados en `resultados/` en JSON y en
  markdown con la semilla, el presupuesto, la fecha y las versiones usadas.
- **FR-023**: Para C3 deben generarse 10.000 solicitudes nuevas, uniformes sobre el diccionario,
  con una semilla distinta a la del descubrimiento; la evaluación reporta cuántas coinciden por
  azar con casos del registro.
- **FR-024**: Debe quedar listo el instrumento para C4: cuestionario para especialistas, clave de
  respuestas, plantilla para registrar respuestas y cálculo del puntaje, sin datos inventados.
- **FR-025**: La evaluación debe repetirse con cinco semillas adicionales y reportar el resultado de
  cada una y su resumen (mínimo y promedio), como información de robustez.
- **FR-026**: Deben generarse capturas del catálogo a partir de una ejecución real para el informe.
- **FR-027**: El README debe explicar cómo instalar y ejecutar cada parte y ofrecer una alternativa
  de demostración (capturas y guion de video).

**Selección de la caja negra (agregado el 2026-11-13, Fase 8)**

- **FR-028**: El catálogo debe permitir elegir la caja negra entre los sistemas registrados, con su
  descripción y los campos que GhostMind conoce de ella, fijar la semilla y el presupuesto, y lanzar
  un descubrimiento. Al terminar, el catálogo abre la ejecución nueva. Debe funcionar también cuando
  todavía no hay ejecuciones.
- **FR-029**: La línea de comandos debe listar las cajas negras disponibles con su descripción.

### Entidades clave

- **Diccionario de campos**: nombre, tipo (entero o categórico), rango o valores permitidos de cada
  entrada, y decisiones posibles.
- **Solicitud**: un valor para cada uno de los 8 campos.
- **Consulta**: una solicitud enviada al sistema y la decisión recibida, con ejecución, ronda,
  origen del caso, sistema consultado y momento.
- **Ejecución**: un descubrimiento o una verificación con su semilla, presupuesto, número de
  consultas, rondas y motivo de parada.
- **Regla descubierta**: región del espacio de entradas (intervalo por cada campo numérico y
  conjunto de valores por cada campo categórico) y decisión; tiene casos de respaldo,
  contraejemplos, confianza, estado y umbrales confirmados.
- **Umbral confirmado**: campo, valor exacto donde cambia la decisión y los dos casos que lo
  demuestran.
- **Revisión del especialista**: regla, decisión (validada o rechazada), nota y fecha.
- **Reporte de verificación**: diferencias por regla descubierta entre dos versiones del sistema.
- **Regla plantada** *(solo evaluación)*: identificador, descripción, condiciones, decisión y
  precedencia.
- **Alteración** *(solo evaluación)*: regla plantada que se cambió en la versión modernizada y cómo.

## Criterios de éxito *(obligatorio)*

### Resultados medibles

Las metas se fijaron antes de ejecutar el experimento y se evalúan sobre la semilla principal.

- **SC-001 (C1, cobertura)**: GhostMind recupera al menos el 80 % de las 10 reglas plantadas.
- **SC-002 (C2, precisión)**: al menos el 90 % de las reglas que GhostMind reporta existen en el
  sistema.
- **SC-003 (C3, fidelidad)**: las reglas extraídas reproducen la decisión del legacy en al menos el
  95 % de 10.000 solicitudes nuevas.
- **SC-004 (C4, utilidad)**: con el catálogo, los especialistas responden bien al menos dos de cada
  tres preguntas sobre el comportamiento del sistema y califican su utilidad con un promedio de 4 o
  más sobre 5. Se mide con usuarios fuera de la ejecución automática.
- **SC-005 (C5, detección de cambios)**: la verificación detecta el 100 % de las reglas alteradas
  en la versión modernizada.
- **SC-006 (costo)**: cada ejecución reporta el número de consultas al sistema; no tiene meta,
  pero no puede superar el presupuesto configurado.
- **SC-007 (reproducibilidad)**: repetir la evaluación con la misma semilla produce exactamente
  las mismas métricas, y el descubrimiento completo termina en menos de 10 minutos en un
  computador personal.

### Definición de las métricas

- **Regla reportada**: cada regla del catálogo final de una ejecución, en cualquier estado, antes de
  la revisión humana.
- **Pureza de una regla reportada**: proporción de 2.000 solicitudes uniformes dentro de la región
  que describe la regla en las que el legacy toma la decisión que la regla afirma. La regla
  **existe** si su pureza es de al menos 95 %. Se asocia a la regla plantada (o al comportamiento
  por defecto) que produce la decisión en la mayoría de esas solicitudes.
- **Regla plantada recuperada**: (a) al menos una regla reportada que existe está asociada a ella,
  y (b) en 2.000 solicitudes uniformes de su región efectiva (donde ella es la regla que decide),
  las reglas de GhostMind predicen su decisión en al menos el 90 %.
- **C1** = reglas plantadas recuperadas / 10. El comportamiento por defecto no cuenta entre las 10.
- **C2** = reglas reportadas que existen / reglas reportadas. Una regla asociada al comportamiento
  por defecto cuenta como existente si cumple la pureza.
- **C3** = solicitudes nuevas en que la predicción de las reglas coincide con el legacy / 10.000.
- **C5** = reglas alteradas detectadas / reglas alteradas. Una alteración se detecta si el
  verificador reporta al menos una diferencia en un caso donde esa alteración cambia la decisión.
- **Consultas**: llamadas al legacy durante el descubrimiento. Las de verificación se reportan
  aparte. Las de la evaluación no se cuentan porque no hacen parte de GhostMind.
- **Semillas**: semilla principal 42; semillas de robustez 1, 2, 3, 4 y 5; semilla de los casos
  nuevos de C3: 20261112. Los muestreos de pureza y cobertura usan semillas fijas propias.

## Supuestos

- Los montos e ingresos son pesos colombianos enteros; todos los campos numéricos son enteros.
- No hay una distribución real de solicitudes; C3 y las métricas de pureza y cobertura usan
  distribución uniforme sobre el diccionario.
- Las reglas del legacy se expresan como condiciones sobre campos individuales (umbrales y
  categorías). Las reglas sobre combinaciones de campos, como la relación cuota/ingreso, quedan
  fuera de este MVP y se reportan como límite.
- El legacy es determinista y no guarda estado entre solicitudes.
- Presupuesto por defecto de 20.000 consultas y máximo de 15 rondas.
- El catálogo es una aplicación local para un usuario, sin autenticación.
- El modelo de lenguaje opcional se usa por medio de la API de un proveedor externo con llave en
  variable de entorno; ninguna métrica depende de él.
- C4 se mide con 5 a 8 profesionales de software o especialistas; el repositorio solo deja el
  instrumento y el cálculo.
