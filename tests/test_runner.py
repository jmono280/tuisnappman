import threading
import time

from tuisnappman.runner import Runner


def test_timeout_returns_error_result():
    result = Runner().run(["sleep", "5"], timeout=0.2)
    assert result.returncode == 124
    assert "tiempo agotado" in result.stderr


def test_cancel_kills_the_process_quickly():
    cancel = threading.Event()
    cancel.set()
    start = time.monotonic()
    result = Runner().run(["sleep", "30"], cancel=cancel)
    assert result.returncode == 130
    assert time.monotonic() - start < 3


def test_normal_command_still_returns_output():
    result = Runner().run(["echo", "hola"])
    assert result.ok and result.stdout.strip() == "hola"
