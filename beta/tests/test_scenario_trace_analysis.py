"""Offline phase inference must not hide gaps or compare different row sets. Model-Author: Codex."""

import json

import pytest

from linumert_plant.scenario_trace import channels
from linumert_plant.scenario_trace_analysis import analyze, main


def fixture_trace(work):
    columns = ["sample", *[c[0] for c in channels()]]
    rows = []
    for i in range(8):
        row = dict.fromkeys(columns, 0.0)
        row.update({"sample": i, "j0.pos-cmd": i*i, "j0.pos-fb": i*i / 2,
                    "j0.f-error": (i-1)**2 / 2 if i else 0, "j0.drive-enabled": 1})
        rows.append(" ".join(str(row[c]) for c in columns))
    # Sampler sequence numbers are integers, unlike the sampled float channels.
    rows = [str(i) + " " + line.split(" ", 1)[1] for i, line in enumerate(rows)]
    (work / "servo_trace.txt").write_text("\n".join(rows) + "\n")
    (work / "servo_trace.json").write_text(json.dumps(
        {"valid": True, "columns": columns, "samples": len(rows)}))


def test_accelerating_synthetic_trace_identifies_previous_cycle(tmp_path):
    fixture_trace(tmp_path)
    result = analyze(tmp_path)
    assert result["selected_samples"] == 6
    residuals = result["residuals"]
    assert residuals[1]["max_abs_residual_mm"] == 0
    assert residuals[0]["max_abs_residual_mm"] > 0
    assert residuals[2]["max_abs_residual_mm"] > 0
    assert result["peak_row"]["sample"] == 7


@pytest.mark.parametrize("damage", ["gap", "stale_count", "invalid_meta", "schema"])
def test_refuses_incomplete_or_inconsistent_evidence(tmp_path, damage):
    fixture_trace(tmp_path)
    meta = tmp_path / "servo_trace.json"
    data = json.loads(meta.read_text())
    if damage == "gap":
        path = tmp_path / "servo_trace.txt"
        path.write_text(path.read_text().replace("3 ", "30 ", 1))
    elif damage == "stale_count":
        data["samples"] = 999
    elif damage == "invalid_meta":
        data["valid"] = False
    else:
        data["columns"] = data["columns"][1:]
    meta.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="integrity mismatch"):
        analyze(tmp_path)


def test_cli_rejects_unrecorded_joint_without_result(tmp_path):
    fixture_trace(tmp_path)
    out = tmp_path / "result.json"
    assert main([str(tmp_path), "--joint", "2", "--out", str(out)]) == 2
    assert not out.exists()


def test_refuses_stationary_trace_without_claiming_phase(tmp_path):
    fixture_trace(tmp_path)
    path = tmp_path / "servo_trace.txt"
    rows = [line.split() for line in path.read_text().splitlines()]
    for row in rows:
        row[1] = "0"  # j0.pos-cmd
    path.write_text("\n".join(" ".join(row) for row in rows) + "\n")
    with pytest.raises(ValueError, match="no enabled moving samples"):
        analyze(tmp_path)
