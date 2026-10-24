"""Zakładki panelu Plant nie mogą za każdym razem parsować biblioteki napędów (zrywanie LRT-NET)."""

import shutil
from pathlib import Path

from linumert_plant import drive_library
from linumert_plant.drive_library import LIBRARY_DIR, load_library


def _copy(tmp_path: Path) -> Path:
    for src in LIBRARY_DIR.glob("*.yaml"):
        shutil.copy(src, tmp_path / src.name)
    return tmp_path


def test_second_load_does_not_reparse(tmp_path, monkeypatch):
    folder = _copy(tmp_path)
    first = load_library(folder)

    def fail(path):
        raise AssertionError(f"ponowne parsowanie {path}")

    monkeypatch.setattr(drive_library, "_read_yaml", fail)
    assert load_library(folder) == first


def test_cached_library_is_a_copy(tmp_path):
    folder = _copy(tmp_path)
    lib = load_library(folder)
    lib[next(iter(lib))]["name"] = "zmienione"
    assert load_library(folder) != lib


def test_changed_file_invalidates_cache(tmp_path):
    folder = _copy(tmp_path)
    before = load_library(folder)
    target = sorted(folder.glob("*.yaml"))[0]
    target.write_text(target.read_text(encoding="utf-8") + "\n# zmiana\n", encoding="utf-8")
    after = load_library(folder)
    assert after.keys() == before.keys()
