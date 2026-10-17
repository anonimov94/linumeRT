"""Szkielet repozytorium zgodny z CLAUDE.md §3; kazdy katalog ma README.md."""

import importlib

import pytest
from conftest import REPO

DIRS = [
    "core/linumert", "simulation", "screens/linumert", "plant/core", "plant/library/drives",
    "config/machines", "docs/wymagania", "plant/server", "hal", "config/sim", "config/plant",
    "config/examples", "tools", "tools/vm", "tools/ci", "tests", "docs", "docs/prawne",
    "prompts", "community",
]
SUBPACKAGES = ["alarms", "tools", "programs", "generators", "machine", "plugins", "cnc", "diag"]


@pytest.mark.parametrize("d", DIRS)
def test_dir_has_readme(d):
    assert (REPO / d / "README.md").is_file(), f"{d}/README.md"


@pytest.mark.parametrize("sub", SUBPACKAGES)
def test_core_subpackage_importable(sub):
    assert (REPO / "core" / "linumert" / sub / "README.md").is_file()
    importlib.import_module(f"linumert.{sub}")


def test_packages_importable():
    import linumert

    assert linumert.__version__
    importlib.import_module("linumert_sim")
    importlib.import_module("linumert_plant")


def test_gitignore_has_binary_and_state_entries():
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").split()
    for entry in ("*.qcow2", "*.img", "*.vdi", "*.TGZ", "/state/"):
        assert entry in lines or entry.rstrip("/") in lines, entry
