"""Testy tools/lock.py (blokady zasobów Claude/Codex, D30)."""

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "lrt_lock", Path(__file__).resolve().parent.parent / "tools" / "lock.py")
lock = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lock)


@pytest.fixture(autouse=True)
def _dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LINUMERT_LOCK_DIR", str(tmp_path))


def test_acquire_busy_then_release():
    assert lock.acquire("linuxcnc", "Codex", "RIP", now=1000.0) == (True, None)
    ok, holder = lock.acquire("linuxcnc", "Claude", now=1100.0)
    assert not ok and holder["model"] == "Codex"
    assert not lock.release("linuxcnc", "Claude")
    assert lock.release("linuxcnc", "Codex")
    assert lock.acquire("linuxcnc", "Claude", now=1200.0)[0]


def test_stale_lock_is_taken_over():
    lock.acquire("linuxcnc", "Codex", ttl=60, now=0.0)
    ok, old = lock.acquire("linuxcnc", "Claude", now=120.0)
    assert ok and old["model"] == "Codex"
    assert lock.read("linuxcnc")["model"] == "Claude"


def test_own_lock_refresh_and_bad_name():
    lock.acquire("wsl-build", "Codex", now=0.0)
    assert lock.acquire("wsl-build", "Codex", now=50.0) == (True, None)
    with pytest.raises(ValueError):
        lock.acquire("../zly", "Codex")


def test_cli_exit_codes(capsys):
    assert lock.main(["acquire", "linuxcnc", "--model", "Codex"]) == 0
    assert lock.main(["acquire", "linuxcnc", "--model", "Claude"]) == 1
    assert lock.main(["status"]) == 0
    assert "linuxcnc: Codex" in capsys.readouterr().out
    assert lock.main(["release", "linuxcnc", "--model", "Codex"]) == 0
    assert lock.main(["acquire", "Zły", "--model", "Codex"]) == 2
