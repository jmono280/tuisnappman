# MEMORY.md — TuiSnappMan

Memoria del proyecto entre sesiones. Máx. 50 líneas: al actualizar, resume o
borra lo obsoleto. No dupliques lo que ya está en `spec.md` o `AGENTS.md`.

## Estado (actualizado 2026-10-06)
- v0.1 base creada: tabla de snapshots, borrar con confirmación, crear, uso
  de disco. 14 tests y ruff en verde. Pestañas Carpetas y Registro: placeholder.
- Tabla inmediata; tamaños en 4 hilos con caché en disco (`cache.py`, se ve como
  "(caché)") y tecla `x` para cancelar (mata los `btrfs du` en curso).
  El usuario tiene ~60 snapshots y el `du` tarda: no se probó aún la velocidad real.
- Sin repo git todavía; el usuario hace init, commits y push (ver AGENTS.md).
- Parser de `snapper list` verificado con salida real; la app completa aún
  solo con runner falso, nunca probada con sudo.

## Pendiente
1. (hecho) `list` y `list-configs` verificados con salida real en `tests/fixtures/`.
2. Probar con sudo contra el sistema real del usuario.
3. Pestaña Carpetas (`du` + atajos Steam, ~/.cache, ~/Downloads).
4. Pestaña Registro (historial del runner).
5. CI (ruff + pytest) y capturas para el README.

## Comandos clave
- Tests: `.venv/bin/pytest -q` · Lint: `.venv/bin/ruff check . && .venv/bin/ruff format .`
- Ejecutar: `sudo .venv/bin/python -m tuisnappman` (sudo no hereda el venv)
- Sin root: `.venv/bin/python -m tuisnappman --dry-run`
- Depurar: `textual console` + `textual run --dev src/tuisnappman/app.py`
- Ver espacio: `sudo btrfs filesystem du -s --human-readable /home/.snapshots/N/snapshot`
- Borrar/crear: `sudo snapper -c home delete N` / `create -t single -d "texto"`

## Decisiones
- Se lanza con sudo; sin quotas (solo `btrfs filesystem du`); UI en español.
- Todo comando pasa por `runner.py`; escribir = `write=True` (respeta dry-run).
- `services/` y `cache.py` no importan Textual; tests nunca ejecutan snapper real.
- Caché: `/var/cache/tuisnappman/sizes.json` como root, si no `~/.cache`. Clave
  incluye la fecha; el valor guardado siempre se marca antiguo hasta recalcular.
- Quotas de btrfs descartadas por ahora (única vía a tamaños instantáneos).

## Hallazgos del entorno
- Equipo CachyOS, btrfs en `/dev/nvme0n1p2` (932 GB, ~86% usado al empezar).
- Subvolúmenes `@` y `@home` con configs snapper `root` y `home` propias.
- Python 3.14, sin `uv`. Textual 6.x (docs vía `npx ctx7@latest`).
- Caso origen: juego de ~100 GB borrado, espacio retenido por snapshots.

## Trampas conocidas
- `snapper` sin root responde `No permissions.`
- `df` miente en btrfs; usar `btrfs filesystem usage /`.
- Con Textual, `@work` bloqueante necesita `thread=True`; salir es Ctrl+Q.
- Ruff: RUF012 ignorado por `BINDINGS` (falso positivo de Textual).
