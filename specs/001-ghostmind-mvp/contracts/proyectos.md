# Contrato: proyectos

Archivo `sistemas/proyectos.json` (Fase 9). Reemplaza a `sistemas/objetivos.json`. Cada proyecto es
un sistema legacy con su diccionario de atributos y sus cajas negras. Todas las cajas negras de un
proyecto reciben el mismo registro, así que comparten diccionario y base de evidencia.

```json
{
  "credito": {
    "nombre": "Créditos (CRDAPR01)",
    "descripcion": "Módulo legacy de aprobación de créditos de consumo...",
    "diccionario": "diccionario_credito.json",
    "cajas_negras": {
      "legacy": {"punto_de_entrada": "legacy.crdapr01:CRDAPR01", "descripcion": "..."},
      "modernizado": {"punto_de_entrada": "legacy.crdapr_moderno:CRDAPR01", "descripcion": "..."}
    }
  },
  "seguros": {
    "nombre": "Seguros de auto (SINAUT01)",
    "descripcion": "Módulo legacy simulado que decide si una reclamación se paga...",
    "diccionario": "diccionario_seguros.json",
    "base": "seguros.sqlite",
    "cajas_negras": {
      "legacy": {"punto_de_entrada": "legacy.sinaut01:SINAUT01", "descripcion": "..."}
    }
  }
}
```

Reglas:

- `diccionario` es relativo a `sistemas/` y sigue [diccionario.md](diccionario.md).
- `base` es opcional. El proyecto que no la declara usa la base principal (`GHOSTMIND_DB` o
  `datos/ghostmind.sqlite`). Los demás usan ese archivo en la misma carpeta de la base principal.
  Solo un proyecto puede omitirla y dos proyectos no pueden compartir archivo.
- Cada proyecto tiene al menos una caja negra. Una caja negra también puede escribirse solo como
  punto de entrada (`"legacy": "legacy.crdapr01:CRDAPR01"`), sin descripción.
- El proyecto por defecto es `credito`. Las órdenes y el catálogo lo usan si no se elige otro.
- `ghostmind/proyectos.py` lee este archivo. Solo `ghostmind/adaptador.py` convierte un punto de
  entrada en una función.
- El registro se niega a abrir una base cuyas columnas de atributos no coinciden con el
  diccionario del proyecto (`BaseDeOtroDiccionario`).

## Frases de las decisiones (opcional en el diccionario)

Cada decisión del diccionario puede ser un texto o un objeto con sus frases:

```json
"decisiones": [
  {"valor": "PAGAR", "frase": "Se paga la reclamación", "frase_general": "Se paga cualquier reclamación.",
   "palabras": ["paga", "pagar", "pago"], "tono": "positivo"}
]
```

- `frase`: comienzo de la redacción por plantilla ("Se paga la reclamación cuando ...").
- `frase_general`: redacción de una regla que aplica a cualquier caso.
- `palabras`: formas con las que la redacción asistida debe expresar esa decisión (control de D9).
- `tono`: `positivo`, `negativo`, `intermedio` o `neutro`. Solo da el color de la etiqueta en el
  catálogo.

Si la decisión es solo un texto, como en `diccionario_credito.json`, se usan las frases conocidas de
`APROBADO`, `RECHAZADO` y `REVISION_MANUAL`, y para cualquier otra una frase genérica. Así ninguna
redacción del proyecto de crédito cambia.
