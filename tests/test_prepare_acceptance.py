"""Odbiór poziomu 1: `linumert-lite prepare` (docs/roadmap/LITE_VERTICAL.md).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-11-05

Test odbioru pisany przed implementacją (podział: Codex kod, Claude odbiór). Dopóki CLI nie ma
podpolecenia `prepare`, moduł jest pomijany; po dodaniu polecenia wszystkie testy muszą przejść.

Kontrakt, który sprawdzamy (z LITE_VERTICAL.md, poziom 1):

    linumert-lite prepare PART.lnx --machine MACHINE.yaml --tools TOOLS.sqlite --out JOB

- Sukces: kod 0, katalog JOB z G-code (`*.ngc`), `tool.tbl`, kopią programu (`*.lnx`) i maszyny
  (`*.yaml`), raportem `report.json` i `manifest.json`. Manifest: `format_version` (int) oraz
  `files` = {ścieżka względna: sha256} dla **każdego** pliku pakietu poza samym manifestem.
- Raport: `status == "prepared"`, `checks` = lista {`id`, `result`}, wynik z {pass, not_run};
  co najmniej jedna kontrola `not_run` (limity toru wymagają interpretera — poziom 2).
- Odrzucenie: kod 2, konkretna przyczyna na stderr z kodem alarmu P-xxxx (gdy jest w katalogu)
  i treścią z katalogu (numer narzędzia, pole, wartość); wszystkie przyczyny naraz. JOB nie
  powstaje, źródła i baza narzędzi bajt w bajt bez zmian. Istniejący JOB nie jest nadpisywany.
- Te same wejścia → identyczne pliki i sumy kontrolne.

Nazwy plików poza `manifest.json`, `report.json`, `tool.tbl` są dowolne.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path

import pytest
from linumert.cli import main, registry
from linumert.programs.compiler import CompileError, compile_program
from linumert.programs.lnx import parse_lnx
from linumert.tools.db import Tool, ToolDB

ROOT = Path(__file__).resolve().parents[1]
MACHINE = ROOT / "config" / "machines" / "mill_servo_table.yaml"   # spindle.max_rpm = 8000


def _has_prepare() -> bool:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            main(["prepare", "--help"])
        except SystemExit as exc:
            return exc.code == 0
    return True


needs_prepare = pytest.mark.skipif(not _has_prepare(),
                                reason="linumert-lite prepare jeszcze nie istnieje (Codex)")

TOOLS = (
    Tool(1, 1, "flat", "Frez 6 mm", params={"d": 6.0, "l": 50.0, "flute_length": 20.0,
                                           "max_rpm": 10000}, offsets={"Z": 50.0}),
    Tool(2, 2, "drill_118", "Wiertło 3 mm", params={"d": 3.0, "l": 40.0, "flute_length": 20.0},
         offsets={"Z": 40.0}),
)

# Detal odbioru: planowanie + kieszeń + wiercenie (kryterium właściciela).
PART = {
    "schema_version": 1, "name": "Odbiór prepare", "units": "mm",
    "steps": [
        {"generator": "header", "version": 1, "params": {"title": "Odbior prepare",
                                                         "units": "G21"}},
        {"generator": "tool_change", "version": 1, "params": {"tool": 1, "rpm": 6000}},
        {"generator": "face_mill", "version": 1,
         "params": {"x0": 0, "y0": 0, "x1": 60, "y1": 40, "depth": 0.5, "step_down": 0.5,
                    "tool_d": 6}},
        {"generator": "pocket_rect", "version": 2,
         "params": {"cx": 30, "cy": 20, "z_top": -0.5, "width": 30, "height": 16, "depth": 3,
                    "step_down": 1, "tool_d": 6}},
        {"generator": "tool_change", "version": 1, "params": {"tool": 2, "rpm": 3000}},
        {"generator": "drill_holes", "version": 1,
         "params": {"pattern": "list", "points": "8,8; 52,8; 52,32; 8,32", "z_top": -0.5,
                    "depth": 5, "cycle": "G81"}},
        {"generator": "program_end", "version": 1, "params": {}},
    ],
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs(tmp_path: Path, part: dict | None = None, tools=TOOLS) -> dict[str, Path]:
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    program = src / "part.lnx"
    program.write_text(json.dumps(part or PART, ensure_ascii=False, indent=2), encoding="utf-8")
    parse_lnx(json.loads(program.read_text(encoding="utf-8")))   # detal odbioru jest poprawnym .lnx
    db = src / "tools.sqlite"
    with ToolDB(db) as handle:
        for tool in tools:
            handle.add(tool, source="test")
    return {"program": program, "machine": MACHINE, "tools": db, "out": tmp_path / "job"}


def _prepare(paths: dict[str, Path], capsys) -> tuple[int, str]:
    code = main(["prepare", str(paths["program"]), "--machine", str(paths["machine"]),
                 "--tools", str(paths["tools"]), "--out", str(paths["out"])])
    return code, capsys.readouterr().err


def _snapshot(paths: dict[str, Path]) -> dict[str, str]:
    return {name: _sha(paths[name]) for name in ("program", "machine", "tools")}


def _manifest(job: Path) -> dict:
    return json.loads((job / "manifest.json").read_text(encoding="utf-8"))


# --- sukces ---------------------------------------------------------------------------------

@needs_prepare
def test_one_command_builds_complete_package(tmp_path, capsys):
    paths = _inputs(tmp_path)
    before = _snapshot(paths)
    code, err = _prepare(paths, capsys)
    assert code == 0, err
    job = paths["out"]

    manifest = _manifest(job)
    assert isinstance(manifest.get("format_version"), int)
    files = manifest["files"]
    on_disk = {p.relative_to(job).as_posix() for p in job.rglob("*")
               if p.is_file() and p.name != "manifest.json"}
    assert set(files) == on_disk, "manifest musi opisywać każdy plik pakietu"
    for name, digest in files.items():
        assert _sha(job / name) == digest, name

    suffixes = {Path(name).suffix for name in files}
    assert {".ngc", ".lnx", ".yaml"} <= suffixes
    assert "tool.tbl" in {Path(name).name for name in files}
    assert "report.json" in {Path(name).name for name in files}
    assert _snapshot(paths) == before, "źródła i baza narzędzi bez zmian"


@needs_prepare
def test_gcode_matches_compile_and_covers_all_operations(tmp_path, capsys):
    paths = _inputs(tmp_path)
    assert _prepare(paths, capsys)[0] == 0
    job = paths["out"]
    (ngc,) = [job / n for n in _manifest(job)["files"] if n.endswith(".ngc")]
    gcode = ngc.read_text(encoding="utf-8")

    reference = tmp_path / "reference.ngc"
    assert main(["compile", str(paths["program"]), "--out", str(reference)]) == 0
    capsys.readouterr()
    assert gcode == reference.read_text(encoding="utf-8"), "prepare = ten sam kompilator"

    for word in ("G21", "T1 M6", "G43 H1", "S6000 M3", "T2 M6", "G43 H2", "G81", "M2"):
        assert word in gcode, word
    assert gcode.rstrip().endswith("M2")


@needs_prepare
def test_tool_table_lists_used_tools_in_machine_units(tmp_path, capsys):
    paths = _inputs(tmp_path)
    assert _prepare(paths, capsys)[0] == 0
    rows = [line.split(";")[0].split() for line in
            (paths["out"] / "tool.tbl").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith(";")]
    table = {row[0]: {w[0]: float(w[1:]) for w in row[1:] if w[0] in "DZ"} for row in rows}
    assert table["T1"] == {"D": 6.0, "Z": 50.0}
    assert table["T2"] == {"D": 3.0, "Z": 40.0}


@needs_prepare
def test_report_does_not_claim_interpreter_checks(tmp_path, capsys):
    paths = _inputs(tmp_path)
    assert _prepare(paths, capsys)[0] == 0
    files = _manifest(paths["out"])["files"]
    (name,) = [n for n in files if Path(n).name == "report.json"]
    report = json.loads((paths["out"] / name).read_text(encoding="utf-8"))
    assert report["status"] == "prepared"
    results = {c["id"]: c["result"] for c in report["checks"]}
    assert set(results.values()) <= {"pass", "not_run"}, results
    assert "not_run" in results.values(), "limity toru = poziom 2 (rs274), nie pass"


@needs_prepare
def test_same_inputs_give_identical_package(tmp_path, capsys):
    first = _inputs(tmp_path)
    assert _prepare(first, capsys)[0] == 0
    second = dict(first, out=tmp_path / "job2")
    assert _prepare(second, capsys)[0] == 0
    assert _manifest(first["out"]) == _manifest(second["out"])


@needs_prepare
def test_existing_package_is_not_overwritten(tmp_path, capsys):
    paths = _inputs(tmp_path)
    assert _prepare(paths, capsys)[0] == 0
    manifest = (paths["out"] / "manifest.json").read_bytes()
    code, err = _prepare(paths, capsys)
    assert code == 2 and err.strip()
    assert (paths["out"] / "manifest.json").read_bytes() == manifest


# --- odrzucenia: konkretne przyczyny ---------------------------------------------------------

def _step(part: dict, generator: str, index: int = 0) -> dict:
    return [s for s in part["steps"] if s["generator"] == generator][index]["params"]


def _missing_tool(part):
    return part, TOOLS[:1]


def _wrong_diameter(part):
    _step(part, "pocket_rect")["tool_d"] = 10
    return part, TOOLS


def _header_units(part):
    _step(part, "header")["units"] = "G20"      # program zadeklarowany w mm
    return part, TOOLS


def _machine_rpm(part):
    _step(part, "tool_change")["rpm"] = 9000    # maszyna 8000, narzędzie 10000
    return part, TOOLS


def _tool_rpm(part):
    tools = (Tool(1, 1, "flat", params={"d": 6.0, "l": 50.0, "flute_length": 20.0,
                                        "max_rpm": 5000}, offsets={"Z": 50.0}), TOOLS[1])
    return part, tools


def _bad_geometry(part):
    _step(part, "face_mill")["x1"] = -10        # x1 <= x0
    return part, TOOLS


def _unknown_version(part):
    part["steps"][3]["version"] = 999
    return part, TOOLS


REJECTIONS = {
    # przypadek: (modyfikacja, fragmenty wymagane na stderr)
    "brak_narzedzia_T2": (_missing_tool, ("P-5206", "T2")),
    "srednica_kieszeni": (_wrong_diameter, ("P-5208", "T1", "D = 6 mm")),
    "jednostki_naglowka": (_header_units, ("G20", "mm")),
    "obroty_maszyny": (_machine_rpm, ("9000", "8000")),
    "obroty_narzedzia": (_tool_rpm, ("P-5210", "T1", "5000")),
    "geometria_planowania": (_bad_geometry, ("P-5003", "x1")),
    "wersja_generatora": (_unknown_version, ("P-5011", "999")),
}


@needs_prepare
@pytest.mark.parametrize("case", sorted(REJECTIONS))
def test_faulty_job_is_rejected_with_reason(case, tmp_path, capsys):
    mutate, expected = REJECTIONS[case]
    part, tools = mutate(copy.deepcopy(PART))
    paths = _inputs(tmp_path, part, tools)
    before = _snapshot(paths)
    code, err = _prepare(paths, capsys)
    assert code == 2, f"{case}: oczekiwano odrzucenia, stderr={err!r}"
    for fragment in expected:
        assert fragment in err, f"{case}: brak {fragment!r} w {err!r}"
    assert "Traceback" not in err
    assert not paths["out"].exists(), "pakiet nie powstaje przy odrzuceniu"
    assert _snapshot(paths) == before, "źródła i baza bez zmian także przy błędzie"


@needs_prepare
def test_all_reasons_are_reported_at_once(tmp_path, capsys):
    part = copy.deepcopy(PART)
    _step(part, "pocket_rect")["tool_d"] = 10
    _step(part, "face_mill")["x1"] = -10
    paths = _inputs(tmp_path, part, TOOLS[:1])
    code, err = _prepare(paths, capsys)
    assert code == 2
    for fragment in ("P-5206", "P-5208", "P-5003"):
        assert fragment in err, fragment


@needs_prepare
def test_missing_tool_database_is_not_created(tmp_path, capsys):
    paths = _inputs(tmp_path)
    paths["tools"] = tmp_path / "src" / "brak.sqlite"
    code, err = _prepare(paths, capsys)
    assert code == 2 and "brak.sqlite" in err
    assert not paths["tools"].exists(), "baza otwierana tylko do odczytu, bez tworzenia"
    assert not paths["out"].exists()


# --- dane odbioru: sprawdzalne już dziś, bez prepare ----------------------------------------

def _compile(part: dict, tools) -> str:
    program = parse_lnx(copy.deepcopy(part))
    by_number = {tool.number: tool for tool in tools}
    return compile_program(program, registry(), tools=by_number.get)


def test_acceptance_part_compiles_with_its_tools():
    gcode = _compile(PART, TOOLS)
    for word in ("T1 M6", "T2 M6", "G81", "M2"):
        assert word in gcode


# Przyczyny, które kompilator zgłasza już dziś; prepare ma je przekazać bez zmian.
COMPILER_CASES = ("brak_narzedzia_T2", "srednica_kieszeni", "obroty_narzedzia",
                  "geometria_planowania", "wersja_generatora")
# Przyczyny nowe w prepare (dziś kompilator je przepuszcza).
PREPARE_CASES = ("jednostki_naglowka", "obroty_maszyny")


@pytest.mark.parametrize("case", COMPILER_CASES)
def test_compiler_already_rejects(case):
    mutate, expected = REJECTIONS[case]
    part, tools = mutate(copy.deepcopy(PART))
    with pytest.raises(CompileError) as info:
        _compile(part, tools)
    codes = [issue.code for issue in info.value.issues]
    assert expected[0] in codes, (case, codes, str(info.value))
    for fragment in expected[1:]:
        assert fragment in str(info.value), (case, fragment, str(info.value))


@pytest.mark.parametrize("case", PREPARE_CASES)
def test_new_prepare_checks_are_not_yet_in_compiler(case):
    # Gdy kompilator zacznie je odrzucać, przenieś przypadek do COMPILER_CASES.
    mutate, _ = REJECTIONS[case]
    part, tools = mutate(copy.deepcopy(PART))
    _compile(part, tools)

