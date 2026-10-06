import threading

from textual.widgets import DataTable

from tuisnappman.app import TuiSnappMan
from tuisnappman.cache import SizeCache, cache_key
from tuisnappman.services import snapper


async def test_table_shows_snapshots_without_current(fake_runner):
    app = TuiSnappMan(fake_runner)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        table = app.query_one("#snapshots", DataTable)
        assert table.row_count == 7


async def test_delete_asks_confirmation_and_runs_exact_command(fake_runner):
    app = TuiSnappMan(fake_runner)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        await pilot.click("#ok")
        await app.workers.wait_for_complete()
        await pilot.pause()
    assert ["snapper", "-c", "home", "delete", "568"] in fake_runner.history


async def test_cancel_does_not_delete(fake_runner):
    app = TuiSnappMan(fake_runner)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    assert not any("delete" in cmd for cmd in fake_runner.history)


async def test_rows_appear_before_sizes_are_computed(fake_runner):
    gate = threading.Event()
    original = fake_runner.run

    def slow_run(command, *, write=False, timeout=None, cancel=None):
        if command[:3] == ["btrfs", "filesystem", "du"]:
            gate.wait(timeout=10)
        return original(command, write=write, timeout=timeout, cancel=cancel)

    fake_runner.run = slow_run
    app = TuiSnappMan(fake_runner)
    async with app.run_test() as pilot:
        for _ in range(50):
            await pilot.pause(0.05)
            if app.query_one("#snapshots", DataTable).row_count:
                break
        table = app.query_one("#snapshots", DataTable)
        assert table.row_count == 7
        assert table.get_cell("home:568", "size") == "calculando..."
        gate.set()
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert table.get_cell("home:568", "size") == "100.0 GiB"
        assert app.sub_title == ""


async def test_sort_puts_largest_first_and_keeps_selection(fake_runner):
    app = TuiSnappMan(fake_runner)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        table = app.query_one("#snapshots", DataTable)
        table.move_cursor(row=table.get_row_index("home:584"))
        await pilot.press("s")
        await pilot.pause()
        assert table.get_row_at(0)[1] == "568"  # 100 GiB arriba
        assert app._selected().number == 584  # el cursor sigue en el mismo snapshot


async def test_cached_sizes_show_immediately_and_cancel_keeps_them(fake_runner, tmp_path):
    cache = SizeCache(tmp_path / "c.json")
    snaps = snapper.list_snapshots(fake_runner, "home")
    first = next(x for x in snaps if x.number == 568)
    cache.set(cache_key(first), 12345)
    gate = threading.Event()
    original = fake_runner.run

    def blocked_run(command, *, write=False, timeout=None, cancel=None):
        if command[:3] == ["btrfs", "filesystem", "du"]:
            gate.wait(timeout=10)
        return original(command, write=write, timeout=timeout, cancel=cancel)

    fake_runner.run = blocked_run
    app = TuiSnappMan(fake_runner, cache)
    async with app.run_test() as pilot:
        for _ in range(50):
            await pilot.pause(0.05)
            if app.query_one("#snapshots", DataTable).row_count:
                break
        table = app.query_one("#snapshots", DataTable)
        assert table.get_cell("home:568", "size") == "12.1 KiB (caché)"
        assert table.get_cell("home:584", "size") == "calculando..."
        await pilot.press("x")
        await pilot.pause()
        assert app.scanning is False
        assert table.get_cell("home:568", "size") == "12.1 KiB (caché)"
        assert table.get_cell("home:584", "size") == "sin calcular"
        assert "cancelado" in app.sub_title
        gate.set()
        await pilot.pause(0.2)
        assert table.get_cell("home:584", "size") == "sin calcular"  # resultado tardío ignorado


async def test_scan_results_are_saved_to_cache(fake_runner, tmp_path):
    cache = SizeCache(tmp_path / "c.json")
    app = TuiSnappMan(fake_runner, cache)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
    reloaded = SizeCache(tmp_path / "c.json")
    snaps = snapper.list_snapshots(fake_runner, "home")
    first = next(x for x in snaps if x.number == 568)
    assert reloaded.get(cache_key(first)) == 107374182400


async def test_dry_run_is_visible_and_reports_nothing_was_deleted(fake_runner):
    fake_runner.dry_run = True
    app = TuiSnappMan(fake_runner)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert "DRY-RUN" in app.title
        await pilot.press("d")
        await pilot.pause()
        await pilot.click("#ok")
        await app.workers.wait_for_complete()
        await pilot.pause()
        messages = [n.message for n in app._notifications]
        assert any("DRY-RUN: no se borró nada" in m for m in messages)
        assert not any(m.endswith("borrado") for m in messages)
