from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    name: str
    subvolume: str


@dataclass(frozen=True)
class Snapshot:
    config: str
    number: int
    kind: str
    date: str
    cleanup: str
    description: str
    exclusive_bytes: int | None = None


def human_size(size: int | None) -> str:
    if size is None:
        return "?"
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"
