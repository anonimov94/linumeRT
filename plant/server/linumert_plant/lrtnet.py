"""Protokół LRT-NET v1: kodowanie i dekodowanie ramek (docs/PLANT.md §3).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 016.

Little-endian, CRC32 IEEE 802.3 (`zlib.crc32`) od pierwszego bajtu do pola `crc32` wyłącznie.
Dekoder nie rzuca niczego poza `FrameError` — uszkodzona ramka jest odrzucana i liczona
przez serwer, proces działa dalej (REQ-QA-03).
"""

from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass

PORT = 47700
MAGIC = 0x524C
VERSION = 1
TYPE_COMMAND = 1  # master → plant
TYPE_REPLY = 2  # plant → master
MAX_AXES = 8

HEADER = struct.Struct("<HBBIQBBH")  # magic, version, type, seq, time_ns, n_axes, flags, reserved
CMD_AXIS = struct.Struct("<HbBi")  # controlword, mode, pad, target_pos
CMD_TAIL = struct.Struct("<If")  # digital_out, spindle_cmd (+ crc32)
REPLY_AXIS = struct.Struct("<HbBiihH")  # statusword, mode_display, pad, actual_pos,
#                                         following_error, torque_pct, error_code
REPLY_TAIL = struct.Struct("<IfIII")  # digital_in, spindle_actual, lost, late, jitter_us (+ crc32)
CRC = struct.Struct("<I")

# Flagi nagłówka.
FLAG_RESET_STATS = 0x01  # master: zeruj statystyki
FLAG_FAULT = 0x01  # plant: fault napędu
FLAG_ESTOP_OPEN = 0x02  # plant: pętla E-STOP otwarta


class FrameError(ValueError):
    """Ramka odrzucona: zły magic, wersja, typ, długość, liczba osi, CRC albo pole
    (niezerowe `reserved`/`pad`, `spindle_*` NaN lub nieskończone)."""


def command_size(n_axes: int) -> int:
    return HEADER.size + n_axes * CMD_AXIS.size + CMD_TAIL.size + CRC.size


def reply_size(n_axes: int) -> int:
    return HEADER.size + n_axes * REPLY_AXIS.size + REPLY_TAIL.size + CRC.size


@dataclass
class AxisCommand:
    controlword: int = 0
    mode: int = 8
    target_pos: int = 0


@dataclass
class Command:
    seq: int
    time_ns: int
    axes: list[AxisCommand]
    digital_out: int = 0
    spindle_cmd: float = 0.0
    flags: int = 0


@dataclass
class AxisReply:
    statusword: int = 0
    mode_display: int = 0
    actual_pos: int = 0
    following_error: int = 0
    torque_pct: int = 0
    error_code: int = 0


@dataclass
class Reply:
    seq: int
    time_ns: int
    axes: list[AxisReply]
    digital_in: int = 0
    spindle_actual: float = 0.0
    frames_lost: int = 0
    frames_late: int = 0
    jitter_us: int = 0
    flags: int = 0


def _seal(body: bytes) -> bytes:
    return body + CRC.pack(zlib.crc32(body))


def _clamp(value: int, lo: int, hi: int) -> int:
    return lo if value < lo else hi if value > hi else value


def _open(frame: bytes, kind: int, size_of) -> tuple[tuple, int]:
    """Sprawdza nagłówek, długość i CRC; zwraca pola nagłówka i liczbę osi."""
    if len(frame) < HEADER.size + CRC.size:
        raise FrameError(f"ramka za krótka ({len(frame)} B)")
    head = HEADER.unpack_from(frame, 0)
    magic, version, ftype, _seq, _time, n_axes = head[:6]
    if magic != MAGIC:
        raise FrameError(f"zły magic 0x{magic:04X}")
    if version != VERSION:
        raise FrameError(f"nieobsługiwana wersja {version}")
    if ftype != kind:
        raise FrameError(f"zły typ ramki {ftype}")
    if head[7] != 0:
        raise FrameError(f"niezerowe pole reserved 0x{head[7]:04X}")
    if not 1 <= n_axes <= MAX_AXES:
        raise FrameError(f"liczba osi {n_axes} poza 1–{MAX_AXES}")
    if len(frame) != size_of(n_axes):
        raise FrameError(f"długość {len(frame)} B, oczekiwano {size_of(n_axes)} B")
    (crc,) = CRC.unpack_from(frame, len(frame) - CRC.size)
    if crc != zlib.crc32(frame[: -CRC.size]):
        raise FrameError("zła suma CRC32")
    return head, n_axes


def encode_command(cmd: Command) -> bytes:
    n = len(cmd.axes)
    if not 1 <= n <= MAX_AXES:
        raise ValueError(f"liczba osi {n} poza 1–{MAX_AXES}")
    parts = [HEADER.pack(MAGIC, VERSION, TYPE_COMMAND, cmd.seq & 0xFFFFFFFF,
                         cmd.time_ns & 0xFFFFFFFFFFFFFFFF, n, cmd.flags & 0xFF, 0)]
    for a in cmd.axes:
        parts.append(CMD_AXIS.pack(a.controlword & 0xFFFF, a.mode, 0, a.target_pos))
    parts.append(CMD_TAIL.pack(cmd.digital_out & 0xFFFFFFFF, cmd.spindle_cmd))
    return _seal(b"".join(parts))


def decode_command(frame: bytes) -> Command:
    head, n = _open(frame, TYPE_COMMAND, command_size)
    axes = []
    off = HEADER.size
    for _ in range(n):
        cw, mode, pad, target = CMD_AXIS.unpack_from(frame, off)
        if pad != 0:
            raise FrameError(f"niezerowe pole pad osi {len(axes)}")
        axes.append(AxisCommand(cw, mode, target))
        off += CMD_AXIS.size
    dout, spindle = CMD_TAIL.unpack_from(frame, off)
    if not math.isfinite(spindle):
        raise FrameError(f"spindle_cmd nieskończone lub NaN ({spindle})")
    return Command(seq=head[3], time_ns=head[4], axes=axes, digital_out=dout,
                   spindle_cmd=spindle, flags=head[6])


def encode_reply(rep: Reply) -> bytes:
    n = len(rep.axes)
    parts = [HEADER.pack(MAGIC, VERSION, TYPE_REPLY, rep.seq & 0xFFFFFFFF,
                         rep.time_ns & 0xFFFFFFFFFFFFFFFF, n, rep.flags & 0xFF, 0)]
    for a in rep.axes:
        parts.append(REPLY_AXIS.pack(
            a.statusword & 0xFFFF, _clamp(a.mode_display, -128, 127), 0,
            _clamp(a.actual_pos, -(2**31), 2**31 - 1),
            _clamp(a.following_error, -(2**31), 2**31 - 1),
            _clamp(a.torque_pct, -(2**15), 2**15 - 1), a.error_code & 0xFFFF))
    u32 = 0xFFFFFFFF
    parts.append(REPLY_TAIL.pack(rep.digital_in & u32, rep.spindle_actual, rep.frames_lost & u32,
                                 rep.frames_late & u32, _clamp(rep.jitter_us, 0, u32)))
    return _seal(b"".join(parts))


def decode_reply(frame: bytes) -> Reply:
    head, n = _open(frame, TYPE_REPLY, reply_size)
    axes = []
    off = HEADER.size
    for _ in range(n):
        sw, mode, pad, pos, ferr, torque, err = REPLY_AXIS.unpack_from(frame, off)
        if pad != 0:
            raise FrameError(f"niezerowe pole pad osi {len(axes)}")
        axes.append(AxisReply(sw, mode, pos, ferr, torque, err))
        off += REPLY_AXIS.size
    din, spindle, lost, late, jitter = REPLY_TAIL.unpack_from(frame, off)
    if not math.isfinite(spindle):
        raise FrameError(f"spindle_actual nieskończone lub NaN ({spindle})")
    return Reply(seq=head[3], time_ns=head[4], axes=axes, digital_in=din, spindle_actual=spindle,
                 frames_lost=lost, frames_late=late, jitter_us=jitter, flags=head[6])


def seq_delta(new: int, last: int) -> int:
    """Różnica numerów ramek z zawinięciem u32: > 0 nowsza, ≤ 0 starsza lub powtórzona."""
    d = (new - last) & 0xFFFFFFFF
    return d - 0x100000000 if d >= 0x80000000 else d
