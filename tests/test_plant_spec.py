"""Spojnosc specyfikacji Plant z wymaganiami i protokolem LRT-NET. Model-Author: Claude.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import re
import struct
import zlib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "docs/wymagania/WIRTUALNA_OBRABIARKA.md"
PLANT = ROOT / "docs/PLANT.md"
MATRIX = ROOT / "docs/wymagania/MACIERZ.md"

HEADER = "<HBBIQBBH"  # magic, version, type, seq, time_ns, n_axes, flags, reserved
CMD_AXIS = "<HbBi"  # controlword, mode, pad, target_pos
CMD_TAIL = "<IfI"  # digital_out, spindle_cmd, crc32
REPLY_AXIS = "<HbBiihH"  # statusword, mode_display, pad, actual_pos, following_error, torque, err
REPLY_TAIL = "<IfIIII"  # digital_in, spindle_actual, lost, late, jitter_us, crc32


def requirement_ids():
    text = REQUIREMENTS.read_text(encoding="utf-8")
    return re.findall(r"^\| (REQ-[A-Z]+-\d+) ", text, flags=re.M)


def test_requirements_are_found():
    assert len(requirement_ids()) == 22


@pytest.mark.parametrize("document", [PLANT, MATRIX])
def test_every_requirement_is_covered_in_spec_and_matrix(document):
    text = document.read_text(encoding="utf-8")
    missing = [rid for rid in requirement_ids() if rid not in text]
    assert not missing, f"{document.name}: brak {missing}"


def test_matrix_rows_match_requirements_table():
    rows = re.findall(r"^\| (REQ-[A-Z]+-\d+) \| (.+?) \| (.+?) \| (\w+) \|$",
                      MATRIX.read_text(encoding="utf-8"), flags=re.M)
    assert [row[0] for row in rows] == requirement_ids()
    assert all(row[3] == "planowane" for row in rows)


def test_yaml_examples_in_spec_parse():
    blocks = re.findall(r"```yaml\n(.*?)```", PLANT.read_text(encoding="utf-8"), flags=re.S)
    assert len(blocks) >= 3
    for block in blocks:
        assert isinstance(yaml.safe_load(block), dict)


def test_spec_has_mermaid_diagram_and_frame_table():
    text = PLANT.read_text(encoding="utf-8")
    assert "```mermaid" in text and "flowchart" in text
    assert "| 0 | `magic` | u16 |" in text


@pytest.mark.parametrize("axes", [1, 3, 6, 8])
def test_frame_sizes_match_documented_formulas(axes):
    header = struct.calcsize(HEADER)
    assert header == 20
    command = header + axes * struct.calcsize(CMD_AXIS) + struct.calcsize(CMD_TAIL)
    reply = header + axes * struct.calcsize(REPLY_AXIS) + struct.calcsize(REPLY_TAIL)
    assert command == 32 + 8 * axes
    assert reply == 44 + 16 * axes
    if axes == 3:
        assert "56 B w górę, 92 B w dół" in PLANT.read_text(encoding="utf-8")


def test_command_frame_roundtrip_with_crc32():
    body = struct.pack(HEADER, 0x524C, 1, 1, 7, 123456789, 1, 0, 0)
    body += struct.pack(CMD_AXIS, 0x000F, 8, 0, -1500) + struct.pack("<If", 5, 1200.0)
    frame = body + struct.pack("<I", zlib.crc32(body))
    assert len(frame) == 32 + 8
    assert frame[:2] == b"LR"
    (crc,) = struct.unpack_from("<I", frame, len(frame) - 4)
    assert crc == zlib.crc32(frame[:-4])
    assert struct.unpack_from(CMD_AXIS, frame, 20) == (0x000F, 8, 0, -1500)
