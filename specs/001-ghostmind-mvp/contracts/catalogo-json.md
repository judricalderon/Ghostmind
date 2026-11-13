# Contrato: catálogo exportado en JSON

```json
{
  "formato": "ghostmind-catalogo/1",
  "generado": "2026-11-20T10:15:00",
  "ejecucion": {
    "id": 1, "objetivo": "legacy", "semilla": 42, "presupuesto": 20000,
    "consultas": 0, "rondas": 0, "motivo_parada": "estable", "version": "0.1.0"
  },
  "reglas": [
    {
      "codigo": "GM-01",
      "decision": "RECHAZADO",
      "condiciones": {
        "codigo_convenio": {"valores": ["NINGUNO", "C-12", "C-31", "C-45"]},
        "edad": {"min": 21, "max": 80},
        "puntaje_credito": {"min": 150, "max": 399}
      },
      "umbrales_confirmados": [{"campo": "puntaje_credito", "valor_cambio": 400}],
      "respaldo": 0,
      "contraejemplos": 0,
      "confianza": 0.0,
      "estado": "corroborada",
      "texto_tecnico": "SI ... ENTONCES RECHAZADO",
      "texto_negocio": "Se rechaza la solicitud cuando ...",
      "texto_llm": null,
      "revisiones": [{"decision": "validada", "nota": "", "momento": "2026-11-20T10:20:00"}]
    }
  ]
}
```

Las cifras del ejemplo son ilustrativas del formato, no resultados.

Reglas del formato:

- `reglas` va ordenada por `codigo`.
- `confianza` está entre 0 y 1.
- `estado` es `hipotesis`, `corroborada`, `validada` o `rechazada`.
- `condiciones` solo incluye los campos que restringen algo respecto del diccionario.
- El archivo no incluye casos individuales; la evidencia completa queda en la base SQLite.
