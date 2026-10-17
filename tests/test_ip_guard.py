"""Straznik IP (CLAUDE.md §7): nazwy producentow sterowan poza docs/prawne/ i docs/."""

import re

from conftest import REPO

NAMES_FILE = REPO / "docs" / "prawne" / "ZAKAZANE_NAZWY.txt"
SKIP_DIRS = {".git", ".venv", "node_modules", ".pytest_cache", ".ruff_cache", "__pycache__"}
# Wyjatki z CLAUDE.md §7: docs/prawne/ oraz rzeczowe porownania w dokumentacji (docs/).
ALLOWED_PREFIXES = ("docs/prawne/", "docs/")
TEXT_SUFFIXES = {
    ".py", ".c", ".h", ".comp", ".hal", ".ini", ".yaml", ".yml", ".toml", ".ui", ".qss",
    ".txt", ".json", ".sh", ".md", ".cfg", ".tbl", "",
}


def forbidden_names():
    names = []
    for line in NAMES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().lower()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def _files():
    for path in REPO.rglob("*"):
        rel = path.relative_to(REPO)
        if path.is_file() and not (SKIP_DIRS & set(rel.parts)):
            yield path, rel.as_posix()


def _pattern(names):
    return re.compile("|".join(re.escape(n) for n in names), re.IGNORECASE)


def test_names_list_is_present():
    assert len(forbidden_names()) >= 10


def test_no_forbidden_names_in_file_names():
    pattern = _pattern(forbidden_names())
    bad = [
        rel for _, rel in _files()
        if not rel.startswith("docs/prawne/") and pattern.search(rel)
    ]
    assert not bad, f"nazwy producentow w nazwach plikow: {bad}"


def test_no_forbidden_names_in_code_and_ui():
    pattern = _pattern(forbidden_names())
    bad = []
    for path, rel in _files():
        if rel.startswith(ALLOWED_PREFIXES) or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
            bad.append(rel)
    assert not bad, f"nazwy producentow w kodzie/UI/konfiguracji: {bad}"


def test_provenance_registry_exists_and_covers_design():
    text = (REPO / "docs" / "PROVENANCE.md").read_text(encoding="utf-8")
    assert "docs/design/ikony" in text
    assert "docs/design/marka" in text
    assert "LICENSE" in text
