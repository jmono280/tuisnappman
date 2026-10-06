"""Caché en disco de tamaños exclusivos. No importa Textual.

Los tamaños cambian al borrar otros snapshots, así que lo guardado se muestra
siempre como "antiguo" hasta que se recalcula. La caché es opcional: si no se
puede leer o escribir, la app funciona igual.
"""

import json
import os
import threading
import time
from pathlib import Path

from tuisnappman.models import Snapshot

VERSION = 1


def default_cache_path() -> Path:
    """Como root (uso normal con sudo) usa /var/cache; si no, ~/.cache."""
    if os.geteuid() == 0:
        base = Path("/var/cache")
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "tuisnappman" / "sizes.json"


def cache_key(snap: Snapshot) -> str:
    """Incluye la fecha para no reutilizar un número de snapshot reciclado."""
    return f"{snap.config}:{snap.number}:{snap.date}"


class SizeCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, float | int]] = self._read()

    def _read(self) -> dict[str, dict[str, float | int]]:
        try:
            data = json.loads(self.path.read_text())
            if data.get("version") != VERSION:
                return {}
            entries = data.get("entries", {})
            return {
                k: v
                for k, v in entries.items()
                if isinstance(v, dict) and isinstance(v.get("bytes"), int)
            }
        except (OSError, ValueError, AttributeError):
            return {}

    def get(self, key: str) -> int | None:
        with self._lock:
            entry = self._entries.get(key)
            return int(entry["bytes"]) if entry else None

    def set(self, key: str, size: int) -> None:
        with self._lock:
            self._entries[key] = {"bytes": size, "at": time.time()}

    def prune(self, keep: set[str]) -> None:
        """Descarta entradas de snapshots que ya no existen."""
        with self._lock:
            self._entries = {k: v for k, v in self._entries.items() if k in keep}

    def save(self) -> bool:
        """Escritura atómica. Devuelve False si no se pudo (no es fatal)."""
        with self._lock:
            payload = json.dumps({"version": VERSION, "entries": self._entries})
        tmp = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(payload)
            os.replace(tmp, self.path)
        except OSError:
            return False
        return True
