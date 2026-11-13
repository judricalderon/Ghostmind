# Constitución del prototipo GhostMind IA

## Principios fundamentales

### I. Caja negra estricta

GhostMind conoce del sistema legacy únicamente su diccionario de campos: nombre, tipo y rango
(o valores permitidos) de cada entrada, y el conjunto de decisiones posibles.

- El adaptador es el ÚNICO punto de contacto con el sistema legacy: envía una solicitud y recibe
  una decisión. Ningún otro módulo de GhostMind importa, lee ni ejecuta código del legacy.
- GhostMind NUNCA lee el código fuente del legacy ni el archivo de reglas verdaderas.
- Una prueba automática DEBE fallar si el paquete de GhostMind referencia el paquete del legacy,
  el de evaluación o el archivo de reglas verdaderas.

Razón: el experimento mide si las reglas pueden descubrirse solo observando el comportamiento;
cualquier fuga de conocimiento invalida los resultados.

### II. Evidencia y trazabilidad

- Cada consulta al sistema (entrada, decisión, ronda, origen del caso y momento) DEBE quedar
  registrada antes de usarse. El origen distingue muestreo aleatorio, valores límite, categorías,
  bisección, contraejemplos y verificación.
- El número de consultas lo cuenta el adaptador y se reporta en cada ejecución.
- Cada regla reportada DEBE poder rastrearse hasta los casos que la respaldan y los que la
  contradicen.

Razón: una regla sin evidencia no puede validarse ni defenderse ante un especialista.

### III. Honestidad experimental (NO NEGOCIABLE)

- Los criterios de éxito, su forma de cálculo y sus umbrales se fijan en la especificación antes
  de ejecutar el experimento.
- Las reglas plantadas, las alteraciones de la versión modernizada y las semillas se definen en el
  plan y NO se modifican después de ver resultados para alcanzar una meta.
- Todo número publicado en `resultados/` sale de una ejecución real y reproducible; nunca se
  escriben cifras a mano.
- Los incumplimientos se reportan tal como ocurren (por ejemplo, una regla no encontrada) junto con
  su explicación.
- Solo el módulo de evaluación, que está fuera de GhostMind, consulta las reglas verdaderas.

Razón: el valor del prototipo para el informe depende de que sus resultados sean creíbles.

### IV. Humano en el ciclo

- Ninguna regla se acepta de forma automática. GhostMind solo asigna los estados `hipótesis` y
  `corroborada`.
- Los estados `validada` y `rechazada` solo los asigna un especialista desde el catálogo, y la
  decisión queda registrada con su fecha y una nota opcional.
- Cada regla muestra su nivel de confianza, calculado a partir de los casos que la respaldan y de
  sus contraejemplos.

Razón: observar desde afuera no garantiza ver todo el comportamiento; la decisión final es humana.

### V. Reproducibilidad y simplicidad

- Toda ejecución es determinista dada su semilla; la misma semilla produce las mismas consultas,
  las mismas reglas y las mismas métricas.
- El descubrimiento usa modelos interpretables. Un modelo de lenguaje, si se usa, SOLO redacta
  reglas ya descubiertas; está desactivado por defecto y su ausencia no cambia ningún resultado.
- Se elige el diseño más simple que cumpla la especificación; toda complejidad adicional se
  justifica en el plan.
- Cada fase termina con pruebas automáticas que pasan.

Razón: un evaluador debe poder repetir el experimento en un computador personal y obtener lo mismo.

## Restricciones técnicas y de seguridad

- Lenguaje Python 3.11 o superior; SQLite para el registro de evidencia; scikit-learn y pandas para
  el extractor; Streamlit para el catálogo y el verificador; pytest para las pruebas.
- Herramientas gratuitas que funcionen sin servidor ni conexión, salvo el modelo de lenguaje
  opcional.
- El repositorio no contiene llaves, contraseñas, tokens ni datos personales. Las llaves se leen de
  variables de entorno y los archivos locales de configuración están excluidos en `.gitignore`.
- Los datos del sistema legacy son sintéticos; no se usa información de ninguna organización real.
- La documentación, la interfaz y los mensajes al usuario están en español.

## Flujo de trabajo por fases

- El trabajo avanza por fases (0 a 7) definidas en el plan. Cada fase termina con pruebas pasando,
  un commit local y un resumen corto, y la siguiente fase empieza solo con el visto bueno del
  usuario.
- La especificación y el plan se revisan con el usuario antes de implementar.
- No se hace push ni se crea el repositorio remoto hasta que el usuario lo pida.
- Los cambios a reglas plantadas, alteraciones o criterios de éxito después de la Fase 1 requieren
  una enmienda explícita de la especificación, aprobada por el usuario y registrada en el historial
  de git.

## Gobernanza

- Esta constitución prevalece sobre cualquier otra práctica del repositorio. Cada plan incluye una
  verificación de cumplimiento (Constitution Check) y toda excepción se justifica en su tabla de
  complejidad.
- Las enmiendas se documentan en este archivo con su razón, se aprueban por el usuario y se
  versionan con versionado semántico: MAYOR para eliminar o redefinir principios, MENOR para
  agregar principios o secciones, PARCHE para aclaraciones de redacción.
- La revisión de cumplimiento se hace al cerrar cada fase, antes del commit.

**Version**: 1.0.0 | **Ratified**: 2026-11-12 | **Last Amended**: 2026-11-12
