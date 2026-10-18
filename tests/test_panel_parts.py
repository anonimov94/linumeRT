"""Panel Plant bez rdzenia C i bez FastAPI: telemetria, pulpit, presety, CSV (sesja 022).

Model-Author: Claude
"""

from __future__ import annotations

import csv
import sys

import pytest
from linumert_plant.panel import PanelUnavailable, load_app_module
from linumert_plant.panel.desk import MAX_PENDING_EDGES, QUADRATURE, Desk, DeskConfig
from linumert_plant.panel.presets import (
    PresetError,
    builtin_values,
    list_presets,
    load_preset,
    save_preset,
)
from linumert_plant.panel.record import Recorder
from linumert_plant.panel.telemetry import FIELDS, Telemetry
from linumert_plant.server import PlantConfigError, load_plant_config

DESK = {"mpg_a": 16, "mpg_b": 17, "axis": {"x": 18, "Y": 19, "Z": 20},
        "step": {1: 21, 10: 22, 100: 23}, "cycle_start": 24, "feed_hold": 25, "key": 26}


def _bits(value: int, *bits: int) -> tuple[int, ...]:
    return tuple(value >> b & 1 for b in bits)


# ---- import bez zależności panelu --------------------------------------------------------

def test_panel_without_fastapi_gives_clear_error(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "fastapi", None)
    monkeypatch.delitem(sys.modules, "linumert_plant.panel.app", raising=False)
    import linumert_plant.panel as panel_pkg

    monkeypatch.delattr(panel_pkg, "app", raising=False)
    import linumert_plant.server  # noqa: F401 - serwer działa bez panelu

    with pytest.raises(PanelUnavailable, match=r"pip install -e \"\.\[panel\]\""):
        load_app_module()


# ---- telemetria ---------------------------------------------------------------------------

def _row(k: float, n: int = 1) -> tuple:
    return tuple(float(k + i) for i in range(len(FIELDS) * n))


def test_telemetry_ring_window_and_since() -> None:
    tel = Telemetry(["a", "b"], window_s=0.1, period_s=0.01)
    t = 0.0
    for k in range(30):
        assert tel.due(t)
        tel.put(t, _row(k, 2))
        assert not tel.due(t + 0.005)
        t += 0.01
    first, data = tel.since()
    assert tel.count == 30 and len(data) == 11 and first == 19  # okno 0,1 s
    first, data = tel.since(25)
    assert first == 25 and len(data) == 5 and data[0][1][0] == 25.0
    assert tel.since(5)[0] == 19  # starsze niż okno: od pierwszej dostępnej
    assert tel.since(99) == (30, [])
    cols = tel.columns(28)
    assert cols["next"] == 30 and cols["t"] == [0.28, 0.29]
    assert cols["drives"]["b"]["cmd"] == [28.0 + len(FIELDS), 29.0 + len(FIELDS)]
    assert set(cols["drives"]["a"]) == set(FIELDS)


def test_telemetry_rejects_bad_period() -> None:
    with pytest.raises(ValueError, match="okres"):
        Telemetry(["a"], period_s=0.0)


# ---- pulpit -------------------------------------------------------------------------------

def test_desk_mpg_quadrature_direction_and_limit() -> None:
    desk = Desk(DeskConfig.from_dict(DESK))
    assert desk.mpg(1) == 4
    seen = []
    for _ in range(6):
        desk.step(0.001)
        _mask, value = desk.inputs()
        seen.append(_bits(value, 16, 17))
    assert seen[:4] == [QUADRATURE[1], QUADRATURE[2], QUADRATURE[3], QUADRATURE[0]]
    assert seen[4:] == [(0, 0), (0, 0)]  # zaległość wyczerpana: koło stoi
    assert desk.edges == 4
    desk.mpg(-1)
    for _ in range(4):
        desk.step(0.001)
        seen.append(_bits(desk.inputs()[1], 16, 17))
    assert seen[6:] == [QUADRATURE[3], QUADRATURE[2], QUADRATURE[1], QUADRATURE[0]]
    assert desk.edges == 0
    taken = desk.mpg(10 * MAX_PENDING_EDGES)
    assert taken == MAX_PENDING_EDGES and desk.dropped == 39 * MAX_PENDING_EDGES
    assert desk.mpg(-1) == -4  # przeciwny kierunek zmniejsza zaległość


def test_desk_selectors_buttons_key() -> None:
    desk = Desk(DeskConfig.from_dict(DESK))
    mask, value = desk.inputs()
    assert mask == sum(1 << b for b in range(16, 27))
    assert _bits(value, 18, 19, 20, 21, 22, 23) == (1, 0, 0, 1, 0, 0)  # X, ×1
    desk.select_axis("z")
    desk.select_step(100)
    desk.set_key(True)
    desk.press("cycle_start")
    value = desk.inputs()[1]
    assert _bits(value, 18, 19, 20, 21, 22, 23, 24, 25, 26) == (0, 0, 1, 0, 0, 1, 1, 0, 1)
    for _ in range(99):
        desk.step(0.001)
    assert _bits(desk.inputs()[1], 24) == (1,)
    desk.step(0.0011)
    assert _bits(desk.inputs()[1], 24) == (0,)  # impuls 100 ms
    for bad in (lambda: desk.select_axis("A"), lambda: desk.select_step(5),
                lambda: desk.press("reset")):
        with pytest.raises(ValueError, match="pulpi"):
            bad()


def test_desk_config_problems() -> None:
    cfg = DeskConfig.from_dict({**DESK, "key": 16, "feed_hold": 40, "edges_per_detent": 3})
    problems = "; ".join(cfg.problems({"estop": 0, "lim_x": 18}))
    assert "desk.key: bit 16 zajęty już przez desk.mpg_a" in problems
    assert "desk.feed_hold: bit 40 poza 0–31" in problems
    assert "wejście maszyny lim_x" in problems
    assert "edges_per_detent" in problems
    assert "obu bitów" in "; ".join(DeskConfig(mpg_a=1).problems())
    with pytest.raises(ValueError, match="nieznane pola"):
        DeskConfig.from_dict({"mpgA": 1})
    assert Desk(DeskConfig()).inputs() == (0, 0)
    with pytest.raises(ValueError, match="bez MPG"):
        Desk(DeskConfig()).mpg(1)


def test_plant_yaml_desk_and_panel_sections(tmp_path) -> None:
    path = tmp_path / "plant.yaml"
    path.write_text("machine: m.yaml\nnetwork: {panel_port: 47811, panel_listen: 0.0.0.0}\n"
                    "panel: {telemetry_ms: 2}\n"
                    "desk: {mpg_a: 20, mpg_b: 21, axis: {X: 22}, step: {1: 23}}\n",
                    encoding="utf-8")
    cfg = load_plant_config(path)
    assert (cfg.panel_port, cfg.panel_listen, cfg.telemetry_ms) == (47811, "0.0.0.0", 2.0)
    assert cfg.desk.bits() == {"mpg_a": 20, "mpg_b": 21, "axis.X": 22, "step.1": 23}
    path.write_text("machine: m.yaml\ndesk: {mpg_a: 3, mpg_b: 3}\n", encoding="utf-8")
    with pytest.raises(PlantConfigError, match="zajęty już"):
        load_plant_config(path)
    path.write_text("machine: m.yaml\nnetwork: {panel_port: 70000}\n", encoding="utf-8")
    with pytest.raises(PlantConfigError, match="panel_port"):
        load_plant_config(path)


# ---- presety ------------------------------------------------------------------------------

BASE = {"drv_x": {"live": ["mechanics.load", "limits.torque_limit_permille"],
                  "mechanics": {"load": 40.0}, "limits": {"torque_limit_permille": 3000}}}


def test_presets_builtin_and_saved(tmp_path) -> None:
    assert builtin_values("ciezki_stol", BASE) == {
        "drv_x": {"mechanics.load": 80.0, "limits.torque_limit_permille": 3000}}
    assert builtin_values("zuzyty_silnik", BASE)["drv_x"]["limits.torque_limit_permille"] == 2400
    assert load_preset("startowy", BASE, None) == {
        "drv_x": {"mechanics.load": 40.0, "limits.torque_limit_permille": 3000}}
    values = {"drv_x": {"mechanics.load": 12.5}}
    save_preset("moj-1", values, tmp_path)
    assert load_preset("moj-1", BASE, tmp_path) == values
    names = [p["name"] for p in list_presets(tmp_path)]
    assert names[:4] == ["startowy", "lekki", "ciezki_stol", "zuzyty_silnik"] and "moj-1" in names
    for name, fragment in (("../x", "dozwolone"), ("lekki", "wbudowany"), ("", "dozwolone")):
        with pytest.raises(PresetError, match=fragment):
            save_preset(name, values, tmp_path)
    with pytest.raises(PresetError, match="brak presetu"):
        load_preset("nie_ma", BASE, tmp_path)
    (tmp_path / "zly.json").write_text("[1]", encoding="utf-8")
    with pytest.raises(PresetError, match="oczekiwano"):
        load_preset("zly", BASE, tmp_path)


# ---- nagrywanie CSV -----------------------------------------------------------------------

def test_recorder_writes_csv_and_counts_dropped(tmp_path) -> None:
    tel = Telemetry(["a"], window_s=0.05, period_s=0.01)
    tel.put(0.0, _row(0))
    rec = Recorder(tel, tmp_path / "rec")
    path = rec.start("test")
    assert path.name == "test.csv" and rec.active
    with pytest.raises(RuntimeError, match="już trwa"):
        rec.start("inny")
    for k in range(1, 4):
        tel.put(k * 0.01, _row(k))
    assert rec.pump() == 3
    for k in range(4, 20):  # więcej niż okno między odczytami
        tel.put(k * 0.01, _row(k))
    rec.stop()
    rows = list(csv.reader(path.open(encoding="utf-8")))
    assert rows[0] == ["t"] + [f"a.{f}" for f in FIELDS]
    assert rows[1][:2] == ["0.010000", "1"]
    assert len(rows) - 1 == rec.rows == 9 and rec.dropped == 10
    assert rec.files() == [{"name": "test.csv", "bytes": path.stat().st_size}]
    with pytest.raises(ValueError, match="nazwa pliku"):
        rec.start("../zly")
