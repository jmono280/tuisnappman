# TuiSnappMan — Especificación

TUI en Python (Textual) para gestionar snapshots de Snapper sobre btrfs:
ver qué ocupa espacio, decidir qué borrar y crear snapshots limpios, sin
memorizar comandos.

## Problema
En btrfs con Snapper, borrar archivos pesados no libera espacio si algún
snapshot anterior todavía los referencia. Pasa con cualquier cosa grande que
se descarga o se copia al disco y luego se borra: juegos, ISOs, modelos de IA,
cachés, builds, backups, descargas, máquinas virtuales.

`df` muestra el disco lleno y no dice por qué. Averiguarlo exige encadenar
`snapper`, `btrfs filesystem du` y `du`. TuiSnappMan lo resume en una pantalla:
qué snapshots retienen espacio, cuánto liberaría borrar cada uno y dónde están
los archivos más pesados.

Caso real que originó el proyecto: tras desinstalar un juego de ~100 GB el disco
seguía lleno. La causa podía ser un snapshot, o restos fuera de ellos (prefijos
de Proton, cachés de shaders). La herramienta debe distinguir ambos casos.

## Alcance v0.1 (MVP)
1. Listar snapshots de todas las configs (`snapper list-configs`).
2. Mostrar por snapshot: número, fecha, tipo, descripción y **espacio exclusivo**.
3. Resaltar los snapshots que más espacio liberarían.
4. Borrar uno o varios snapshots con confirmación.
5. Crear un snapshot manual (`single`) con descripción.
6. Mostrar el uso real del disco (`btrfs filesystem usage`).
7. Explorar las carpetas y archivos más pesados de `/home` (`du`), para ver si
   el espacio está fuera de los snapshots. Con atajos a ubicaciones típicas
   (Steam `compatdata`/`shadercache`/`downloading`, `~/.cache`, `~/Downloads`,
   contenedores y VMs).

## Fuera de alcance (por ahora)
Rollback, edición de configs de Snapper, activar quotas, otros sistemas de
archivos que no sean btrfs.

## Comandos que envuelve la app
| Acción | Comando |
|---|---|
| Configs | `snapper list-configs` |
| Listar | `snapper -c <cfg> list` |
| Espacio por snapshot | `btrfs filesystem du -s --human-readable <ruta>/.snapshots/<N>/snapshot` |
| Espacio con quotas | `btrfs qgroup show -pcre /` |
| Comparar | `snapper -c <cfg> status N..M` |
| Borrar | `snapper -c <cfg> delete N` (o rango `N-M`) |
| Crear | `snapper -c <cfg> create -t single -d "<texto>"` |
| Uso global | `btrfs filesystem usage /` |
| Carpetas pesadas | `du -h --max-depth=1 <ruta>` |

Notas aprendidas:
- `/` y `/home` son subvolúmenes distintos, cada uno con su config y sus
  snapshots. Un snapshot de `root` no incluye `/home`.
- La columna `Exclusive` es lo que se libera al borrar ese snapshot.
- `df` miente en btrfs; usar `btrfs filesystem usage`.
- `snapper` y `btrfs` requieren root. Sin permisos devuelven `No permissions.`
- El espacio puede tardar unos segundos en aparecer como libre tras borrar.
- Los snapshots `timeline` los limpia Snapper solo; los `single` no.

## Requisitos de seguridad
- Solo lectura por defecto. Nada destructivo sin un diálogo de confirmación que
  muestre el comando exacto y el espacio estimado a liberar.
- Modo `--dry-run` que imprime los comandos sin ejecutarlos.
- Nunca guardar ni pedir la contraseña dentro de la TUI.
- No borrar el snapshot más reciente ni los marcados `important` sin doble
  confirmación.
- La app no ejecuta `git`. Ver `AGENTS.md` para las reglas de control de versiones.

## Interfaz
- Pestañas: **Snapshots** · **Espacio** · **Carpetas** · **Registro**.
- `DataTable` para snapshots, ordenable por espacio.
- `ModalScreen` para confirmar borrado y para crear snapshot.
- Atajos: `d` borrar, `c` crear, `r` refrescar, `s` ordenar, `Ctrl+Q` salir.
- Los comandos corren en `@work(thread=True)`; la UI nunca se bloquea y
  muestra un indicador de carga.

## Arquitectura
```
src/tuisnappman/
  app.py          # App Textual, bindings, pantallas
  screens/        # SnapshotsScreen, ConfirmDeleteModal, CreateModal
  widgets/        # SnapshotTable, DiskUsageBar
  services/       # snapper.py, btrfs.py, disk.py  (sin imports de Textual)
  models.py       # dataclasses Snapshot, Config, DiskUsage
  runner.py       # ejecuta comandos (subprocess), soporta dry-run
  tuisnappman.tcss
tests/            # parsers con salidas reales guardadas + pruebas Pilot
```
Regla: `services/` y `runner.py` no conocen la UI, así se prueban sin Textual.

## Stack
Python ≥ 3.11 · Textual ≥ 6 · pytest + pytest-asyncio · ruff · textual-dev (dev).
Entorno con `venv` + `pip`, para que cualquiera pueda clonar y ejecutar.

## Pruebas
- Parsers con fixtures de salidas reales (por ejemplo, la lista de snapshots
  de `home` 568, 584–587).
- UI con `run_test()` + `Pilot` (pulsar `d`, confirmar, comprobar la llamada).
- El runner se sustituye por uno falso: las pruebas nunca ejecutan snapper.

## Publicación en GitHub
README con capturas, LICENSE (MIT), `pyproject.toml` con entry point
`tuisnappman`, `.gitignore`, CI con ruff + pytest. Los pasos de git los
ejecuta el usuario (ver `AGENTS.md`).

## Criterios de aceptación del MVP
- Con la lista de ejemplo muestra los 5 snapshots con su espacio exclusivo.
- Borrar un snapshot pide confirmación y refresca la tabla.
- Distingue "el espacio está retenido por snapshots" de "el espacio está en
  archivos que siguen en disco".
- Cubre el flujo completo (ver, borrar, crear snapshot limpio) en menos de
  5 pulsaciones.

## Decisiones tomadas
1. Privilegios: la app se lanza con `sudo` (`sudo .venv/bin/python -m tuisnappman`).
2. Quotas: solo `btrfs filesystem du`, sin activar quotas.
3. Idioma de la interfaz: español.

## Pendiente de verificar
- `snapper --jsonout -c home list`: verificado con salida real (fixture en
  `tests/fixtures/snapper_list_home.json`).
- `snapper --jsonout list-configs`: verificado con salida real (fixture en
  `tests/fixtures/snapper_list_configs.json`).
- La app completa aún no se ha probado con sudo sobre el sistema real.
