"""Protokół LRT-NET w C (hal/lrt_net_proto.h) zgodny bajt w bajt z lrtnet.py (sesja 017).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 017.
Kompiluje hal/tests/lrt_net_proto_cli.c zwykłym kompilatorem C (bez LinuxCNC), z -Werror.
"""

from __future__ import annotations

import shutil
import subprocess
import zlib
from pathlib import Path

import pytest

from linumert_plant.lrtnet import (
    AxisReply,
    Reply,
    decode_command,
    encode_reply,
)

ROOT = Path(__file__).resolve().parents[1]  # beta/ (testy leżą płasko w tests/, jak w głównym repo)
CLI_SRC = ROOT / "hal" / "tests" / "lrt_net_proto_cli.c"


@pytest.fixture(scope="module")
def cli(tmp_path_factory) -> Path:
    cc = shutil.which("cc") or shutil.which("gcc")
    if cc is None:
        pytest.skip("brak kompilatora C")
    out = tmp_path_factory.mktemp("proto") / "lrt_net_proto_cli"
    subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                    str(CLI_SRC), "-o", str(out)], check=True)
    return out


def _run(cli: Path, *args) -> str:
    return subprocess.run([str(cli), *map(str, args)], capture_output=True, text=True,
                          check=True).stdout.strip()


def test_crc32_matches_zlib(cli):
    for data in (b"", b"123456789", bytes(range(256)) * 3):
        assert int(_run(cli, "crc", data.hex())) == zlib.crc32(data)


def test_command_from_c_decodes_in_python(cli):  # REQ-VM-02: master LinuxCNC → Plant
    axes = [(0x000F, 8, 123456), (0x0080, 6, -7), (0x0006, -3, -2147483648)]
    args = [0xFFFFFFFE, 2**40 + 5, len(axes)]
    for cw, mode, target in axes:
        args += [cw, mode, target]
    args += [0xA5A5_0001, 12000.5]
    frame = bytes.fromhex(_run(cli, "cmd", *args))
    cmd = decode_command(frame)
    assert cmd.seq == 0xFFFFFFFE and cmd.time_ns == 2**40 + 5
    assert [(a.controlword, a.mode, a.target_pos) for a in cmd.axes] == axes
    assert cmd.digital_out == 0xA5A5_0001
    assert cmd.spindle_cmd == pytest.approx(12000.5)


def test_reply_from_python_decodes_in_c(cli):
    rep = Reply(seq=77, time_ns=123_456_789, flags=3, digital_in=0x8000_0001,
                spindle_actual=-250.25, frames_lost=4, frames_late=2, jitter_us=17,
                axes=[AxisReply(statusword=0x1637, mode_display=8, actual_pos=-1000,
                                following_error=12, torque_pct=-345, error_code=0x8130),
                      AxisReply(statusword=0x0250, mode_display=6, actual_pos=2**31 - 1,
                                following_error=-2**31, torque_pct=32767, error_code=0)])
    out = _run(cli, "reply", encode_reply(rep).hex()).splitlines()
    assert out[0] == ("seq=77 time=123456789 flags=3 din=2147483649 spindle=-250.250 "
                      "lost=4 late=2 jitter=17")
    assert out[1] == "axis sw=5687 mode=8 pos=-1000 ferr=12 torque=-345 err=33072"
    assert out[2] == "axis sw=592 mode=6 pos=2147483647 ferr=-2147483648 torque=32767 err=0"


def test_reply_errors_detected_in_c(cli):
    rep = Reply(seq=1, time_ns=0, axes=[AxisReply(statusword=0x27)])
    good = bytearray(encode_reply(rep))
    bad_crc = good.copy()
    bad_crc[25] ^= 0xFF
    bad_magic = good.copy()
    bad_magic[0] = 0
    assert _run(cli, "reply", bytes(bad_crc).hex()) == "ERR -6"
    assert _run(cli, "reply", bytes(bad_magic).hex()) == "ERR -2"
    assert _run(cli, "reply", bytes(good[:-1]).hex()) == "ERR -1"
