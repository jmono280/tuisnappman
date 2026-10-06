import json
from pathlib import Path

import pytest

from tuisnappman.runner import Result, Runner

CONFIGS = json.dumps({"configs": [{"config": "home", "subvolume": "/home"}]})
FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOTS = (FIXTURES / "snapper_list_home.json").read_text()
DU = "  Total  Exclusive  Set shared  Filename\n{total} {excl} 0 {path}\n"


class FakeRunner(Runner):
    """Responde con datos fijos y registra lo que se pediría ejecutar."""

    def __init__(self) -> None:
        super().__init__()
        self.responses: dict[str, str] = {
            "snapper --jsonout list-configs": CONFIGS,
            "snapper --jsonout -c home list": SNAPSHOTS,
            "btrfs filesystem usage /": "Overall:\n  Device size: 932GiB\n",
            "btrfs filesystem du -s --raw /home/.snapshots/568/snapshot": DU.format(
                total=200, excl=107374182400, path="/home/.snapshots/568/snapshot"
            ),
            "btrfs filesystem du -s --raw /home/.snapshots/584/snapshot": DU.format(
                total=200, excl=4096, path="/home/.snapshots/584/snapshot"
            ),
        }

    def run(
        self,
        command: list[str],
        *,
        write: bool = False,
        timeout: float | None = None,
        cancel=None,
    ) -> Result:
        self.history.append(command)
        key = " ".join(command)
        if write:
            return Result(command, 0, "", "")
        if key in self.responses:
            return Result(command, 0, self.responses[key], "")
        return Result(command, 1, "", f"comando no esperado: {key}")


@pytest.fixture
def fake_runner() -> FakeRunner:
    return FakeRunner()


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Ningún test escribe en la caché real del sistema."""
    monkeypatch.setattr(
        "tuisnappman.cache.default_cache_path", lambda: tmp_path / "cache" / "sizes.json"
    )
