"""Testy katalogu alarmow i managera. Model-Author: Claude.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import threading

import pytest

from linumert.alarms import Alarm, AlarmManager, AlarmState, CatalogError, load_catalog

REQUIRED = (
    ["W-2104", "W-2105", "W-2110", "W-2120", "W-2130"]
    + ["E-1000", "E-1001", "E-1100", "E-1200"]
    + [f"E-{n}" for n in range(4000, 4011)]
    + [f"E-{n}" for n in range(4100, 4106)]
    + [f"E-{n}" for n in range(4200, 4211)]
    + ["K-301", "K-302", "K-303", "K-304", "K-305", "K-306", "K-307", "K-308", "K-309",
       "K-310", "K-311", "K-320", "K-321", "K-322"]
    + [f"P-{n}" for n in range(5001, 5011)]
)


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def manager(**kwargs):
    return AlarmManager(clock=kwargs.pop("clock", Clock()), **kwargs)


def write_catalog(tmp_path, text):
    path = tmp_path / "catalog.yaml"
    path.write_text(text, encoding="utf-8")
    return path


GOOD = '- {code: W-2104, clear: ack, params: [axis], pl: "Os {axis}.", en: "Axis {axis}."}\n'


# ---- katalog -------------------------------------------------------------
def test_default_catalog_has_all_required_codes():
    catalog = load_catalog()
    missing = [code for code in REQUIRED if code not in catalog]
    assert not missing and len(catalog) >= len(REQUIRED)


def test_every_alarm_has_both_languages_and_matching_placeholders():
    for definition in load_catalog():
        assert set(definition.texts) == {"pl", "en"}, definition.code
        assert definition.texts["pl"].strip() and definition.texts["en"].strip()


def test_levels_follow_code_prefix():
    catalog = load_catalog()
    assert catalog.get("W-2104").level == "warning"
    assert catalog.get("E-4003").level == "error"
    assert catalog.get("K-301").level == "simulation"
    assert catalog.get("P-5010").level == "program"


def test_format_in_both_languages_and_errors():
    catalog = load_catalog()
    assert catalog.format("W-2104", "pl", axis="X") == "Oś X nie jest zbazowana."
    assert catalog.format("W-2104", "en", axis="X") == "Axis X is not homed."
    with pytest.raises(ValueError, match="axis"):
        catalog.format("W-2104")
    with pytest.raises(KeyError):
        catalog.format("W-9999")
    with pytest.raises(KeyError):
        catalog.format("W-2104", "de", axis="X")


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        (GOOD + GOOD, "powtorzony"),
        ('- {code: W-1, clear: ack, params: [], pl: "a", en: "b"}\n', "niepoprawny kod"),
        ('- {code: W-2104, clear: ack, params: [], pl: "a"}\n', "brak tekstu en"),
        ('- {code: W-2104, clear: zzz, params: [], pl: "a", en: "b"}\n', "clear"),
        ('- {code: W-2104, clear: ack, params: [], pl: "{x}", en: "b"}\n', "pola tekstu pl"),
        ('- {code: W-2104, clear: ack, params: [], pl: "{}", en: "b"}\n', "niedozwolone"),
        ("klucz: wartosc\n", "listy"),
    ],
)
def test_invalid_catalogs_are_rejected_with_reason(tmp_path, text, fragment):
    with pytest.raises(CatalogError, match=fragment):
        load_catalog(write_catalog(tmp_path, text))


# ---- manager -------------------------------------------------------------
def test_raise_alarm_and_localized_message():
    mgr = manager()
    alarm = mgr.raise_alarm("E-4201", axis="X", error=0.5, limit=0.2)
    assert alarm.state is AlarmState.ACTIVE and alarm.id == 1
    assert "X" in mgr.message(alarm, "pl") and "Following error" in mgr.message(alarm, "en")
    assert [item.id for item in mgr.active()] == [1]


def test_repeated_identical_alarm_increments_count_only():
    mgr = manager()
    mgr.raise_alarm("W-2104", axis="X")
    again = mgr.raise_alarm("W-2104", axis="X")
    other = mgr.raise_alarm("W-2104", axis="Y")
    assert again.count == 2 and other.id != again.id
    assert len(mgr.active()) == 2


def test_unknown_code_and_missing_params_are_rejected():
    mgr = manager()
    with pytest.raises(KeyError):
        mgr.raise_alarm("E-0000")
    with pytest.raises(ValueError, match="axis"):
        mgr.raise_alarm("W-2104")
    assert mgr.active() == []


def test_ack_clears_ack_class_but_only_marks_reset_class():
    mgr = manager()
    sim = mgr.raise_alarm("K-321")
    drive = mgr.raise_alarm("E-4003", ms=50)
    assert mgr.acknowledge(sim.id) and mgr.acknowledge(drive.id)
    assert mgr.acknowledge(999) is False
    assert [a.code for a in mgr.active()] == ["E-4003"]
    assert mgr.active()[0].state is AlarmState.ACKNOWLEDGED
    assert [a.code for a in mgr.history()] == ["K-321"]


def test_reset_clears_only_reset_class_alarms():
    mgr = manager()
    mgr.raise_alarm("E-4003", ms=50)
    mgr.raise_alarm("E-1100")
    mgr.raise_alarm("W-2104", axis="X")
    mgr.raise_alarm("W-2105", axis="X", distance=1.0)  # auto: kasuje je zrodlo
    assert mgr.reset() == 2
    assert sorted(a.code for a in mgr.active()) == ["W-2104", "W-2105"]


def test_clear_by_code_by_id_and_argument_validation():
    mgr = manager()
    first = mgr.raise_alarm("W-2105", axis="X", distance=1.0)
    mgr.raise_alarm("W-2105", axis="Y", distance=2.0)
    assert mgr.clear(alarm_id=first.id) == 1
    assert mgr.clear(code="W-2105") == 1
    assert mgr.clear(code="W-2105") == 0
    with pytest.raises(ValueError):
        mgr.clear()
    with pytest.raises(ValueError):
        mgr.clear(code="W-2105", alarm_id=1)


def test_history_is_newest_first_limited_and_trimmed():
    mgr = manager(history_limit=3)
    for number in range(5):
        mgr.raise_alarm("P-5009", name=f"k{number}")
    mgr.acknowledge_all()
    names = [a.params["name"] for a in mgr.history()]
    assert names == ["k4", "k3", "k2"]
    assert len(mgr.history(limit=1)) == 1


def test_timestamps_come_from_injected_clock():
    clock = Clock()
    mgr = manager(clock=clock)
    alarm = mgr.raise_alarm("E-4003", ms=50)
    clock.now = 105.0
    mgr.acknowledge(alarm.id)
    clock.now = 110.0
    mgr.reset()
    done = mgr.history()[0]
    assert (done.raised_at, done.acknowledged_at, done.cleared_at) == (100.0, 105.0, 110.0)
    assert done.state is AlarmState.CLEARED


def test_listeners_get_events_and_failures_do_not_break_state():
    mgr = manager()
    events = []
    mgr.subscribe(lambda event, alarm: events.append((event, alarm.code)))

    def broken(event, alarm):
        raise RuntimeError("blad sluchacza")

    mgr.subscribe(broken)
    alarm = mgr.raise_alarm("K-321")
    mgr.raise_alarm("K-321")
    mgr.acknowledge(alarm.id)
    assert events == [("raised", "K-321"), ("repeated", "K-321"), ("cleared", "K-321")]
    assert mgr.active() == []


def test_worst_level_prefers_error_then_program_then_warning():
    mgr = manager()
    assert mgr.worst_level() is None
    mgr.raise_alarm("W-2120")
    assert mgr.worst_level() == "warning"
    mgr.raise_alarm("P-5009", name="a")
    assert mgr.worst_level() == "program"
    mgr.raise_alarm("E-1100")
    assert mgr.worst_level() == "error"


def test_returned_alarms_are_copies():
    mgr = manager()
    alarm = mgr.raise_alarm("W-2104", axis="X")
    alarm.params["axis"] = "Z"
    alarm.state = AlarmState.CLEARED
    stored = mgr.active()[0]
    assert stored.params["axis"] == "X" and stored.state is AlarmState.ACTIVE
    assert isinstance(stored, Alarm)


def test_manager_is_safe_across_threads():
    mgr = manager()

    def worker(index):
        for number in range(100):
            mgr.raise_alarm("P-5009", name=f"{index}-{number}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(mgr.active()) == 800
    assert len({a.id for a in mgr.active()}) == 800
