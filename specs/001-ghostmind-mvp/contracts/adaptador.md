# Contrato: adaptador

Único punto de contacto entre GhostMind y un sistema. Vive en `ghostmind/adaptador.py`.

```python
class Adaptador:
    def __init__(self, diccionario: Diccionario, objetivo: str, registro: Registro,
                 ejecucion_id: int, presupuesto: int): ...

    consultas: int          # consultas hechas al sistema por esta instancia
    restantes: int          # presupuesto - consultas

    def consultar(self, solicitud: dict[str, int | str], ronda: int, origen: str) -> str:
        """Valida, arma el registro, llama al sistema, guarda el caso y devuelve la decisión."""
```

Comportamiento:

1. Si la solicitud tiene campos faltantes, sobrantes o valores fuera del diccionario, lanza
   `SolicitudInvalida` sin llamar al sistema y sin contar la consulta.
2. Si `restantes == 0`, lanza `PresupuestoAgotado` sin llamar al sistema.
3. Arma el registro de ancho fijo y llama al punto de entrada del objetivo, que se resuelve a
   partir de `sistemas/objetivos.json` al crear el adaptador.
4. Cuenta la consulta. Si el sistema lanza una excepción o devuelve un valor que no está en
   `decisiones`, guarda el caso con `decision = NULL` y el `error`, y lanza `ErrorDelSistema`.
5. Si no hay error, guarda el caso con su decisión, ronda y origen, y devuelve la decisión.

Garantías que verifican las pruebas:

- Ningún otro módulo de `ghostmind/` resuelve ni llama puntos de entrada de sistemas.
- Ningún archivo de `ghostmind/` importa `legacy` o `evaluacion`, ni menciona
  `reglas_verdaderas` o `alteraciones`.
- `consultas` coincide con el número de filas de `casos` de la ejecución.
