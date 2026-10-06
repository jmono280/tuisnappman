"""Envoltorio de `btrfs`. No importa Textual."""

import threading

from tuisnappman.runner import Runner

DU_TIMEOUT = 900.0  # segundos; `du` recorre el snapshot completo y puede ser lento


def snapshot_path(subvolume: str, number: int) -> str:
    return f"{subvolume.rstrip('/')}/.snapshots/{number}/snapshot"


def parse_du(output: str) -> int | None:
    """Devuelve la columna Exclusive de `btrfs filesystem du -s --raw`."""
    for line in output.splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[1])
    return None


def exclusive_bytes(
    runner: Runner, subvolume: str, number: int, cancel: threading.Event | None = None
) -> int | None:
    result = runner.run(
        ["btrfs", "filesystem", "du", "-s", "--raw", snapshot_path(subvolume, number)],
        timeout=DU_TIMEOUT,
        cancel=cancel,
    )
    return parse_du(result.stdout) if result.ok else None


def usage(runner: Runner, path: str = "/") -> str:
    result = runner.run(["btrfs", "filesystem", "usage", path])
    return result.stdout if result.ok else result.stderr.strip() or "No disponible"
