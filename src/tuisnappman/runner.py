import subprocess
import threading
import time
from dataclasses import dataclass

POLL_SECONDS = 0.25  # cada cuánto se comprueba cancelación y tiempo máximo


class CommandError(RuntimeError):
    """Un comando terminó con error."""


@dataclass
class Result:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def check(self) -> "Result":
        if not self.ok:
            detail = self.stderr.strip() or self.stdout.strip() or f"código {self.returncode}"
            raise CommandError(f"{' '.join(self.command)}: {detail}")
        return self


class Runner:
    """Único punto que ejecuta comandos. Nunca usa shell=True."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.history: list[list[str]] = []

    def run(
        self,
        command: list[str],
        *,
        write: bool = False,
        timeout: float | None = None,
        cancel: threading.Event | None = None,
    ) -> Result:
        """Ejecuta `command`.

        Si `write` y dry-run, solo lo registra. Si `cancel` se activa o se
        agota `timeout`, el proceso se mata.
        """
        self.history.append(command)
        if write and self.dry_run:
            return Result(command, 0, "[dry-run] " + " ".join(command), "")
        try:
            proc = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
        except OSError as exc:
            code = 127 if isinstance(exc, FileNotFoundError) else 126
            return Result(command, code, "", str(exc))
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            try:
                out, err = proc.communicate(timeout=POLL_SECONDS)
                return Result(command, proc.returncode, out, err)
            except subprocess.TimeoutExpired:
                if cancel is not None and cancel.is_set():
                    proc.kill()
                    proc.communicate()
                    return Result(command, 130, "", "cancelado")
                if deadline is not None and time.monotonic() >= deadline:
                    proc.kill()
                    proc.communicate()
                    return Result(command, 124, "", f"tiempo agotado ({timeout:.0f} s)")
