"""Report acceptance against original real LinuxCNC sim/Plant recordings.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import hashlib
import json
import math
import tarfile
from pathlib import Path, PurePosixPath

import pytest
from linumert.programs import job_report

PROOF = Path(__file__).resolve().parents[1] / "docs/raporty/vertical"
INDEX = json.loads((PROOF / "runs-20261107.json").read_text())
RAW_INDEX = json.loads((PROOF / "report-ferr-acceptance-20261108.json").read_text())


def unpack(archive, output, *, flat=False):
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if not member.isfile():
                continue
            name = PurePosixPath(member.name)
            assert not name.is_absolute() and ".." not in name.parts
            path = output / (name.name if flat else Path(*name.parts))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bundle.extractfile(member).read())


@pytest.fixture(scope="module")
def executions(tmp_path_factory):
    work = tmp_path_factory.mktemp("original-job-executions")
    for target in ("sim", "plant"):
        unpack(PROOF / f"execution-{target}-20261108.tar.gz", work / target)
    return work


@pytest.mark.parametrize("entry", INDEX, ids=[e["archive"] for e in INDEX])
def test_report_matches_original_hashes_and_independent_statistics(entry, executions, tmp_path):
    archive = PROOF / entry["archive"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == entry["archive_sha256"]
    unpack(archive, tmp_path, flat=True)
    for name, digest in entry["files"].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == digest
    report = job_report.build(tmp_path, executions / entry["result"]["target"])
    samples = [json.loads(row) for row in (tmp_path / "samples.jsonl").read_text().splitlines()]
    samples = [r for r in samples if "axes" in r]
    assert report["quality"]["samples"] == len(samples) == entry["result"]["samples"]
    assert report["quality"]["issues"] == []
    for axis in "XYZ":
        values = [r["axes"][axis]["commanded"] - r["axes"][axis]["actual"] for r in samples]
        stat = report["axes"][axis]["following_error"]
        assert stat["max_abs_mm"] == max(map(abs, values))
        assert stat["rms_mm"] == pytest.approx(
            math.sqrt(math.fsum(v*v for v in values) / len(values)), abs=1e-12)
        if "last3_max_abs_axis_error_mm" in entry:
            assert report["positioning"]["last3_max_abs_mm"][axis] == (
                entry["last3_max_abs_axis_error_mm"][axis])
    assert report["execution_status"] == entry["result"]["status"]
    assert report["positioning"]["status"] == (
        "passed" if entry["result"].get("settled_position_observed") else "unavailable")
    assert report["time"]["comparison_available"] == (
        entry["result"]["status"] == "completed_observed")
    if entry["result"]["status"] == "client_lost":
        alarm = report["alarms"][0]
        assert alarm["code"] == "E-1100" and alarm["observed_at_s"] > 8
        assert isinstance(alarm["motion_line"], int) and isinstance(alarm["line"], int)


@pytest.mark.parametrize("entry", RAW_INDEX, ids=[e["case"] for e in RAW_INDEX])
def test_raw_joint_archives_preserve_gaps_and_independent_statistics(entry, executions, tmp_path):
    archive = PROOF / entry["archive"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == entry["archive_sha256"]
    unpack(archive, tmp_path, flat=True)
    for name, digest in entry["files"].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == digest
    report = job_report.build(tmp_path, executions / entry["target"])
    samples = [json.loads(row) for row in (tmp_path / "samples.jsonl").read_text().splitlines()]
    samples = [row for row in samples if "axes" in row]
    raw = report["joint_following_error"]
    assert raw["joint_axes"] == {"0": "X", "1": "Y", "2": "Y", "3": "Z"}
    assert raw["status"] == "available" and raw["samples"] == len(samples)
    for joint, stat in raw["joints"].items():
        values = [row["joint_following_errors"]["values"][int(joint)] for row in samples]
        assert stat["max_abs_mm"] == max(map(abs, values))
        assert stat["rms_mm"] == pytest.approx(math.sqrt(
            math.fsum(value * value for value in values) / len(values)), abs=1e-12)
    assert report["quality"] == entry["quality"]
    assert report["positioning"] == entry["positioning"]
    assert report["time"] == entry["time"]
    assert report["execution_status"] == entry["execution_status"]
    if entry["case"] == "gapped":
        assert report["status"] == "incomplete"
        assert not report["time"]["comparison_available"]
        assert report["positioning"]["status"] == "unavailable"
    from linumert.programs.job import json_text

    assert job_report.load(json_text(report).encode()) == report
