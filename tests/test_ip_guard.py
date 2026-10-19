"""Straznik IP (CLAUDE.md §7, docs/prawne/PROCES.md).

Nazwy producentow (docs/prawne/ZAKAZANE_NAZWY.txt) i slowa zakazane (docs/SLOWNIK.md) nie wystepuja
w kodzie, UI, konfiguracji ani nazwach plikow. Wyjatki: docs/prawne/ oraz docs/
(rzeczowe porownania).
"""

import re

from conftest import REPO

NAMES_FILE = REPO / "docs" / "prawne" / "ZAKAZANE_NAZWY.txt"
GLOSSARY = REPO / "docs" / "SLOWNIK.md"
PROVENANCE = REPO / "docs" / "PROVENANCE.md"
SKIP_DIRS = {".git", ".venv", "node_modules", ".pytest_cache", ".ruff_cache", "__pycache__",
             "build"}  # build/ = wyniki lokalne (gitignore), np. zrzuty tools/dev/sim-e2e.sh
SKIP_SUFFIXES = (".egg-info",)
# Skanowane drzewa (kod, UI, konfiguracja) oraz pliki w korzeniu repozytorium.
SCAN_DIRS = (
    "core", "simulation", "screens", "plant", "hal", "config", "tools", "tests", "community",
)
TEXT_SUFFIXES = {
    ".py", ".c", ".h", ".comp", ".hal", ".ini", ".yaml", ".yml", ".toml", ".ui", ".qss",
    ".txt", ".json", ".sh", ".md", ".cfg", ".tbl", ".html", ".js", ".css", ".svg", ".lnx", "",
}
BINARY_ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".ico", ".ttf", ".otf",
                         ".woff", ".woff2", ".pdf"}


def forbidden_names():
    names = []
    for line in NAMES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().lower()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def forbidden_words():
    """Slowa zakazane z bloku ```zakazane w SLOWNIK.md (format: 'slowo -> zamiennik')."""
    text = GLOSSARY.read_text(encoding="utf-8")
    block = re.search(r"```zakazane\n(.*?)```", text, re.S)
    assert block, "brak bloku ```zakazane w docs/SLOWNIK.md"
    words = []
    for line in block.group(1).splitlines():
        if "->" in line:
            words.append(line.split("->")[0].strip())
    return words


def _files():
    for path in REPO.rglob("*"):
        rel = path.relative_to(REPO)
        if not path.is_file() or SKIP_DIRS & set(rel.parts):
            continue
        if any(part.endswith(SKIP_SUFFIXES) for part in rel.parts):
            continue
        yield path, rel.as_posix()


def _in_scope(rel):
    if rel.startswith(("docs/prawne/", "docs/")):
        return False
    return "/" not in rel or rel.split("/")[0] in SCAN_DIRS


def _name_pattern(names):
    return re.compile("|".join(re.escape(n) for n in names), re.IGNORECASE)


def _word_pattern(words):
    alternatives = "|".join(re.escape(w) for w in words)
    return re.compile(rf"(?<!\w)({alternatives})(?!\w)", re.IGNORECASE)


def _scan(pattern, skip=()):
    bad = []
    for path, rel in _files():
        if rel in skip or not _in_scope(rel) or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
            bad.append(rel)
    return bad


def test_lists_are_present():
    assert len(forbidden_names()) >= 10
    assert len(forbidden_words()) >= 5


def test_no_forbidden_names_in_file_names():
    pattern = _name_pattern(forbidden_names())
    bad = [rel for _, rel in _files() if not rel.startswith("docs/prawne/") and pattern.search(rel)]
    assert not bad, f"nazwy producentow w nazwach plikow: {bad}"


def test_no_forbidden_names_in_code_and_ui():
    bad = _scan(_name_pattern(forbidden_names()))
    assert not bad, f"nazwy producentow w kodzie/UI/konfiguracji: {bad}"


def test_no_forbidden_words_in_code_and_ui():
    bad = _scan(_word_pattern(forbidden_words()))
    assert not bad, f"slowa zakazane (docs/SLOWNIK.md) w kodzie/UI/konfiguracji: {bad}"


def test_forbidden_words_have_replacements():
    text = GLOSSARY.read_text(encoding="utf-8")
    block = re.search(r"```zakazane\n(.*?)```", text, re.S).group(1)
    for line in block.splitlines():
        if line.strip():
            word, _, repl = line.partition("->")
            assert repl.strip(), f"brak zamiennika dla: {word.strip()}"


def test_no_references_to_earlier_materials():
    """Brak odwolan do wczesniejszych materialow projektu (nazwy koncepcji, katalog nadrzedny)."""
    pattern = re.compile(r"projekt_hmi|PythonProjects|\bAPEX\b")
    # README.md i CLAUDE.md wprost zaznaczaja, ze licencja katalogu nadrzednego nie obowiazuje.
    bad = _scan(pattern, skip=("README.md", "CLAUDE.md", "tests/test_ip_guard.py"))
    assert not bad, f"odwolania do wczesniejszych materialow: {bad}"


def test_images_and_fonts_only_with_provenance():
    """Grafiki/fonty mają wpis w PROVENANCE.md; obrazy w docs/design, docs/raporty, screens."""
    text = PROVENANCE.read_text(encoding="utf-8")
    missing, misplaced = [], []
    for path, rel in _files():
        if rel.startswith("docs/prawne/"):
            continue
        if path.suffix.lower() in BINARY_ASSET_SUFFIXES:
            if f"`{rel}`" not in text:
                missing.append(rel)
            if not rel.startswith(("docs/design/", "docs/raporty/", "screens/", "fonts/",
                                   "plant/server/")):
                misplaced.append(rel)
    assert not missing, f"zasoby bez wpisu w docs/PROVENANCE.md: {missing}"
    assert not misplaced, f"obrazy/fonty w niedozwolonym miejscu: {misplaced}"


def test_provenance_covers_every_design_file():
    text = PROVENANCE.read_text(encoding="utf-8")
    missing = [
        rel for _, rel in _files()
        if rel.startswith("docs/design/") and f"`{rel}`" not in text
    ]
    assert not missing, f"pliki docs/design bez wpisu w PROVENANCE.md: {missing}"


def test_provenance_table_columns():
    header = next(
        line for line in PROVENANCE.read_text(encoding="utf-8").splitlines()
        if line.startswith("| Zasób")
    )
    cols = [c.strip() for c in header.strip("|").split("|")]
    expected = ["Zasób", "Typ", "Autor", "Data", "Źródło", "Licencja", "Zakres użycia", "Ścieżka"]
    assert cols == expected


def test_ip_process_docs_exist():
    for rel in ("docs/prawne/PROCES.md", "docs/prawne/LISTA_PRZED_WYDANIEM.md", "docs/SLOWNIK.md"):
        assert (REPO / rel).is_file(), rel
    checklist = (REPO / "docs/prawne/LISTA_PRZED_WYDANIEM.md").read_text(encoding="utf-8")
    assert checklist.count("| [ ] |") == 8
