"""Baza narzędzi (sesja 032): typy, walidacja, SQLite z historią, tool.tbl i CSV.

Model-Author: Claude
Test z markerem `linuxcnc`: tool.tbl z bazy czyta prawdziwy interpreter LinuxCNC 2.9 (rs274),
a G43 bierze z niego długość narzędzia.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

import pytest
from linumert.tools.db import MIGRATIONS, Tool, ToolDB, ToolDBError
from linumert.tools.tbl import TblEntry, ToolTableError, format_tbl, parse_tbl
from linumert.tools.types import TYPES, validate_geometry

SAMPLE_TBL = """\
; tabela przykładowa
T1 P1 Z0.511 D0.125 ;1/8 end mill
T2 P2 Z0.1 D0.0625 ;1/16 end mill
T3 P3 Z1.273 D0.201 ;#7 tap drill
T99999 P99999 Z0.1 ;big tool number
T4 P4 Z0 D.005 ;Added 20131029
"""
LATHE_TBL = "T7 P17 X1.5 Z-2.25 D0.8 I95 J155 Q3 ;tokarski\nT8 P0 Z10 D6 X0 Y0\n"


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        self.t += 1.0
        return self.t


@pytest.fixture
def db():
    with ToolDB(":memory:", clock=Clock()) as base:
        yield base


def _flat(number=1, pocket=1, **params) -> Tool:
    geometry = {"d": 6.0, "l": 40.0, "flute_length": 15.0}
    geometry.update(params)
    return Tool(number, pocket, type="flat", description="frez 6 mm", params=geometry,
                offsets={"Z": 52.3})


# ---- typy ----------------------------------------------------------------------------------


def test_all_types_from_requirements():
    assert set(TYPES) == {"flat", "ball", "bull", "tslot", "lollipop", "chamfer", "drill_118",
                          "drill_angle", "face_mill", "tap", "special_stl"}


@pytest.mark.parametrize("type_id,params", [
    ("flat", {"d": 6, "l": 40, "flute_length": 15}),
    ("ball", {"d": 6, "l": 40}),
    ("bull", {"d": 10, "l": 50, "corner_radius": 1}),
    ("tslot", {"d": 20, "width": 5, "neck_d": 8, "neck_l": 15}),
    ("lollipop", {"d": 6, "neck_d": 3, "neck_l": 20}),
    ("chamfer", {"d": 10, "angle": 90}),
    ("drill_118", {"d": 5, "l": 60}),
    ("drill_angle", {"d": 5, "angle": 180}),
    ("face_mill", {"d": 50, "h": 40}),
])
def test_valid_geometry_per_type(type_id, params):
    assert validate_geometry(1, type_id, params, None) == []


@pytest.mark.parametrize("type_id,params,bad", [
    ("flat", {"d": 6, "l": 40}, "flute_length"),                       # brak wymaganego
    ("flat", {"d": 6, "l": 40, "flute_length": 50}, "flute_length"),   # ostrze dłuższe niż L
    ("bull", {"d": 10, "l": 50, "corner_radius": 6}, "corner_radius"),  # R > D/2
    ("tslot", {"d": 8, "width": 5, "neck_d": 8, "neck_l": 15}, "neck_d"),
    ("chamfer", {"d": 10, "angle": 180}, "angle"),
    ("drill_angle", {"d": 5, "angle": 190}, "angle"),                   # kąt ≤ 180°
    ("ball", {"d": 6, "l": 40, "angle": 10}, "angle"),                  # pole spoza typu
    ("ball", {"d": -6, "l": 40}, "d"),
    ("ball", {"d": "6", "l": 40}, "d"),
    ("special_stl", {}, "stl"),
])
def test_invalid_geometry(type_id, params, bad):
    issues = validate_geometry(3, type_id, params, None)
    assert issues and issues[0].field == bad and issues[0].code == "P-5201"
    assert issues[0].message().startswith("Narzędzie T3: pole")


def test_unknown_type_and_missing_type_warning():
    issues = validate_geometry(5, "laser", {}, None)
    assert [i.code for i in issues] == ["P-5205"]
    tool = Tool(5, 5)
    assert tool.validate() == []
    assert [w.code for w in tool.warnings()] == ["K-320"]
    assert tool.warnings()[0].message() == "Narzędzie T5 nie ma geometrii; użyto walca zastępczego."


# ---- tool.tbl ------------------------------------------------------------------------------


def test_tbl_roundtrip_without_loss():
    for text in (SAMPLE_TBL, LATHE_TBL):
        entries = parse_tbl(text)
        canonical = format_tbl(entries)
        assert parse_tbl(canonical) == sorted(entries, key=lambda e: e.number)  # rosnąco po T
        assert format_tbl(parse_tbl(canonical)) == canonical
    lathe = {e.number: e for e in parse_tbl(LATHE_TBL)}
    assert lathe[7].values == {"X": 1.5, "Z": -2.25, "D": 0.8, "I": 95.0, "J": 155.0}
    assert lathe[7].orientation == 3 and lathe[7].comment == "tokarski"
    assert lathe[8].pocket == 0 and "X" not in lathe[8].values  # X0 = brak przesunięcia


def test_tbl_canonical_format():
    assert format_tbl(parse_tbl(SAMPLE_TBL)).splitlines()[0] == "T1 P1 Z0.511 D0.125 ;1/8 end mill"
    assert format_tbl([TblEntry(2, 3, {"Z": -0.0, "D": 1e-7})]) == "T2 P3 Z0 D0\n"
    assert format_tbl([]) == ""


@pytest.mark.parametrize("text,detail", [
    ("T1 Z1\n", "brak wymaganego słowa P"),
    ("T1 P1 K2\n", "nieznane słowo K2"),
    ("T1 P1 Z1 Z2\n", "powtórzone"),
    ("T1 P100000\n", "0…99999"),
    ("T0 P1\n", "1…"),
    ("T1 P1 Zabc\n", "oczekiwano liczby"),
    ("T1 P1 D-2\n", "ujemna"),
    ("T1 P1 Q12\n", "0…9"),
    ("T1 P1\nT1 P2\n", "T1 już w linii 1"),
    ("T1 P1\nT2 P1\n", "P1 już w linii 1"),
])
def test_tbl_errors_with_line(text, detail):
    with pytest.raises(ToolTableError) as info:
        parse_tbl(text)
    assert info.value.issues[0].code == "P-5204"
    assert detail in info.value.issues[0].message()


# ---- baza ----------------------------------------------------------------------------------


def test_add_get_update_remove_with_history(db):
    tool = _flat()
    db.add(tool)
    assert db.get(1) == tool
    changed = _flat(d=8.0)
    db.update(changed, source="test")
    db.update(changed)  # bez zmian: bez wpisu w historii
    db.remove(1)
    history = db.history(1)
    assert [h["action"] for h in history] == ["add", "update", "remove"]
    assert [h["time"] for h in history] == [1001.0, 1002.0, 1003.0]
    assert history[1]["source"] == "test"
    assert '"d": 6.0' in history[1]["before"]["params"]
    assert '"d": 8.0' in history[1]["after"]["params"]
    assert history[2]["after"] is None and db.get(1) is None


def test_rejects_duplicates_and_invalid(db):
    db.add(_flat(1, 1))
    with pytest.raises(ToolDBError) as info:
        db.add(_flat(1, 2))
    assert [i.code for i in info.value.issues] == ["P-5202"]
    with pytest.raises(ToolDBError) as info:
        db.add(_flat(2, 1))
    assert info.value.issues[0].code == "P-5203"
    assert "Gniazdo P1 jest już zajęte przez narzędzie T1." in str(info.value)
    with pytest.raises(ToolDBError) as info:
        db.add(Tool(3, 3, type="ball", params={"d": 6}))
    assert info.value.issues[0].field == "l"
    with pytest.raises(ToolDBError):
        db.add(Tool(4, 4, description="zły; opis"))
    with pytest.raises(ToolDBError) as info:
        db.update(_flat(9, 9))
    assert info.value.issues[0].code == "P-5206"
    assert [t.number for t in db.tools()] == [1]
    assert len(db.history()) == 1  # odrzucone operacje nie zostawiają śladu


def test_export_tbl_atomic_and_roundtrip(db, tmp_path):
    db.add(_flat(1, 1))
    db.add(Tool(2, 5, type="drill_118", description="wiertło 5", params={"d": 5.0, "l": 60.0},
                offsets={"Z": 80.125}))
    path = db.export_tbl(tmp_path / "tool.tbl")
    text = path.read_text(encoding="utf-8")
    assert text == "T1 P1 Z52.3 D6 ;frez 6 mm\nT2 P5 Z80.125 D5 ;wiertło 5\n"
    assert not list(tmp_path.glob(".*.tmp"))
    # tbl → baza → tbl bez strat
    with ToolDB(tmp_path / "druga.db") as other:
        other.import_tbl(text)
        assert other.export_tbl(tmp_path / "t2.tbl").read_text(encoding="utf-8") == text


def test_inch_machine_units(db, tmp_path):
    db.add(_flat(1, 1))  # Z 52,3 mm, D 6 mm
    text = db.export_tbl(tmp_path / "in.tbl", units="inch").read_text(encoding="utf-8")
    assert text == "T1 P1 Z2.059055 D0.23622 ;frez 6 mm\n"
    with ToolDB(":memory:") as other:
        other.import_tbl(text, units="inch")
        assert other.get(1).offsets["Z"] == pytest.approx(52.3, abs=1e-4)
    with pytest.raises(ValueError, match="mm albo inch"):
        db.export_tbl(tmp_path / "x.tbl", units="cm")


def test_import_keeps_type_and_geometry(db):
    db.add(_flat(1, 1))
    changed = db.import_tbl("T1 P3 Z60.5 D6 ;frez 6 mm po pomiarze\nT9 P9 Z10 D3 ;nowy\n")
    assert changed == [1, 9]
    tool = db.get(1)
    assert tool.type == "flat" and tool.params["flute_length"] == 15.0   # zachowane
    assert tool.pocket == 3 and tool.offsets == {"Z": 60.5}               # z tool.tbl
    assert tool.description == "frez 6 mm po pomiarze"
    new = db.get(9)
    assert new.type is None and new.diameter == 3.0
    assert [w.code for w in new.warnings()] == ["K-320"]
    assert db.history(1)[-1]["action"] == "import"
    # zmiana średnicy w LinuxCNC (G10 L1) trafia do geometrii typu
    db.import_tbl("T1 P3 Z60.5 D6.02 ;frez 6 mm po pomiarze\n")
    assert db.get(1).params["d"] == 6.02
    assert db.import_tbl("T1 P3 Z60.5 D6.02 ;frez 6 mm po pomiarze\n") == []  # bez zmian


def test_import_swaps_pockets_or_rejects_all(db):
    db.add(_flat(1, 1))
    db.add(_flat(2, 2))
    db.import_tbl("T1 P2 Z52.3 D6 ;frez 6 mm\nT2 P1 Z52.3 D6 ;frez 6 mm\n")
    assert (db.get(1).pocket, db.get(2).pocket) == (2, 1)
    with pytest.raises(ToolDBError) as info:  # T3 w gnieździe zajętym przez T1 (spoza importu)
        db.import_tbl("T2 P1 Z1 D6\nT3 P2 Z1\n")
    assert info.value.issues[0].code == "P-5203"
    assert db.get(3) is None and db.get(2).offsets == {"Z": 52.3}  # nic nie zapisano


def test_csv_roundtrip(db):
    db.add(_flat(1, 1))
    db.add(Tool(2, 2, type="chamfer", params={"d": 10.0, "angle": 90.0}, life_min=120.0,
                holder="ER16", lathe={"Q": 2.0}))
    text = db.export_csv()
    with ToolDB(":memory:") as other:
        assert other.import_csv(text) == [1, 2]
        assert other.tools() == db.tools()
        assert other.export_csv() == text
        assert other.import_csv(text) == []
    with pytest.raises(ToolDBError) as info:
        db.import_csv("number,pocket\nx,1\n")
    assert info.value.issues[0].code == "P-5204"


def test_migrations_and_newer_database(tmp_path):
    path = tmp_path / "narzedzia.db"
    with ToolDB(path) as base:
        assert base.schema_version == len(MIGRATIONS)
        base.add(_flat())
    with ToolDB(path) as again:  # ponowne otwarcie bez migracji, dane zostają
        assert again.get(1) == _flat()
    raw = sqlite3.connect(path)
    raw.execute(f"PRAGMA user_version = {len(MIGRATIONS) + 1}")
    raw.commit()
    raw.close()
    with pytest.raises(ToolDBError, match="nowsza"):
        ToolDB(path)


@pytest.mark.linuxcnc
def test_exported_table_used_by_linuxcnc(db, tmp_path):  # tool.tbl z bazy w interpreterze 2.9
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache" / "linuxcnc-2.9"))
    if not (root / "bin" / "rs274").exists():
        pytest.skip(f"brak rs274 w {root}")
    db.add(_flat(1, 1))
    db.add(Tool(2, 7, description="bez typu", offsets={"Z": 33.75}, diameter=4.0))
    table = db.export_tbl(tmp_path / "tool.tbl")
    program = tmp_path / "t.ngc"
    program.write_text("G21\nT2 M6\nG43 H2\nG0 X0\nT1 M6\nG43 H1\nM2\n", encoding="utf-8")
    sim = root / "configs" / "sim" / "axis"
    run = subprocess.run(["bash", "-c", f"source '{root}/scripts/rip-environment' >/dev/null && "
                          f"rs274 -i axis_mm.ini -t '{table}' -n 0 '{program}' </dev/null"],
                         cwd=sim, capture_output=True, text=True, timeout=60, check=False)
    offsets = [line for line in run.stdout.splitlines() if "USE_TOOL_LENGTH_OFFSET" in line]
    assert len(offsets) == 2, run.stdout + run.stderr
    assert "33.7500" in offsets[0] and "52.3000" in offsets[1], offsets
    # Maszyna calowa: tool.tbl w calach, interpreter z G21 przelicza z powrotem na mm.
    inch = db.export_tbl(tmp_path / "tool_in.tbl", units="inch")
    run = subprocess.run(["bash", "-c", f"source '{root}/scripts/rip-environment' >/dev/null && "
                          f"rs274 -i axis.ini -t '{inch}' -n 0 '{program}' </dev/null"],
                         cwd=sim, capture_output=True, text=True, timeout=60, check=False)
    offsets = [line for line in run.stdout.splitlines() if "USE_TOOL_LENGTH_OFFSET" in line]
    assert "33.7500" in offsets[0] and "52.3000" in offsets[1], offsets
