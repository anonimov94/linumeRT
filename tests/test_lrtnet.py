"""Kodek ramek LRT-NET v1 i master testowy — bez rdzenia C (sesja 016).

Model-Author: Claude
"""

from __future__ import annotations

import math
import random
import struct
import zlib

import pytest
from linumert_plant.lrtnet import (
    AxisCommand,
    AxisReply,
    Command,
    FrameError,
    Reply,
    command_size,
    decode_command,
    decode_reply,
    encode_command,
    encode_reply,
    reply_size,
    seq_delta,
)
from test_master import drive_state, trapezoid


def _cmd(n: int = 3, seq: int = 7) -> Command:
    axes = [AxisCommand(0x000F, 8, -1500 + i) for i in range(n)]
    return Command(seq=seq, time_ns=123456789, axes=axes, digital_out=5, spindle_cmd=1200.0)


def test_sizes_match_spec() -> None:
    assert command_size(3) == 56 and reply_size(3) == 92  # docs/PLANT.md §3
    assert len(encode_command(_cmd(3))) == 56
    assert len(encode_reply(Reply(1, 2, [AxisReply()] * 3))) == 92


def test_command_roundtrip_and_layout() -> None:
    frame = encode_command(_cmd())
    assert frame[:2] == b"\x4c\x52"
    assert struct.unpack_from("<HbBi", frame, 20) == (0x000F, 8, 0, -1500)
    (crc,) = struct.unpack_from("<I", frame, len(frame) - 4)
    assert crc == zlib.crc32(frame[:-4])
    back = decode_command(frame)
    assert back == _cmd()


def test_reply_roundtrip_and_clamping() -> None:
    rep = Reply(seq=0xFFFFFFFF, time_ns=2**63, axes=[
        AxisReply(0x0627, 8, -(2**40), 12, 99999, 0x8130)], digital_in=3, spindle_actual=0.5,
        frames_lost=1, frames_late=2, jitter_us=-5, flags=3)
    back = decode_reply(encode_reply(rep))
    axis = back.axes[0]
    assert axis.actual_pos == -(2**31) and axis.torque_pct == 2**15 - 1  # nasycenie, bez wyjątku
    assert axis.error_code == 0x8130 and back.jitter_us == 0 and back.flags == 3
    assert (back.seq, back.time_ns, back.frames_late) == (0xFFFFFFFF, 2**63, 2)


@pytest.mark.parametrize("mutate, reason", [
    (lambda f: b"\x00\x00" + f[2:], "magic"),
    (lambda f: f[:2] + b"\x02" + f[3:], "wersja"),
    (lambda f: f[:3] + b"\x02" + f[4:], "typ"),
    (lambda f: f[:-1], "długość"),
    (lambda f: f[:30] + bytes([f[30] ^ 1]) + f[31:], "CRC"),
    (lambda f: b"", "krótka"),
])
def test_rejects_bad_frames(mutate, reason) -> None:  # REQ-QA-03
    with pytest.raises(FrameError):
        decode_command(mutate(encode_command(_cmd())))


def _resealed(frame: bytes, fmt: str, offset: int, value) -> bytes:
    """Wpisuje pole i przelicza CRC — ramka przechodzi CRC, odrzuca ją dopiero walidacja pól."""
    body = bytearray(frame[:-4])
    struct.pack_into(fmt, body, offset, value)
    return bytes(body) + struct.pack("<I", zlib.crc32(bytes(body)))


# Offsety z docs/PLANT.md §3: reserved @18, pad osi @20+3, spindle za blokami osi + digital u32.
@pytest.mark.parametrize("fmt, offset, value, reason", [
    ("<H", 18, 1, "reserved"),
    ("<B", 20 + 3, 1, "pad"),
    ("<B", 20 + 8 + 3, 1, "pad osi 1"),
    ("<f", 20 + 2 * 8 + 4, math.nan, "spindle_cmd"),
    ("<f", 20 + 2 * 8 + 4, math.inf, "spindle_cmd"),
    ("<f", 20 + 2 * 8 + 4, -math.inf, "spindle_cmd"),
])
def test_command_rejects_invalid_fields(fmt, offset, value, reason) -> None:  # REQ-QA-03
    frame = _resealed(encode_command(_cmd(2)), fmt, offset, value)
    with pytest.raises(FrameError, match=reason):
        decode_command(frame)


@pytest.mark.parametrize("fmt, offset, value, reason", [
    ("<H", 18, 1, "reserved"),
    ("<B", 20 + 3, 1, "pad"),
    ("<f", 20 + 16 + 4, math.nan, "spindle_actual"),
    ("<f", 20 + 16 + 4, math.inf, "spindle_actual"),
])
def test_reply_rejects_invalid_fields(fmt, offset, value, reason) -> None:  # REQ-QA-03
    frame = _resealed(encode_reply(Reply(1, 2, [AxisReply()])), fmt, offset, value)
    with pytest.raises(FrameError, match=reason):
        decode_reply(frame)


def test_rejects_axis_count_out_of_range() -> None:  # REQ-QA-03
    body = bytearray(encode_command(_cmd(1))[:-4])
    body[16] = 9
    with pytest.raises(FrameError, match="liczba osi"):
        decode_command(bytes(body) + struct.pack("<I", zlib.crc32(bytes(body))))
    with pytest.raises(ValueError):
        encode_command(Command(1, 0, []))


def test_fuzz_only_frame_errors() -> None:  # REQ-QA-03
    rng = random.Random(16)
    good = encode_command(_cmd(4))
    for _ in range(3000):
        if rng.random() < 0.5:
            frame = bytes(rng.getrandbits(8) for _ in range(rng.randrange(0, 120)))
        else:
            frame = bytearray(good)
            for _ in range(rng.randrange(1, 4)):
                frame[rng.randrange(len(frame))] = rng.getrandbits(8)
            frame = bytes(frame)
        try:
            decode_command(frame)
        except FrameError:
            pass


def test_seq_delta_wraps() -> None:
    assert seq_delta(1, 0) == 1
    assert seq_delta(0, 0xFFFFFFFF) == 1
    assert seq_delta(5, 0xFFFFFFFE) == 7
    assert seq_delta(3, 3) == 0 and seq_delta(2, 3) == -1


def test_trapezoid_profile() -> None:
    dt, vmax, amax = 1e-3, 100_000.0, 1_000_000.0
    for dist in (50_000, -50_000, 2_000):  # trapez, w drugą stronę, trójkąt
        prof = trapezoid(dist, vmax, amax, dt)
        assert prof[-1] == pytest.approx(dist)
        steps = [b - a for a, b in zip([0.0] + prof[:-1], prof, strict=True)]
        assert max(abs(s) for s in steps) <= vmax * dt * 1.001
        assert all(s * dist >= 0 for s in steps)
    assert trapezoid(0, vmax, amax, dt) == []


def test_drive_state_masks() -> None:
    assert drive_state(0x0250) == "SWITCH_ON_DISABLED"
    assert drive_state(0x0231) == "READY_TO_SWITCH_ON"
    assert drive_state(0x0233) == "SWITCHED_ON"
    assert drive_state(0x1237) == "OPERATION_ENABLED"
    assert drive_state(0x0218) == "FAULT"
