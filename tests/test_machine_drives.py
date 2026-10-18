"""Napędy w machine.yaml: instancje szablonów z biblioteki (REQ-VD-02, REQ-VD-03).

Model-Author: Claude · sesja 013.
"""

from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from linumert.machine.schema import MachineConfigError, parse_machine
from linumert_plant.drive_library import load_library
from linumert_plant.machine_drives import load_machine_drives, resolve_machine_drives

ROOT = Path(__file__).resolve().parents[1]
MACHINES = sorted((ROOT / "config" / "machines").glob("*.yaml"))
BASE = ROOT / "config" / "machines" / "router_gantry_steppers.yaml"


@pytest.fixture(scope="module")
def library() -> dict[str, dict]:
    return load_library()


@pytest.fixture()
def data() -> dict:
    return yaml.safe_load(BASE.read_text(encoding="utf-8"))


def _errors(data: dict, library: dict[str, dict]) -> list[str]:
    with pytest.raises(MachineConfigError) as exc:
        resolve_machine_drives(parse_machine(data), library)
    return exc.value.errors


@pytest.mark.parametrize("path", MACHINES, ids=lambda p: p.stem)
def test_example_machines_resolve_drives(path: Path) -> None:
    # REQ-VD-02: każda przykładowa maszyna składa się z instancji szablonów biblioteki
    cfg, drives = load_machine_drives(path)
    assert list(drives) == [d.name for d in cfg.drives]
    for inst in drives.values():
        assert inst.params["id"] == inst.template_id


def test_machine_overrides_inherit_and_stay_local(library: dict[str, dict]) -> None:
    # REQ-VD-02: nadpisanie zmienia tylko instancję; reszta dziedziczona z szablonu
    _cfg, drives = load_machine_drives(BASE)
    z, x = drives["drv_z"], drives["drv_x"]
    assert z.overrides == {"mechanics.load": 15.0}
    assert z.params["mechanics"]["load"] == 15.0
    tpl = library["stepper_nema23_3nm"]
    assert x.params["mechanics"]["load"] == tpl["mechanics"]["load"] != 15.0
    assert z.params["motor"] == tpl["motor"]


def test_machine_drive_id_and_legacy_name_keys(data: dict, library: dict[str, dict]) -> None:
    # REQ-VD-02: klucz `id` (format sesji 013) i `name` (sesja 010) oznaczają to samo
    legacy = copy.deepcopy(data)
    for entry in legacy["drives"]:
        entry["name"] = entry.pop("id")
    a = resolve_machine_drives(parse_machine(data), library)
    b = resolve_machine_drives(parse_machine(legacy), library)
    assert {k: v.params for k, v in a.items()} == {k: v.params for k, v in b.items()}


def test_machine_overrides_validated_with_template_ranges(data: dict,
                                                          library: dict[str, dict]) -> None:
    # REQ-VD-02: błędne nadpisanie w machine.yaml → komunikat ze ścieżką w pliku
    data["drives"][1]["overrides"] = {"mechanics": {"load": -5}}
    data["drives"][2]["overrides"] = {"motor": {"bogus": 1}}
    errors = _errors(data, library)
    assert any(e.startswith("drives[1].overrides.mechanics.load:") for e in errors), errors
    assert any(e.startswith("drives[2].overrides.motor.bogus:") for e in errors), errors


def test_machine_unknown_template_keeps_file_indices(data: dict,
                                                     library: dict[str, dict]) -> None:
    # REQ-VD-02: nieznany szablon i błędne nadpisanie dalej — indeksy jak w pliku
    data["drives"][0]["template"] = "nie_ma_takiego"
    data["drives"][3]["overrides"] = {"mechanics": {"load": "dużo"}}
    errors = _errors(data, library)
    assert any("drives[0].template: brak szablonu nie_ma_takiego" in e for e in errors), errors
    assert any(e.startswith("drives[3].overrides.mechanics.load:") for e in errors), errors


def test_machine_drive_kind_must_match_axis(data: dict, library: dict[str, dict]) -> None:
    # REQ-VD-02: oś liniowa wymaga mechaniki linear, wrzeciono — rotary
    for entry in data["drives"]:
        if entry["id"] == "drv_x":
            entry["template"] = "rotary_table_worm_1_90"
        if entry["id"] == "drv_spindle":
            entry["template"] = "servo_400w"
    errors = _errors(data, library)
    assert any(e.startswith("axes[0].drives: napęd drv_x") and "wymaga linear" in e
               for e in errors), errors
    assert any(e.startswith("spindle.drive: napęd drv_spindle") for e in errors), errors


def test_python_m_plant_drive_clone(tmp_path: Path, library: dict[str, dict]) -> None:
    # REQ-VD-03: `python -m plant drive clone` z katalogu głównego (szablon i instancja)
    lib = tmp_path / "lib"
    lib.mkdir()
    src = ROOT / "plant" / "library" / "drives" / "servo_400w.yaml"
    (lib / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-m", "plant", "drive", "--dir", str(lib), *args],
                              cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                              check=False)

    done = run("clone", "servo_400w", "servo_400w_ciezki")
    assert done.returncode == 0, done.stderr
    clone = yaml.safe_load((lib / "servo_400w_ciezki.yaml").read_text(encoding="utf-8"))
    assert clone["based_on"] == "servo_400w" and clone["version"] == 1

    machine = tmp_path / "m.yaml"
    machine.write_text(yaml.safe_dump({"drives": [
        {"id": "X1", "template": "servo_400w", "overrides": {"mechanics": {"load": 120.0}}}]}),
        encoding="utf-8")
    done = run("clone", "X1", "servo_x1", "--machine", str(machine))
    assert done.returncode == 0, done.stderr
    baked = yaml.safe_load((lib / "servo_x1.yaml").read_text(encoding="utf-8"))
    assert baked["mechanics"]["load"] == 120.0 and baked["based_on"] == "servo_400w"
    original = yaml.safe_load(src.read_text(encoding="utf-8"))
    assert original["mechanics"]["load"] == library["servo_400w"]["mechanics"]["load"]

    bad = run("instances", str(machine))
    assert bad.returncode == 1 and "Błąd" in bad.stderr
