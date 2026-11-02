"""Format .lnx, BaseMacroGenerator, rejestr i kompilator .lnx → .ngc (sesja 039).

Model-Author: Claude
Generatory w tym pliku są przykładowe (testowe); generatory wbudowane powstają w sesjach 040–043.
Plik golden: tests/golden/lnx_program.ngc (odświeżenie: LINUMERT_UPDATE_GOLDEN=1).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from linumert.generators.base import BaseMacroGenerator, Field, Issue, fmt
from linumert.generators.registry import GeneratorRegistry, RegistryError
from linumert.programs.compiler import CompileError, compile_file, compile_program
from linumert.programs.lnx import (
    SCHEMA_PATH,
    LnxError,
    LnxProgram,
    Step,
    dump_lnx,
    json_schema,
    load_lnx,
    parse_lnx,
    save_lnx,
)
from linumert.programs.stock import Stock, StockError, format_stock_line, parse_stock_line

GOLDEN = Path(__file__).with_name("golden") / "lnx_program.ngc"


# ---- generatory przykładowe ----------------------------------------------------------------


class DrillPoint(BaseMacroGenerator):
    name = "test_drill"
    version = 1
    title = "Wiercenie punktu (test)"
    fields = (
        Field("x", "float", "X", "mm"),
        Field("y", "float", "Y", "mm"),
        Field("depth", "float", "Głębokość", "mm", minimum=0, exclusive_minimum=True,
              maximum=200),
        Field("retract", "float", "Wycofanie R", "mm", default=2.0, minimum=0.5),
        Field("feed", "float", "Posuw", "mm/min", default=100.0, minimum=1, maximum=20000),
    )

    def check(self, values, step):
        if values["retract"] > 50:
            return [Issue("P-5003", {"name": "retract", "value": fmt(values["retract"]),
                                     "limit": "<= 50 mm przy wierceniu"}, "retract")]
        return []

    def generate(self, v):
        return [f"G0 Z{fmt(v['retract'])}",
                f"G98 G81 X{fmt(v['x'])} Y{fmt(v['y'])} Z{fmt(-v['depth'])} "
                f"R{fmt(v['retract'])} F{fmt(v['feed'])}",
                "G80"]

    def preview_2d(self, v):
        x, y = v["x"], v["y"]
        return [[(x - 1, y), (x + 1, y)], [(x, y - 1), (x, y + 1)]]


class DrillPointV2(DrillPoint):
    """Nowa wersja: wiercenie z łamaniem wióra (G73), stara zostaje w rejestrze."""

    version = 2
    fields = DrillPoint.fields + (Field("peck", "float", "Krok Q", "mm", default=1.0,
                                        minimum=0.1),)

    def generate(self, v):
        return [f"G0 Z{fmt(v['retract'])}",
                f"G98 G73 X{fmt(v['x'])} Y{fmt(v['y'])} Z{fmt(-v['depth'])} "
                f"R{fmt(v['retract'])} Q{fmt(v['peck'])} F{fmt(v['feed'])}",
                "G80"]


class Coolant(BaseMacroGenerator):
    name = "test_coolant"
    version = 1
    title = "Chłodzenie (test)"
    fields = (Field("mode", "choice", "Tryb", choices=("mist", "flood", "off")),
              Field("note", "text", "Uwaga", default=""),
              Field("wait", "bool", "Czekaj", default=False))

    def generate(self, v):
        lines = [{"mist": "M7", "flood": "M8", "off": "M9"}[v["mode"]]]
        if v["wait"]:
            lines.append("G4 P0.5")
        return lines


class BadOutput(BaseMacroGenerator):
    name = "test_bad"
    version = 1
    title = "Zły generator (test)"
    fields = (Field("variant", "int", "Wariant", minimum=0, maximum=4),)

    def generate(self, v):
        return [["M98 P100", "G0 X0\nG0 Y0", "G1 X1 (bez zamkniecia", "M30",
                 "G0 X1 ( M2 w komentarzu ) M20 ; M99 po srednik"][v["variant"]]]


@pytest.fixture
def registry():
    reg = GeneratorRegistry()
    for cls in (DrillPoint, DrillPointV2, Coolant, BadOutput):
        reg.register(cls)
    return reg


def _program(**extra) -> LnxProgram:
    data = {
        "name": "pokrywa",
        "comment": "płyta testowa (sesja 039)",
        "stock": {"shape": "BOX", "x": 120, "y": 80, "z": 30, "origin": "TOP_FRONT_LEFT",
                  "top": 1.0, "material": "aluminium"},
        "steps": [
            {"generator": "test_coolant", "version": 1, "params": {"mode": "flood"}},
            {"generator": "test_drill", "version": 1, "comment": "otwór A",
             "params": {"x": 10, "y": 12.5, "depth": 8}},
            {"generator": "test_drill", "version": 2,
             "params": {"x": -0.00001, "y": 40, "depth": 20.25, "peck": 2.5, "feed": 80}},
            {"generator": "test_drill", "version": 1, "enabled": False,
             "params": {"x": 1, "y": 1, "depth": 1}},
            {"generator": "test_coolant", "version": 1, "params": {"mode": "off"}},
        ],
    }
    data.update(extra)
    return parse_lnx(data)


# ---- przygotówka ---------------------------------------------------------------------------


@pytest.mark.parametrize("line", [
    ';@STOCK BOX X120 Y80 Z30 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 TOP=1.0 MAT="aluminium"',
    ";@STOCK CYL D60 H40 ORIGIN=TOP_CENTER OFFSET=G54",
    ";@stock box y80 x120.50 z30 offset=g55",
    ';@STOCK BOX X1 Y2 Z3 MAT="stal nierdzewna 1.4301" OFFSET=G59.3',
])
def test_stock_line_roundtrip(line):
    stock = parse_stock_line(line)
    canonical = format_stock_line(stock)
    assert parse_stock_line(canonical) == stock
    assert format_stock_line(parse_stock_line(canonical)) == canonical


def test_stock_canonical_form():
    stock = parse_stock_line(';@STOCK BOX X120 Y80 Z30 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 '
                             'TOP=1.0 MAT="aluminium"')
    assert format_stock_line(stock) == (';@STOCK BOX X120 Y80 Z30 ORIGIN=TOP_FRONT_LEFT '
                                        'OFFSET=G54 TOP=1 MAT="aluminium"')
    assert format_stock_line(Stock(shape="CYL", d=60, h=40, origin="TOP_CENTER")) == \
        ";@STOCK CYL D60 H40 ORIGIN=TOP_CENTER OFFSET=G54"


@pytest.mark.parametrize("line,match", [
    (";@STOCK", "BOX albo CYL"),
    (";@STOCK BOX X10 Y10", "Z"),
    (";@STOCK CYL D10 H5 X3", "nie ma wymiarów"),
    (";@STOCK CYL D10 H5 ORIGIN=TOP_FRONT_LEFT", "środku"),
    (";@STOCK BOX X10 Y10 Z10 ORIGIN=GDZIES", "origin"),
    (";@STOCK BOX X10 Y10 Z10 OFFSET=G60", "offset"),
    (';@STOCK BOX X10 Y10 Z10 MAT="otwarte', "cudzysłów"),
    (";@STOCK BOX X10 Y10 Z10 KOLOR=red", "nieznane"),
    (";@STOCK BOX X-10 Y10 Z10", "x"),
    (";@STOCK BOX Xabc Y10 Z10", "niepoprawne"),
    ("( komentarz )", "nie zaczyna"),
])
def test_stock_line_errors(line, match):
    with pytest.raises(StockError, match=match):
        parse_stock_line(line)


# ---- plik .lnx -----------------------------------------------------------------------------


def test_schema_file_is_generated_from_model():
    assert json.loads(SCHEMA_PATH.read_text(encoding="utf-8")) == json_schema()


def test_lnx_save_load_roundtrip(tmp_path):
    program = _program()
    path = save_lnx(program, tmp_path / "pokrywa.lnx")
    assert load_lnx(path) == program
    assert dump_lnx(load_lnx(path)) == path.read_text(encoding="utf-8")  # stabilny zapis
    assert not list(tmp_path.glob(".*.tmp"))
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1


@pytest.mark.parametrize("data,match", [
    ({"name": "a", "steps": [{"generator": "x", "version": 0}]}, r"steps\.0\.version"),
    ({"name": "a", "kolor": 1}, "kolor"),
    ({"name": ""}, "name"),
    ({"name": "a", "schema_version": 2}, "wersję 1"),
    ({"name": "a", "stock": {"shape": "BOX", "x": 1}}, "stock"),
    ({"name": "a", "units": "cm"}, "units"),
])
def test_lnx_errors_have_field_paths(data, match):
    with pytest.raises(LnxError, match=match) as info:
        parse_lnx(data)
    assert all(i.code == "P-5012" for i in info.value.alarms())


def test_lnx_bad_files(tmp_path):
    (tmp_path / "zly.lnx").write_text("{", encoding="utf-8")
    with pytest.raises(LnxError, match="JSON"):
        load_lnx(tmp_path / "zly.lnx")
    with pytest.raises(LnxError, match="brak pliku"):
        load_lnx(tmp_path / "nie_ma.lnx")


# ---- generator: walidacja ------------------------------------------------------------------


def test_validation_codes_and_messages():
    gen = DrillPoint()
    issues = gen.validate({"x": "dziesięć", "depth": 0, "feed": 1e6, "kolor": 3}, step=4)
    codes = {(i.code, i.field) for i in issues}
    assert codes == {("P-5015", "kolor"), ("P-5015", "x"), ("P-5014", "y"),
                     ("P-5003", "depth"), ("P-5003", "feed")}
    depth = next(i for i in issues if i.field == "depth")
    assert depth.message() == "Wartość depth = 0 jest poza dozwolonym zakresem (> 0, <= 200 mm)."
    assert "outside the allowed range" in depth.message("en")
    missing = next(i for i in issues if i.field == "y")
    assert missing.message() == "Krok 4: brak wymaganego pola y."
    assert gen.validate({"x": 1, "y": 2, "depth": 3}) == []
    cross = gen.validate({"x": 1, "y": 2, "depth": 3, "retract": 60})
    assert [i.code for i in cross] == ["P-5003"]  # reguła między polami (check)


def test_field_kinds():
    gen = Coolant()
    assert gen.validate({"mode": "flood", "wait": True, "note": "ok"}) == []
    bad = gen.validate({"mode": "lód", "wait": 1, "note": "a ( b"})
    assert {i.field for i in bad} == {"mode", "wait", "note"}
    assert all(i.code == "P-5015" for i in bad)
    assert BadOutput().validate({"variant": 2.0}) == []      # 2.0 to liczba całkowita
    assert [i.code for i in BadOutput().validate({"variant": 2.5})] == ["P-5015"]
    assert [i.code for i in DrillPoint().validate({"x": float("nan"), "y": 0, "depth": 1})] == \
        ["P-5015"]


def test_fmt_is_deterministic():
    assert fmt(-0.00001) == "0"
    assert fmt(12.50) == "12.5"
    assert fmt(1e-5, 6) == "0.00001"
    assert fmt(123456789.0) == "123456789"
    with pytest.raises(ValueError):
        fmt(float("inf"))


# ---- kompilator ----------------------------------------------------------------------------


def test_compile_golden_and_deterministic(registry, tmp_path):
    text = compile_program(_program(), registry, source="pokrywa.lnx")
    if os.environ.get("LINUMERT_UPDATE_GOLDEN"):
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(text, encoding="utf-8", newline="\n")
    assert text == GOLDEN.read_text(encoding="utf-8")
    assert compile_program(_program(), registry, source="pokrywa.lnx") == text
    lnx = save_lnx(_program(), tmp_path / "pokrywa.lnx")
    ngc = compile_file(lnx, registry=registry)
    assert ngc.read_text(encoding="utf-8") == text  # z pliku tak samo jak z pamięci
    assert ngc.suffix == ".ngc"


def test_compile_pins_generator_version(registry):
    text = compile_program(_program(), registry)
    assert "G81 X10 Y12.5 Z-8 R2 F100" in text           # krok v1
    assert "G73 X0 Y40 Z-20.25 R2 Q2.5 F80" in text      # krok v2
    assert "( krok 4 pominiety: test_drill v1 )" in text
    program = _program(steps=[{"generator": "test_drill", "version": 3,
                               "params": {"x": 0, "y": 0, "depth": 1}}])
    with pytest.raises(CompileError) as info:
        compile_program(program, registry)
    assert [i.code for i in info.value.issues] == ["P-5011"]
    assert "brak generatora test_drill w wersji 3" in str(info.value)


def test_validation_error_blocks_write(registry, tmp_path):
    program = _program(steps=[
        {"generator": "test_drill", "version": 1, "params": {"x": 0, "y": 0, "depth": 5}},
        {"generator": "test_drill", "version": 1, "params": {"x": 0, "depth": -1}},
    ])
    lnx = save_lnx(program, tmp_path / "zly.lnx")
    ngc = tmp_path / "zly.ngc"
    ngc.write_text("poprzednia wersja\n", encoding="utf-8")
    with pytest.raises(CompileError) as info:
        compile_file(lnx, registry=registry)
    assert {(i.code, i.field) for i in info.value.issues} == {("P-5014", "y"),
                                                              ("P-5003", "depth")}
    assert "Krok 2" in str(info.value)
    assert ngc.read_text(encoding="utf-8") == "poprzednia wersja\n"  # nietknięty
    assert not (tmp_path / "inny.ngc").exists()


@pytest.mark.parametrize("variant,word", [(0, "M98"), (1, "znak nowej linii"),
                                          (2, "niezamknięty komentarz"), (3, "M30")])
def test_generator_output_is_checked(registry, variant, word):
    program = _program(steps=[{"generator": "test_bad", "version": 1,
                               "params": {"variant": variant}}])
    with pytest.raises(CompileError) as info:
        compile_program(program, registry)
    assert info.value.issues[0].code == "P-5013"
    assert info.value.issues[0].params["word"] == word


def test_codes_in_comments_and_m20_are_allowed(registry):
    program = _program(steps=[{"generator": "test_bad", "version": 1, "params": {"variant": 4}}])
    assert "M20" in compile_program(program, registry)


def test_units_and_no_stock(registry):
    text = compile_program(_program(units="inch", stock=None, comment=None), registry)
    assert "\nG20\n" in text and ";@STOCK" not in text
    assert text.endswith("M2\n")


def test_compat_wrappers():
    gen = DrillPoint()
    assert gen.is_valid({"x": 1, "y": 2, "depth": 3})
    assert not gen.is_valid({"x": 1})
    text = gen.generate_ngc({"x": 1, "y": 2, "depth": 3}, "otwor.ngc")
    assert "G81 X1 Y2 Z-3" in text and text.endswith("M2\n")
    with pytest.raises(CompileError):
        gen.generate_ngc({"x": 1}, "otwor.ngc")
    assert gen.preview_2d({"x": 1, "y": 2})[0] == [(0, 2), (2, 2)]


def test_registry_rules():
    reg = GeneratorRegistry()
    reg.register(DrillPoint)
    reg.register(DrillPoint)  # ta sama klasa ponownie: bez zmian
    reg.register(DrillPointV2)
    assert reg.names() == ["test_drill"]
    assert reg.latest("test_drill").version == 2
    assert reg.get("test_drill", 1).version == 1
    assert reg.get("nie_ma", 1) is None and reg.latest("nie_ma") is None

    class Other(DrillPoint):
        pass

    with pytest.raises(RegistryError, match="już"):
        reg.register(Other)

    class BadName(DrillPoint):
        name = "Zła Nazwa"

    class BadVersion(DrillPoint):
        name = "ok_name"
        version = 0

    class Duplicate(DrillPoint):
        name = "dup"
        fields = (Field("a", "int", "A"), Field("a", "int", "A"))

    for cls, match in ((BadName, "nazwa"), (BadVersion, "wersja"), (Duplicate, "powtórzone")):
        with pytest.raises(RegistryError, match=match):
            reg.register(cls)


def test_step_model_defaults():
    step = Step(generator="g", version=1)
    assert step.enabled and step.params == {}
