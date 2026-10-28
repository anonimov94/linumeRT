# SPDX-License-Identifier: GPL-2.0-or-later
"""Generator INI/HAL z machine.yaml (sesja 062): golden względem sprawdzonej konfiguracji Plant.

Model-Author: Claude · 2026-10-24. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

from linumert.machine.configgen import render
from linumert.machine.schema import load_machine

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
PLANT_DIR = ROOT / "config/plant/linumert_plant_xyz"
MACHINES = sorted((ROOT / "config/machines").glob("*.yaml"))


def ini_entries(text: str) -> list[tuple[str, str, str]]:
    """(sekcja, klucz, wartość) w kolejności pliku; komentarze i puste linie pominięte."""
    section, out = "", []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            section = line.strip("[]")
            continue
        key, _, value = line.partition("=")
        out.append((section, key.strip(), value.strip()))
    return out


def hal_statements(*texts: str) -> Counter:
    """Instrukcje HAL bez komentarzy, z ujednoliconymi odstępami (multizbiór)."""
    out: Counter = Counter()
    for text in texts:
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if line:
                out[" ".join(line.split())] += 1
    return out


@pytest.fixture(scope="module")
def plant_files():
    return render(load_machine(MILL), "plant")


def test_plant_ini_equals_verified_config(plant_files):
    generated = ini_entries(plant_files["mill_servo_table.ini"])
    reference = ini_entries((PLANT_DIR / "linumert_plant_xyz.ini").read_text(encoding="utf-8"))
    # Nazwa maszyny w [EMC] jedyną różnicą jest dopuszczalna tylko co do tekstu opisu.
    gen = [e for e in generated if e[:2] != ("EMC", "MACHINE")]
    ref = [e for e in reference if e[:2] != ("EMC", "MACHINE")]
    assert gen == ref


def test_plant_hal_equals_verified_config(plant_files):
    generated = hal_statements(plant_files["linumert_plant.hal"], plant_files["spindle_sim.hal"])
    reference = hal_statements((PLANT_DIR / "linumert_plant.hal").read_text(encoding="utf-8"),
                               (PLANT_DIR / "spindle_sim.hal").read_text(encoding="utf-8"))
    assert generated == reference


@pytest.mark.parametrize("path", MACHINES, ids=lambda p: p.stem)
@pytest.mark.parametrize("target", ["plant", "sim"])
def test_every_example_machine_generates_d05_contract(path, target):
    cfg = load_machine(path)
    files = render(cfg, target)
    ini = files[f"{cfg.machine.name}.ini"]
    hal = "\n".join(t for n, t in files.items() if n.endswith(".hal"))
    entries = ini_entries(ini)
    joints = int(next(v for s, k, v in entries if (s, k) == ("KINS", "JOINTS")))
    # W bliźniaku bez GUI ekranem jest usługa headless — nie qtvcp (Qt usunięte).
    assert ("DISPLAY", "DISPLAY", "linumert_headless") in entries
    assert joints == sum(len(a.drives) for a in cfg.axes)
    for j in range(joints):
        for sig in ("pos-cmd", "pos-fb", "enable", "fault"):
            assert re.search(rf"^net linumert\.j{j}\.{sig}\s", hal, re.M), (j, sig)
        assert any(s == f"JOINT_{j}" for s, _, _ in entries)
    assert "linumert.io.estop-ok" in hal and "iocontrol.0.emc-enable-in" in hal
    assert "linumert.hmi.estop-ok" in hal
    for name in ("linumert.spindle.on", "linumert.spindle.speed-cmd", "linumert.spindle.revs"):
        assert name in hal
    # Każda oś ma czujnik bazy podłączony do jointów (wspólny dla bramy).
    for a in cfg.axes:
        if a.home_sensor is not None and a.home_sensor.shared_with:
            for j in range(joints):
                section = dict((k, v) for s, k, v in entries if s == f"JOINT_{j}")
                if section["AXIS"] == a.letter:
                    assert f"joint.{j}.home-sw-in" in hal, (a.letter, j)


def test_unknown_target():
    with pytest.raises(ValueError, match="nieznany cel"):
        render(load_machine(MILL), "laptop")
