"""Instrumento para medir C4 (utilidad del catálogo para especialistas).

- ``preguntas.json``: definición de las preguntas (solicitudes de prueba y valoraciones).
- ``generar.py``: produce ``cuestionario.md`` y ``clave.json`` a partir de las reglas verdaderas.
- ``plantilla_respuestas.csv``: formato para registrar las respuestas de cada participante.
- ``puntuar.py``: calcula el porcentaje de respuestas correctas y la utilidad promedio.

La clave se calcula con las reglas verdaderas; los participantes solo usan el catálogo.
"""
