# AGENTS.md — TuiSnappMan

TUI en Python/Textual para gestionar snapshots de Snapper y encontrar qué
archivos pesados ocupan espacio. Lee `spec.md` antes de tocar código.

## Git: reglas estrictas
- **No ejecutes ningún comando de git sin consultar al usuario**: ni `commit`,
  `push`, `pull`, `add`, `init`, `branch`, `merge`, `rebase`, `reset`, `tag` ni
  `stash`. Tampoco `gh` para crear PRs o releases.
- Solo se permiten comandos de git de lectura (`git status`, `git diff`,
  `git log`) cuando ayuden a la tarea.
- Cuando haya cambios listos, **genera un mensaje de commit corto** (una línea,
  imperativo, en inglés, ~50 caracteres) y entrégalo al usuario junto con los
  archivos afectados. Ejemplo: `add snapshot table with exclusive size column`.
- **Pide al usuario que haga el commit y el push él mismo.** Tú no los subes.
- Un commit por cambio lógico. Si el cambio es grande, propón dividirlo en
  varios mensajes cortos.

## Comandos
- Entorno: `python -m venv .venv && source .venv/bin/activate`
- Instalar: `pip install -e ".[dev]"`
- Ejecutar: `python -m tuisnappman` (o `textual run --dev src/tuisnappman/app.py`)
- Consola de depuración: `textual console` en otra terminal
- Pruebas: `pytest`
- Lint y formato: `ruff check . && ruff format .`

## Reglas de código
1. **Seguridad primero.** Prohibido ejecutar `snapper delete/create` o `btrfs`
   con escritura en pruebas o ejemplos. Todo pasa por `runner.py`, que tiene
   modo `dry-run` y se sustituye por uno falso en tests.
2. Toda acción destructiva exige un `ModalScreen` de confirmación que muestre
   el comando exacto.
3. `services/` no importa Textual. La UI no llama a `subprocess` directamente.
4. Los comandos bloqueantes van en `@work(thread=True)`; actualiza widgets con
   `call_from_thread` o mensajes (`post_message` es thread-safe).
5. Nunca uses `print` en la app; usa `self.log` y `textual console`.
6. Estilos en `.tcss`, no en el código Python.
7. Cada parser nuevo lleva una fixture con salida real y su prueba.
8. Type hints en todo; funciones cortas; sin dependencias nuevas sin motivo.
9. No guardes ni registres contraseñas ni salidas con datos personales.
10. No uses `shell=True`; pasa listas de argumentos.

## Convenciones
- Código y commits en inglés; texto de interfaz y README en español.
- Antes de proponer un commit: `ruff` y `pytest` en verde.

## Documentación
Consulta la documentación actual de Textual (no la memoria): hay cambios entre
versiones. Versión objetivo: Textual 6.x. Ojo con los tutoriales antiguos:
`@work` con código bloqueante requiere `thread=True`, y el atajo de salida
estándar es Ctrl+Q.

## Qué NO hacer
- No cambiar configs de snapper ni activar quotas sin que el usuario lo pida.
- No añadir rollback en el MVP.
- No crear archivos fuera de `/home/gutidev/Projects/TuiSnappMan`.
- Muestra al usuario el contenido antes de escribir archivos nuevos y espera su
  visto bueno.
