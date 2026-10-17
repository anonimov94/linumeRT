"""Licencja projektu: GPL-2.0, bez licencji "Paid Reuse" z katalogu nadrzednego (D14)."""

import tomllib

from conftest import REPO

LICENSE_NAMES = ("license", "licence", "copying", "unlicense")
SKIP_DIRS = {".git", ".venv", "node_modules", ".pytest_cache", ".ruff_cache", "__pycache__"}


def _license_like_files():
    for path in REPO.rglob("*"):
        if not path.is_file() or SKIP_DIRS & set(path.relative_to(REPO).parts):
            continue
        stem = path.name.lower().split(".")[0]
        if stem in LICENSE_NAMES:
            yield path


def test_license_is_gpl2():
    text = (REPO / "LICENSE").read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in text
    assert "Version 2, June 1991" in text


def test_no_paid_reuse_license_file():
    found = list(_license_like_files())
    assert found, "brak pliku LICENSE"
    for path in found:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        assert "paid reuse" not in text, f"{path} zawiera licencje Paid Reuse (niezgodna z GPL)"
        assert "source-available" not in text, f"{path}: licencja source-available niezgodna z GPL"


def test_pyproject_declares_gpl():
    meta = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert meta["license"]["text"] == "GPL-2.0-or-later"
    assert not any("paid" in c.lower() for c in meta.get("classifiers", []))


def test_readme_declares_license():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "GPL-2.0-or-later dla własnego kodu" in readme
    assert "Szybki start" in readme


def test_dependencies_listed_in_licences_doc():
    meta = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    doc = (REPO / "docs" / "LICENCJE.md").read_text(encoding="utf-8").lower()
    deps = list(meta["dependencies"]) + list(meta["optional-dependencies"]["dev"])
    for dep in deps:
        assert dep.lower() in doc, f"zaleznosc {dep} bez wpisu w docs/LICENCJE.md"
