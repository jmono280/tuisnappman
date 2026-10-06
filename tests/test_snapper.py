import pytest
from conftest import FIXTURES

from tuisnappman.models import human_size
from tuisnappman.runner import CommandError, Result, Runner
from tuisnappman.services import snapper


def test_list_configs(fake_runner):
    configs = snapper.list_configs(fake_runner)
    assert [(c.name, c.subvolume) for c in configs] == [("home", "/home")]


def test_list_snapshots(fake_runner):
    snaps = snapper.list_snapshots(fake_runner, "home")
    assert [s.number for s in snaps] == [0, 568, 584, 585, 586, 587, 588, 589]
    assert snaps[1].cleanup == "timeline"


def test_delete_builds_exact_command(fake_runner):
    snapper.delete_snapshots(fake_runner, "home", [568])
    assert fake_runner.history[-1] == ["snapper", "-c", "home", "delete", "568"]


def test_create_builds_exact_command(fake_runner):
    snapper.create_snapshot(fake_runner, "home", "limpio")
    assert fake_runner.history[-1] == [
        "snapper",
        "-c",
        "home",
        "create",
        "-t",
        "single",
        "-d",
        "limpio",
    ]


def test_dry_run_does_not_execute():
    runner = Runner(dry_run=True)
    result = snapper.delete_snapshots(runner, "home", [1])
    assert result.stdout.startswith("[dry-run]")


def test_failed_command_raises():
    with pytest.raises(CommandError):
        Result(["x"], 1, "", "No permissions.").check()


def test_human_size():
    assert human_size(None) == "?"
    assert human_size(512) == "512 B"
    assert human_size(107374182400) == "100.0 GiB"


def test_list_configs_real_output(fake_runner):
    real = (FIXTURES / "snapper_list_configs.json").read_text()
    fake_runner.responses["snapper --jsonout list-configs"] = real
    configs = snapper.list_configs(fake_runner)
    assert [(c.name, c.subvolume) for c in configs] == [("home", "/home"), ("root", "/")]
