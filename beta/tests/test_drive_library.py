"""Testy biblioteki napędów wirtualnych (sesja 013): szablony, instancje, klony, zmiany live.

Model-Author: Claude. Znaczniki `# REQ-VD-nn` wskazują wymagania z
docs/wymagania/WIRTUALNA_OBRABIARKA.md. NIEZWERYFIKOWANE NA SPRZĘCIE: wartości szablonów są
przykładowe; walidacja i krótki test dynamiki wykorzystują rdzeń C (plant/core).
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from linumert_plant import drive_library as lib_mod
from linumert_plant.__main__ import main as cli_main
from linumert_plant.drive_library import (
    LIBRARY_DIR,
    apply_overrides,
    clone_instance,
    clone_template,
    load_library,
    load_template_file,
    resolve_instance,
    resolve_instances,
    save_template,
)
from linumert_plant.drive_template import (
    CIA_REQUIRED,
    LIVE_CAPABLE,
    LIVE_TO_C,
    LiveParams,
    TemplateError,
    available_torque,
    c_check_input,
    json_schema,
    max_acceleration,
    template_issues,
    total_inertia,
    validate_template,
)

ROOT = Path(__file__).resolve().parents[1]  # beta/ (testy leżą płasko w tests/, jak w głównym repo)
CORE = ROOT / "plant_core"  # w beta rdzeń C nosi nazwę plant_core
EXPECTED_IDS = {
    "stepper_nema23_3nm", "stepper_nema34_85nm", "servo_stepper_22nm", "servo_400w",
    "servo_750w", "rotary_table_worm_1_90", "spindle_vfd_22kw",
}
HAS_TOOLCHAIN = shutil.which("make") is not None and (
    shutil.which("cc") is not None or shutil.which("gcc") is not None
)


@pytest.fixture(scope="module")
def library() -> dict[str, dict]:
    return load_library()


@pytest.fixture()
def servo(library: dict[str, dict]) -> dict:
    return copy.deepcopy(library["servo_400w"])


@pytest.fixture(scope="module")
def check_tool() -> Path:
    if not HAS_TOOLCHAIN:
        pytest.skip("brak make i kompilatora C")
    result = subprocess.run(["make", "-C", str(CORE), "tools"], capture_output=True, text=True,
                            check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    return CORE / "build" / "lrt_check_params"


# --- REQ-VD-05: biblioteka startowa --------------------------------------------------------


def test_library_loads_all(library: dict[str, dict]) -> None:
    # REQ-VD-05
    assert set(library) == EXPECTED_IDS
    for tpl_id, tpl in library.items():
        assert (LIBRARY_DIR / f"{tpl_id}.yaml").is_file()
        assert "przykładowe" in tpl["value_source"], tpl_id
        assert tpl["based_on"] is None and tpl["version"] == 1
    types = {t["type"] for t in library.values()}
    assert types == {"servo_csp", "servo_stepper", "stepper_open", "rotary_geared", "spindle_vfd"}


def test_library_values_match_requirement_classes(library: dict[str, dict]) -> None:
    # REQ-VD-05: klasy momentu/mocy z wymagania
    assert library["stepper_nema23_3nm"]["motor"]["rated_torque"] == pytest.approx(3.0, rel=0.1)
    assert library["stepper_nema34_85nm"]["motor"]["rated_torque"] == pytest.approx(8.5, rel=0.1)
    assert library["servo_stepper_22nm"]["motor"]["rated_torque"] == pytest.approx(2.2, rel=0.1)
    # moc = moment znamionowy × prędkość znamionowa (3000 obr/min = 314 rad/s)
    assert library["servo_400w"]["motor"]["rated_torque"] * 314.16 == pytest.approx(400, rel=0.05)
    assert library["servo_750w"]["motor"]["rated_torque"] * 314.16 == pytest.approx(750, rel=0.05)
    assert library["rotary_table_worm_1_90"]["mechanics"]["ratio"] == pytest.approx(1 / 90)
    spindle = library["spindle_vfd_22kw"]
    assert spindle["motor"]["rated_torque"] * 1257.0 == pytest.approx(2200, rel=0.05)


def test_library_has_no_vendor_names_and_valid_ids() -> None:
    # REQ-VD-05: bez nazw producentów (pełna kontrola: tests/test_ip_guard.py)
    for path in LIBRARY_DIR.glob("*.yaml"):
        assert re.fullmatch(r"[a-z][a-z0-9_]{1,47}\.yaml", path.name)


def test_library_rejects_bad_files(tmp_path: Path, servo: dict) -> None:
    (tmp_path / "servo_400w.yaml").write_text(yaml.safe_dump(servo), encoding="utf-8")
    assert set(load_library(tmp_path)) == {"servo_400w"}
    servo["id"] = "inny_id"
    (tmp_path / "servo_400w.yaml").write_text(yaml.safe_dump(servo), encoding="utf-8")
    with pytest.raises(TemplateError, match="nazwa pliku musi odpowiadać id"):
        load_library(tmp_path)
    (tmp_path / "servo_400w.yaml").write_text("id: [niedomknięty", encoding="utf-8")
    with pytest.raises(TemplateError, match="niepoprawny YAML"):
        load_library(tmp_path)
    with pytest.raises(TemplateError, match="brak katalogu"):
        load_library(tmp_path / "nie_ma")
    with pytest.raises(TemplateError, match="nie można odczytać"):
        load_template_file(tmp_path / "brak.yaml")


# --- REQ-VD-01: schemat, zakresy, fizyka ---------------------------------------------------


def test_drive_template_schema(library: dict[str, dict]) -> None:
    # REQ-VD-01
    for tpl in library.values():
        assert validate_template(copy.deepcopy(tpl)) == tpl
        assert set(CIA_REQUIRED) <= set(tpl["cia402"]["objects"])
        assert set(tpl["live"]) <= set(LIVE_CAPABLE)
        for key in ("kp_pos", "kv", "ti", "kff_vel", "kff_acc", "vel_filter_hz"):
            assert key in tpl["controller"]
        for key in ("torque_limit_permille", "following_window", "following_window_ms"):
            assert key in tpl["limits"]
        for key in ("brake_present", "brake_release_ms", "brake_engage_ms", "torque_curve",
                    "rotor_inertia", "torque_constant", "rated_current", "peak_current",
                    "encoder_counts_per_rev"):
            assert key in tpl["motor"]
        for key in ("quick_stop_option", "fault_reaction_option", "brake_on_fault"):
            assert key in tpl["reactions"]


def test_drive_template_schema_reports_polish_errors_with_paths(servo: dict) -> None:
    # REQ-VD-01: wszystkie błędy naraz, ze ścieżką pola, po polsku
    bad = copy.deepcopy(servo)
    bad["motor"]["rated_torque"] = -1
    bad["motor"]["rotor_inertia"] = "1e-4"
    bad["controller"]["kff_vel"] = 3.5
    del bad["limits"]["following_window"]
    bad["reactions"]["quick_stop_option"] = 7
    bad["motor"]["bogus"] = 1
    bad["type"] = "serwo_magiczne"
    with pytest.raises(TemplateError) as err:
        validate_template(bad)
    paths = {i.path: i.message for i in err.value.issues}
    assert "poza zakresem" in paths["motor.rated_torque"]
    assert "tekstem" in paths["motor.rotor_inertia"]
    assert "poza zakresem [0; 2]" in paths["controller.kff_vel"]
    assert paths["limits.following_window"] == "brak wymaganego pola"
    assert "dozwolone: 1, 2" in paths["reactions.quick_stop_option"]
    assert paths["motor.bogus"] == "nieznane pole"
    assert "nieznany typ" in paths["type"]
    assert "motor.rated_torque:" in str(err.value)


@pytest.mark.parametrize(
    ("path", "value", "fragment"),
    [
        (("motor", "torque_curve"), [[0, 1]], "2..16 punktów"),
        (("motor", "torque_curve"), [[0, 1], [0, 2]], "omega musi rosnąć"),
        (("motor", "torque_curve"), [[5, 1], [10, 2]], "zaczynać się od omega = 0"),
        (("motor", "torque_curve"), [[0, 1], [10, -2]], "nie mogą być ujemne"),
        (("motor", "torque_curve"), [[0, 3.8], [10, 99.0]], "przekraczać momentu szczytowego"),
        (("motor", "peak_torque"), 0.5, "nie może być mniejszy od znamionowego"),
        (("motor", "torque_constant"), 0.9, "niespójne"),
        (("motor", "encoder_counts_per_rev"), 3200.5, "liczba całkowita"),
        (("motor", "brake_present"), "tak", "logiczna"),
        (("limits", "torque_limit_permille"), 9000, "przekracza moment szczytowy"),
        (("electrical", "supply_voltage"), 1000.0, "poza 0,1..1,5"),
        (("mechanics", "friction_static"), 0.001, "mniejsze od tarcia Coulomba"),
        (("mechanics", "ratio"), 0, "poza zakresem"),
        (("cia402", "objects"), ["6040h"], "brak wymaganych obiektów"),
        (("cia402", "objects"), [*CIA_REQUIRED, "9999h"], "nieobsługiwane obiekty"),
        (("live",), ["motor.rated_torque"], "nie może być zmieniany w locie"),
        (("live",), "mechanics.load", "lista ścieżek"),
        (("id",), "Zły Id", "identyfikator"),
        (("version",), 0, "wersja"),
        (("based_on",), 5, "szablonu źródłowego"),
        (("name",), "  ", "niepusty tekst"),
    ],
)
def test_drive_template_schema_rejects(servo: dict, path: tuple[str, ...], value: object,
                                       fragment: str) -> None:
    # REQ-VD-01
    node = servo
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    issues = template_issues(servo)
    assert issues, "szablon powinien zostać odrzucony"
    assert any(fragment in i.message for i in issues), [str(i) for i in issues]


def test_drive_template_schema_type_rules(library: dict[str, dict]) -> None:
    # REQ-VD-01: typy krokowe wymagają sekcji stepper, pozostałe jej zabraniają
    stepper = copy.deepcopy(library["stepper_nema23_3nm"])
    del stepper["stepper"]
    assert any("wymaga sekcji stepper" in i.message for i in template_issues(stepper))
    stepper["stepper"] = {"full_steps_per_rev": 202, "damping_ratio": 0.2}
    assert any("wielokrotnością 4" in i.message for i in template_issues(stepper))
    stepper["stepper"] = {"full_steps_per_rev": 200, "damping_ratio": 0.2}
    stepper["motor"]["encoder_counts_per_rev"] = 3210
    assert any("mikrokroków" in i.message for i in template_issues(stepper))
    servo = copy.deepcopy(library["servo_400w"])
    servo["stepper"] = {"full_steps_per_rev": 200, "damping_ratio": 0.2}
    assert any("dotyczy tylko krokowców" in i.message for i in template_issues(servo))
    rotary = copy.deepcopy(library["spindle_vfd_22kw"])
    rotary["mechanics"]["kind"] = "linear"
    assert any("wymaga osi obrotowej" in i.message for i in template_issues(rotary))
    real = copy.deepcopy(library["servo_400w"])
    real["real"] = {"lcec": {}}
    assert any(i.path == "real.driver" for i in template_issues(real))  # sesja 061: walidacja
    assert template_issues("nie słownik")[0].message.startswith("szablon musi być słownikiem")


def test_drive_template_json_schema_file_is_current() -> None:
    # REQ-VD-01: plik JSON Schema generowany z tabeli parametrów
    path = LIBRARY_DIR / "drive_template.schema.json"
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == json_schema()
    assert on_disk["additionalProperties"] is False
    assert "motor" in on_disk["required"] and "stepper" not in on_disk["required"]


def test_drive_template_physics(library: dict[str, dict]) -> None:
    # REQ-VD-01: większe J → mniejsze maks. przyspieszenie zgodnie ze wzorem a = T·ratio/J
    for tpl in library.values():
        mech = tpl["mechanics"]
        base = max_acceleration(tpl)
        j1 = total_inertia(tpl)
        heavy_load = mech["load"] * 4.0
        j2 = total_inertia(tpl, heavy_load)
        heavy = max_acceleration(tpl, load=heavy_load)
        assert j2 > j1
        assert heavy < base
        assert heavy / base == pytest.approx(j1 / j2, rel=1e-12)
        expected = tpl["motor"]["torque_curve"][0][1] / j1 * mech["ratio"]
        assert base == pytest.approx(expected, rel=1e-12)
    servo = library["servo_400w"]
    j = servo["motor"]["rotor_inertia"] + servo["mechanics"]["j_screw"]
    assert total_inertia(servo, 0.0) == pytest.approx(j)
    # J wirnika (REQ: „J” w locie) zmienia przyspieszenie tak samo
    bigger = copy.deepcopy(servo)
    bigger["motor"]["rotor_inertia"] *= 3
    assert max_acceleration(bigger) < max_acceleration(servo)


def test_drive_template_physics_curve_and_supply(library: dict[str, dict]) -> None:
    # REQ-VD-01: moment dostępny z krzywej (interpolacja) i napięcie zasilania
    servo = library["servo_400w"]
    assert available_torque(servo, 0.0) == pytest.approx(3.8)
    assert available_torque(servo, 257.0) == pytest.approx((3.8 + 1.9) / 2)  # środek 200..314
    assert available_torque(servo, -257.0) == pytest.approx((3.8 + 1.9) / 2)
    assert available_torque(servo, 600.0) == 0.0
    assert available_torque(servo, 0.0, supply_scale=0.5) == pytest.approx(1.9)


@pytest.mark.skipif(not HAS_TOOLCHAIN, reason="brak make i kompilatora C")
def test_drive_template_accepted_by_c_core(library: dict[str, dict], check_tool: Path) -> None:
    # REQ-VD-01: szablony przechodzą walidatory rdzenia C i działają w pętli napęd+oś
    for tpl_id, tpl in library.items():
        run = subprocess.run([str(check_tool), "--simulate"], input=c_check_input(tpl),
                             capture_output=True, text=True, check=False)
        assert run.returncode == 0, f"{tpl_id}: {run.stdout}{run.stderr}"
        sim = re.search(r"SIM state=(\d+) fault=(\d+) err_counts=(-?\d+) lost_steps=(-?\d+)",
                        run.stdout)
        assert sim, f"{tpl_id}: {run.stdout}"
        state, fault, err, lost = (int(x) for x in sim.groups())
        assert state == 4, tpl_id  # OPERATION_ENABLED
        assert fault == 0 and lost == 0, tpl_id
        counts = tpl["motor"]["encoder_counts_per_rev"]
        assert abs(err) <= counts * 0.01, f"{tpl_id}: błąd {err} imp"


@pytest.mark.skipif(not HAS_TOOLCHAIN, reason="brak make i kompilatora C")
def test_c_validators_reject_what_python_rejects(library: dict[str, dict],
                                                 check_tool: Path) -> None:
    # REQ-VD-01: narzędzie C zgłasza błąd po polsku dla niepoprawnych parametrów
    tpl = copy.deepcopy(library["servo_400w"])
    text = c_check_input(tpl).replace("drive.rated_torque 1.27", "drive.rated_torque -1.0")
    run = subprocess.run([str(check_tool)], input=text, capture_output=True, text=True,
                         check=False)
    assert run.returncode == 1 and run.stdout.startswith("ERR drive:")
    run = subprocess.run([str(check_tool)], input="zepsute\n", capture_output=True, text=True,
                         check=False)
    assert run.returncode == 2 and run.stdout.startswith("ERR input:")


# --- REQ-VD-02: instancje i nadpisania -----------------------------------------------------


def test_drive_instance_overrides(library: dict[str, dict]) -> None:
    # REQ-VD-02
    inst = resolve_instance(
        {"id": "X1", "template": "servo_400w",
         "overrides": {"mechanics": {"load": 150.0}, "controller.kv": 0.05}},
        library)
    assert inst.id == "X1" and inst.template_id == "servo_400w"
    assert inst.params["mechanics"]["load"] == 150.0
    assert inst.params["controller"]["kv"] == 0.05
    assert inst.overrides == {"mechanics.load": 150.0, "controller.kv": 0.05}
    assert library["servo_400w"]["mechanics"]["load"] == 80.0  # szablon nietknięty
    plain = resolve_instance({"id": "Y1", "template": "servo_400w"}, library)
    assert plain.params == library["servo_400w"] and plain.overrides == {}


def test_drive_instance_overrides_use_template_ranges(library: dict[str, dict]) -> None:
    # REQ-VD-02: te same zakresy co szablon, ścieżka z indeksem instancji
    with pytest.raises(TemplateError) as err:
        resolve_instance({"id": "X1", "template": "servo_400w",
                          "overrides": {"mechanics": {"load": -5}, "controller": {"kff_vel": 9}}},
                         library, "drives[2]")
    paths = {i.path for i in err.value.issues}
    assert paths == {"drives[2].overrides.mechanics.load", "drives[2].overrides.controller.kff_vel"}
    assert all("poza zakresem" in i.message for i in err.value.issues)


def test_drive_instance_overrides_cross_field_and_unknown(library: dict[str, dict]) -> None:
    # REQ-VD-02: reguły między polami po nadpisaniu; nieznane i niedozwolone nadpisania
    with pytest.raises(TemplateError, match="po zastosowaniu nadpisań"):
        apply_overrides(library["servo_400w"], {"motor.peak_torque": 0.5})
    with pytest.raises(TemplateError, match="nieznany parametr do nadpisania"):
        apply_overrides(library["servo_400w"], {"mechanics": {"loadd": 1}})
    with pytest.raises(TemplateError, match="nie podlega nadpisaniu"):
        apply_overrides(library["servo_400w"], {"type": "stepper_open"})
    with pytest.raises(TemplateError, match="sekcja nadpisań"):
        apply_overrides(library["servo_400w"], {"mechanics": 5})
    with pytest.raises(TemplateError, match="musi być słownikiem"):
        apply_overrides(library["servo_400w"], [1, 2])


def test_drive_instance_entry_errors(library: dict[str, dict]) -> None:
    # REQ-VD-02: nieznany szablon wymienia dostępne; powtórzone id; zły wpis
    with pytest.raises(TemplateError) as err:
        resolve_instance({"id": "X1", "template": "nie_ma"}, library)
    assert "nieznany szablon" in str(err.value) and "servo_400w" in str(err.value)
    with pytest.raises(TemplateError, match="powtórzony identyfikator"):
        resolve_instances([{"id": "X", "template": "servo_400w"},
                           {"id": "X", "template": "servo_750w"}], library)
    with pytest.raises(TemplateError, match="musi być listą"):
        resolve_instances({"id": "X"}, library)
    with pytest.raises(TemplateError, match="musi być słownikiem"):
        resolve_instance("X1", library)
    with pytest.raises(TemplateError, match="nieznane pole instancji"):
        resolve_instance({"id": "X", "template": "servo_400w", "x": 1}, library)
    insts = resolve_instances([{"id": "X", "template": "servo_400w"},
                               {"id": "Y", "template": "stepper_nema23_3nm"}], library)
    assert list(insts) == ["X", "Y"]


# --- REQ-VD-03: kopiowanie -----------------------------------------------------------------


def test_drive_clone_independent(library: dict[str, dict], tmp_path: Path) -> None:
    # REQ-VD-03: kopia szablonu jest niezależna od oryginału
    original = copy.deepcopy(library["servo_400w"])
    clone = clone_template(library["servo_400w"], "moje_serwo")
    assert clone["id"] == "moje_serwo" and clone["version"] == 1
    assert clone["based_on"] == "servo_400w"
    assert clone["motor"]["torque_curve"] == original["motor"]["torque_curve"]
    clone["motor"]["torque_curve"][0][1] = 1.0  # modyfikacja kopii (lista zagnieżdżona)
    clone["mechanics"]["load"] = 999.0
    clone["live"].append("x")
    assert library["servo_400w"] == original
    # zapis i ponowne wczytanie: pliki niezależne
    clone2 = clone_template(library["servo_400w"], "moje_serwo")
    path = save_template(clone2, tmp_path)
    assert path == tmp_path / "moje_serwo.yaml"
    reloaded = load_template_file(path)
    assert reloaded == clone2
    reloaded["mechanics"]["load"] = 5.0
    assert load_template_file(path)["mechanics"]["load"] == 80.0
    assert "przykładowe" in path.read_text(encoding="utf-8")


def test_drive_clone_of_instance_bakes_overrides(library: dict[str, dict]) -> None:
    # REQ-VD-03: kopia instancji = szablon z nadpisaniami, based_on = szablon źródłowy
    inst = resolve_instance({"id": "X1", "template": "servo_400w",
                             "overrides": {"mechanics.load": 150.0}}, library)
    clone = clone_instance(inst, "serwo_ciezkie")
    assert clone["mechanics"]["load"] == 150.0
    assert clone["based_on"] == "servo_400w" and clone["version"] == 1
    clone["mechanics"]["load"] = 1.0
    assert inst.params["mechanics"]["load"] == 150.0


def test_drive_clone_rules(library: dict[str, dict], tmp_path: Path) -> None:
    # REQ-VD-03: zły id, nadpisanie istniejącego, błąd zapisu
    with pytest.raises(TemplateError, match="identyfikator"):
        clone_template(library["servo_400w"], "Zły Id")
    new = clone_template(library["servo_400w"], "kopia_a")
    save_template(new, tmp_path)
    with pytest.raises(TemplateError, match="już istnieje"):
        save_template(new, tmp_path)
    save_template(new, tmp_path, overwrite=True)
    blocker = tmp_path / "plik"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(TemplateError, match="nie można zapisać"):
        save_template(new, blocker)
    assert lib_mod.LIBRARY_DIR == LIBRARY_DIR


def test_drive_clone_cli(tmp_path: Path, library: dict[str, dict],
                         capsys: pytest.CaptureFixture[str]) -> None:
    # REQ-VD-03: `python -m linumert_plant drive clone` dla szablonu i instancji
    for tpl_id in ("servo_400w", "servo_750w"):
        save_template(library[tpl_id], tmp_path)
    assert cli_main(["drive", "--dir", str(tmp_path), "clone", "servo_400w", "kopia_cli"]) == 0
    assert "Zapisano" in capsys.readouterr().out
    clone = load_template_file(tmp_path / "kopia_cli.yaml")
    assert clone["based_on"] == "servo_400w"
    assert cli_main(["drive", "--dir", str(tmp_path), "clone", "servo_400w", "kopia_cli"]) == 1
    assert "już istnieje" in capsys.readouterr().err
    assert cli_main(["drive", "--dir", str(tmp_path), "clone", "servo_400w", "kopia_cli",
                     "--force"]) == 0
    capsys.readouterr()
    machine_dir = tmp_path / "maszyna"
    machine_dir.mkdir()
    machine = machine_dir / "machine.yaml"
    machine.write_text(yaml.safe_dump({"drives": [
        {"id": "X1", "template": "servo_750w", "overrides": {"mechanics": {"load": 300.0}}}]}),
        encoding="utf-8")
    assert cli_main(["drive", "--dir", str(tmp_path), "clone", "X1", "z_instancji",
                     "--machine", str(machine), "--name", "Ciężka oś X"]) == 0
    from_instance = load_template_file(tmp_path / "z_instancji.yaml")
    assert from_instance["mechanics"]["load"] == 300.0
    assert from_instance["based_on"] == "servo_750w" and from_instance["name"] == "Ciężka oś X"
    assert cli_main(["drive", "--dir", str(tmp_path), "clone", "Z9", "x_y",
                     "--machine", str(machine)]) == 1
    assert "brak instancji" in capsys.readouterr().err
    assert cli_main(["drive", "--dir", str(tmp_path), "clone", "nie_ma", "x_y"]) == 1
    assert "Nieznany szablon" in capsys.readouterr().err
    missing = tmp_path / "brak.yaml"
    assert cli_main(["drive", "--dir", str(tmp_path), "clone", "X1", "x_y", "--machine",
                     str(missing)]) == 1
    capsys.readouterr()


def test_drive_cli_list_show_validate_schema(capsys: pytest.CaptureFixture[str],
                                              tmp_path: Path) -> None:
    # REQ-VD-03/05: polecenia pomocnicze CLI
    assert cli_main(["drive", "list"]) == 0
    out = capsys.readouterr().out
    assert all(tpl_id in out for tpl_id in EXPECTED_IDS)
    assert cli_main(["drive", "show", "servo_400w"]) == 0
    assert "torque_curve" in capsys.readouterr().out
    assert cli_main(["drive", "show", "nie_ma"]) == 1
    capsys.readouterr()
    assert cli_main(["drive", "validate", str(LIBRARY_DIR / "servo_400w.yaml")]) == 0
    assert "OK: servo_400w" in capsys.readouterr().out
    bad = tmp_path / "zly.yaml"
    bad.write_text("id: zly\n", encoding="utf-8")
    assert cli_main(["drive", "validate", str(bad)]) == 1
    assert "brak wymaganej sekcji" in capsys.readouterr().err
    assert cli_main(["drive", "schema"]) == 0
    assert json.loads(capsys.readouterr().out)["title"].startswith("Szablon napędu")


# --- REQ-VD-04: parametry live -------------------------------------------------------------


def test_live_params(servo: dict) -> None:
    # REQ-VD-04: zmiana w locie, walidacja zakresów, dziennik z czasem
    live = LiveParams(servo)
    first = live.set("mechanics.load", 160.0, t=1.5)
    second = live.set("motor.rotor_inertia", 6.0e-5, t=2.0)
    live.set("electrical.supply_voltage", 115.0, t=2.0)
    assert (first.t, first.path, first.old, first.new) == (1.5, "mechanics.load", 80.0, 160.0)
    assert second.old == 3.0e-5 and second.new == 6.0e-5
    assert live.get("mechanics.load") == 160.0
    assert [r.t for r in live.log] == [1.5, 2.0, 2.0]
    assert live.log_as_dicts()[0] == {"t": 1.5, "path": "mechanics.load", "old": 80.0, "new": 160.0}
    assert servo["mechanics"]["load"] == 80.0  # słownik wejściowy nietknięty


def test_live_params_rejections_leave_state_unchanged(servo: dict) -> None:
    # REQ-VD-04: błędna zmiana nie zmienia wartości ani dziennika
    live = LiveParams(servo)
    live.set("mechanics.load", 100.0, t=1.0)
    snapshot = copy.deepcopy(live.params)
    cases = [
        ("motor.rated_torque", 2.0, 2.0, "nie jest oznaczony jako live"),
        ("mechanics.load", -1.0, 2.0, "poza zakresem"),
        ("mechanics.friction_coulomb", 5.0, 2.0, "mniejsze od tarcia Coulomba"),
        ("electrical.supply_voltage", 9999.0, 2.0, "poza zakresem"),
        ("mechanics.load", 90.0, 0.5, "cofać"),
        ("mechanics.load", 90.0, -1.0, "czas zmiany"),
        ("mechanics.load", "dużo", 2.0, "tekstem"),
    ]
    for path, value, t, fragment in cases:
        with pytest.raises(TemplateError, match=fragment):
            live.set(path, value, t=t)
    assert live.params == snapshot
    assert len(live.log) == 1


def test_live_params_only_marked_parameters(library: dict[str, dict]) -> None:
    # REQ-VD-04: parametry bez znacznika live wymagają przeładowania modelu
    tpl = copy.deepcopy(library["spindle_vfd_22kw"])
    assert "mechanics.backlash" not in tpl["live"]
    live = LiveParams(tpl)
    with pytest.raises(TemplateError, match="przeładowania modelu"):
        live.set("mechanics.backlash", 0.001, t=0.0)
    live.set("mechanics.friction_viscous", 3.0e-4, t=0.0)


def test_live_params_c_mapping(servo: dict) -> None:
    # REQ-VD-04: mapowanie na rdzeń C; napięcie jako mnożnik znamionowego
    live = LiveParams(servo)
    assert live.c_command("mechanics.load", 120.0) == ("LRT_LIVE_LOAD", 120.0)
    target, value = live.c_command("electrical.supply_voltage", 115.0)
    assert target == "LRT_LIVE_SUPPLY_SCALE" and value == pytest.approx(0.5)
    assert live.c_command("limits.torque_limit_permille", 800) == ("LRT_LIVE_TORQUE_LIMIT", 800.0)
    assert set(LIVE_TO_C) == set(LIVE_CAPABLE)
    header = (CORE / "live.h").read_text(encoding="utf-8")
    for target in LIVE_TO_C.values():
        assert re.search(rf"\b{target}\b", header), target
    drive_c = (CORE / "drive.c").read_text(encoding="utf-8")
    assert "case LRT_LIVE_TORQUE_LIMIT" in drive_c


def test_live_to_c_resolves_two_body_for_live_backlash(library: dict[str, dict]) -> None:
    # REQ-VD-04: luz live wymaga modelu dwuczłonowego od startu (sztywność > 0)
    from linumert_plant.drive_template import to_c_params

    tpl = copy.deepcopy(library["spindle_vfd_22kw"])
    tpl["live"] = [*tpl["live"], "mechanics.backlash"]
    assert to_c_params(tpl)["axis"]["stiffness"] == 1000.0
    tpl["live"].remove("mechanics.backlash")
    assert to_c_params(tpl)["axis"]["stiffness"] == 0.0


def test_instances_in_machine_file_roundtrip(library: dict[str, dict], tmp_path: Path) -> None:
    # REQ-VD-02: fragment machine.yaml z listą drives: rozwiązuje się do instancji
    text = """
drives:
  - {id: X1, template: servo_400w}
  - id: Y1
    template: stepper_nema34_85nm
    overrides: {mechanics: {load: 200.0}, stepper.damping_ratio: 0.3}
"""
    entries = yaml.safe_load(text)["drives"]
    insts = resolve_instances(entries, library)
    assert insts["Y1"].params["stepper"]["damping_ratio"] == 0.3
    assert insts["Y1"].params["mechanics"]["load"] == 200.0
