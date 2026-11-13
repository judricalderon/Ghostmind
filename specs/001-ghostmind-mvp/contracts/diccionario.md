# Contrato: diccionario de campos y registro del sistema

Archivo `sistemas/diccionario_credito.json`. Es el documento de interfaz que GhostMind recibe; no
contiene reglas de negocio.

```json
{
  "sistema": "CRDAPR01 - aprobacion de creditos",
  "longitud_registro": 35,
  "decisiones": ["APROBADO", "RECHAZADO", "REVISION_MANUAL"],
  "campos": [
    {"nombre": "edad", "etiqueta": "edad", "tipo": "entero", "unidad": "años",
     "minimo": 18, "maximo": 80, "inicio": 1, "longitud": 3},
    {"nombre": "ingreso_mensual", "etiqueta": "ingreso mensual", "tipo": "entero", "unidad": "pesos",
     "minimo": 0, "maximo": 20000000, "inicio": 4, "longitud": 9},
    {"nombre": "monto", "etiqueta": "monto solicitado", "tipo": "entero", "unidad": "pesos",
     "minimo": 1000000, "maximo": 150000000, "inicio": 13, "longitud": 9},
    {"nombre": "plazo_meses", "etiqueta": "plazo", "tipo": "entero", "unidad": "meses",
     "minimo": 6, "maximo": 120, "inicio": 22, "longitud": 3},
    {"nombre": "puntaje_credito", "etiqueta": "puntaje de crédito", "tipo": "entero", "unidad": "puntos",
     "minimo": 150, "maximo": 950, "inicio": 25, "longitud": 3},
    {"nombre": "antiguedad_meses", "etiqueta": "antigüedad como cliente", "tipo": "entero", "unidad": "meses",
     "minimo": 0, "maximo": 240, "inicio": 28, "longitud": 3},
    {"nombre": "tipo_empleo", "etiqueta": "tipo de empleo", "tipo": "categorico", "inicio": 31, "longitud": 1,
     "valores": [{"valor": "EMPLEADO", "codigo": "E"}, {"valor": "INDEPENDIENTE", "codigo": "I"},
                 {"valor": "PENSIONADO", "codigo": "P"}, {"valor": "DESEMPLEADO", "codigo": "D"}]},
    {"nombre": "codigo_convenio", "etiqueta": "código de convenio", "tipo": "categorico", "inicio": 32, "longitud": 4,
     "valores": [{"valor": "NINGUNO", "codigo": "    "}, {"valor": "C-12", "codigo": "C-12"},
                 {"valor": "C-31", "codigo": "C-31"}, {"valor": "C-45", "codigo": "C-45"},
                 {"valor": "C-77", "codigo": "C-77"}]}
  ]
}
```

Campos opcionales para la redacción de reglas (agregados en la Fase 4): `articulo` de cada campo
(`el` o `la`) y `etiqueta` de cada valor categórico (por ejemplo, `desempleado`). No cambian el
registro ni la validación.

## Registro de ancho fijo

- Campos enteros: dígitos con ceros a la izquierda, por ejemplo `edad` 35 es `035`.
- Campos categóricos: el `codigo` del valor, rellenado con espacios a la derecha.
- Ejemplo (35 posiciones):
  `035002500000030000000036720096EC-12` corresponde a edad 35, ingreso 2.500.000, monto 30.000.000,
  plazo 36, puntaje 720, antigüedad 96, EMPLEADO, convenio C-12.

## Punto de entrada del sistema

```text
CRDAPR01(WK_REG: str) -> str   # devuelve "APROBADO", "RECHAZADO" o "REVISION_MANUAL"
```

`sistemas/objetivos.json` asocia cada nombre de objetivo con su punto de entrada:

```json
{
  "legacy": "legacy.crdapr01:CRDAPR01",
  "modernizado": "legacy.crdapr_moderno:CRDAPR01"
}
```
