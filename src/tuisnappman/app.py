import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Static, TabbedContent, TabPane
from textual.widgets.data_table import CellDoesNotExist
from textual.worker import get_current_worker

from tuisnappman import cache as size_cache
from tuisnappman.models import Snapshot, human_size
from tuisnappman.runner import CommandError, Runner
from tuisnappman.screens.confirm import ConfirmScreen, PromptScreen
from tuisnappman.services import btrfs, snapper

SIZE_WORKERS = 4  # snapshots medidos en paralelo (solo lectura)


class TuiSnappMan(App):
    CSS_PATH = "tuisnappman.tcss"
    TITLE = "TuiSnappMan"
    BINDINGS = [
        ("d", "delete", "Borrar"),
        ("c", "create", "Crear"),
        ("r", "refresh", "Refrescar"),
        ("s", "sort", "Ordenar por espacio"),
        ("x", "cancel_scan", "Cancelar escaneo"),
        ("ctrl+q", "quit", "Salir"),
    ]

    def __init__(
        self, runner: Runner | None = None, cache: size_cache.SizeCache | None = None
    ) -> None:
        super().__init__()
        self.runner = runner or Runner()
        self.cache = cache or size_cache.SizeCache(size_cache.default_cache_path())
        self.snapshots: list[Snapshot] = []
        self.fresh: set[str] = set()  # filas con tamaño calculado en esta sesión
        self.scanning = False
        self.sort_by_size = False
        self._cancel = threading.Event()
        if self.runner.dry_run:
            self.title = "TuiSnappMan [DRY-RUN: no modifica nada]"

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Snapshots", id="tab-snapshots"):
                yield DataTable(id="snapshots", cursor_type="row", zebra_stripes=True)
            with TabPane("Espacio", id="tab-usage"):
                yield Static("Cargando...", id="usage", markup=False)
            with TabPane("Carpetas", id="tab-folders"):
                yield Static("Próximamente.")
            with TabPane("Registro", id="tab-log"):
                yield Static("Próximamente.")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#snapshots", DataTable)
        table.add_columns("Config", "#", "Fecha")
        table.add_column("Exclusivo", key="size")
        table.add_columns("Tipo", "Limpieza", "Descripción")
        self.action_refresh()

    # --- carga de datos -------------------------------------------------

    def action_refresh(self) -> None:
        self._cancel.set()  # corta el escaneo anterior, si lo hay
        self._cancel = threading.Event()
        self.load_data(self._cancel)

    def action_cancel_scan(self) -> None:
        if not self.scanning:
            return
        self._cancel.set()
        self.scanning = False
        self._set_status("Escaneo cancelado: se muestra la caché")
        self._render_table()

    @work(thread=True, exclusive=True, group="load")
    def load_data(self, cancel: threading.Event) -> None:
        """Lista los snapshots al instante y calcula el espacio uno a uno."""
        worker = get_current_worker()
        self.call_from_thread(self._set_status, "Leyendo snapshots...")
        try:
            subvolumes: dict[str, str] = {}
            snapshots: list[Snapshot] = []
            for config in snapper.list_configs(self.runner):
                subvolumes[config.name] = config.subvolume
                found = snapper.list_snapshots(self.runner, config.name)
                snapshots += [s for s in found if s.number != 0]
            usage = btrfs.usage(self.runner)
        except (CommandError, ValueError, KeyError) as exc:
            self.call_from_thread(self._set_status, f"Error: {exc}")
            self.call_from_thread(self.notify, f"Error: {exc}", severity="error", timeout=15)
            return
        self.cache.prune({size_cache.cache_key(s) for s in snapshots})
        snapshots = [
            replace(s, exclusive_bytes=self.cache.get(size_cache.cache_key(s))) for s in snapshots
        ]
        self.call_from_thread(self._show, snapshots, usage, cancel)
        total = len(snapshots)
        pool = ThreadPoolExecutor(max_workers=SIZE_WORKERS)
        try:
            futures = {
                pool.submit(
                    btrfs.exclusive_bytes,
                    self.runner,
                    subvolumes[snap.config],
                    snap.number,
                    cancel,
                ): snap
                for snap in snapshots
            }
            for done, future in enumerate(as_completed(futures), start=1):
                if worker.is_cancelled or cancel.is_set():
                    return
                snap, size = futures[future], future.result()
                if size is not None:
                    self.cache.set(size_cache.cache_key(snap), size)
                    self.cache.save()
                self.call_from_thread(self._set_size, snap, size, done, total, cancel)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        self.call_from_thread(self._finish_scan, cancel)

    def _set_status(self, text: str) -> None:
        self.sub_title = text

    def _is_current(self, cancel: threading.Event) -> bool:
        """False si este escaneo fue cancelado o reemplazado por otro."""
        return cancel is self._cancel and not cancel.is_set()

    def _show(self, snapshots: list[Snapshot], usage: str, cancel: threading.Event) -> None:
        if not self._is_current(cancel):
            return
        self.snapshots = snapshots
        self.fresh = set()
        self.scanning = True
        self._render_table()
        self.query_one("#usage", Static).update(usage)

    def _finish_scan(self, cancel: threading.Event) -> None:
        if self._is_current(cancel):
            self.scanning = False
            self._set_status("")

    def _set_size(
        self, snap: Snapshot, size: int | None, done: int, total: int, cancel: threading.Event
    ) -> None:
        if not self._is_current(cancel):
            return
        key = self._key(snap)
        self.fresh.add(key)
        self.snapshots = [
            replace(s, exclusive_bytes=size) if self._key(s) == key else s for s in self.snapshots
        ]
        if self.sort_by_size:
            self._render_table()
        else:
            table = self.query_one("#snapshots", DataTable)
            try:
                table.update_cell(key, "size", human_size(size))
            except CellDoesNotExist:
                pass
        self._set_status(
            f"Calculando espacio {done}/{total} (último: {snap.config} #{snap.number}) · x cancela"
        )

    @staticmethod
    def _key(snap: Snapshot) -> str:
        return f"{snap.config}:{snap.number}"

    def _size_text(self, snap: Snapshot) -> str:
        if self._key(snap) in self.fresh:
            return human_size(snap.exclusive_bytes)
        if snap.exclusive_bytes is not None:
            return f"{human_size(snap.exclusive_bytes)} (caché)"
        return "calculando..." if self.scanning else "sin calcular"

    def _render_table(self) -> None:
        table = self.query_one("#snapshots", DataTable)
        selected = self._selected()
        table.clear()
        if self.sort_by_size:
            rows = sorted(
                self.snapshots,
                key=lambda s: -1 if s.exclusive_bytes is None else s.exclusive_bytes,
                reverse=True,
            )
        else:
            rows = self.snapshots
        for s in rows:
            table.add_row(
                s.config,
                str(s.number),
                s.date,
                self._size_text(s),
                s.kind,
                s.cleanup,
                s.description,
                key=self._key(s),
            )
        if selected is not None:
            table.move_cursor(row=table.get_row_index(self._key(selected)))

    def action_sort(self) -> None:
        self.sort_by_size = not self.sort_by_size
        self._render_table()

    # --- acciones -------------------------------------------------------

    def _selected(self) -> Snapshot | None:
        table = self.query_one("#snapshots", DataTable)
        if table.row_count == 0:
            return None
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        for s in self.snapshots:
            if f"{s.config}:{s.number}" == row_key.value:
                return s
        return None

    def action_delete(self) -> None:
        snap = self._selected()
        if snap is None:
            return
        newest = max(s.number for s in self.snapshots if s.config == snap.config)
        detail = f"Se liberarían ~{human_size(snap.exclusive_bytes)}."
        if snap.number == newest:
            detail += " ATENCIÓN: es el snapshot más reciente de esta config."
        if self.runner.dry_run:
            detail += " MODO DRY-RUN: no se ejecutará de verdad."
        command = f"snapper -c {snap.config} delete {snap.number}"

        def done(confirmed: bool | None) -> None:
            if confirmed:
                self.do_delete(snap)

        self.push_screen(ConfirmScreen(f"Borrar snapshot {snap.number}", command, detail), done)

    @work(thread=True, group="write")
    def do_delete(self, snap: Snapshot) -> None:
        try:
            snapper.delete_snapshots(self.runner, snap.config, [snap.number])
        except CommandError as exc:
            self.call_from_thread(self.notify, f"Error: {exc}", severity="error")
            return
        if self.runner.dry_run:
            self.call_from_thread(
                self.notify,
                f"DRY-RUN: no se borró nada (snapshot {snap.number} sigue existiendo)",
                severity="warning",
                timeout=10,
            )
            return
        self.call_from_thread(self.notify, f"Snapshot {snap.number} borrado")
        self.call_from_thread(self.action_refresh)

    def action_create(self) -> None:
        snap = self._selected()
        config = snap.config if snap else "home"

        def done(description: str | None) -> None:
            if description:
                self.do_create(config, description)

        self.push_screen(PromptScreen(f"Nuevo snapshot en '{config}'", "Descripción"), done)

    @work(thread=True, group="write")
    def do_create(self, config: str, description: str) -> None:
        try:
            snapper.create_snapshot(self.runner, config, description)
        except CommandError as exc:
            self.call_from_thread(self.notify, f"Error: {exc}", severity="error")
            return
        if self.runner.dry_run:
            self.call_from_thread(
                self.notify,
                f"DRY-RUN: no se creó ningún snapshot en '{config}'",
                severity="warning",
                timeout=10,
            )
            return
        self.call_from_thread(self.notify, f"Snapshot creado en '{config}'")
        self.call_from_thread(self.action_refresh)
