#!/usr/bin/env python3
"""Pomiar łącza LRT-NET między VM-A a VM-B (sesja 025, docs/VM.md §5).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 025.

Wysyła ramki komend co `--cycle-ms` (jak `lrt_net` w wątku servo: wysyłka co cykl, odbiór
nieblokujący, bez czekania na odpowiedź) i mierzy: czas obiegu (RTT), rozrzut własnego okresu
wysyłki (VM-A nie jest systemem RT), brakujące odpowiedzi oraz liczniki Plant (utracone,
spóźnione, jitter odbioru) i zadziałanie watchdoga E-4003 (603Fh = 0x8130). Napędy są włączane
jak w `lrt_cia402` (6040h: 0x06 → 0x07 → 0x0F) z celem CSP równym pozycji aktualnej, czyli osie
stoją; na końcu sonda je wyłącza. Uruchamiaj przy zatrzymanym LinuxCNC (jeden master naraz).

  python tools/vm/lrtnet_probe.py --host 10.77.0.20            # z VM-A, Plant w VM-B
  python tools/vm/lrtnet_probe.py --host 127.0.0.1 --frames 5000 --json wynik.json

Kod wyjścia: 0 = łącze w normie, 1 = watchdog albo straty powyżej progów, 2 = brak odpowiedzi.
Tryb `--realtime` Plant wymaga, by przerwa między ramkami nie przekroczyła `watchdog_ms` (50 ms).
"""

from __future__ import annotations

import argparse
import json
import select
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plant" / "server"))

from linumert_plant.lrtnet import (  # noqa: E402
    PORT,
    AxisCommand,
    Command,
    FrameError,
    decode_reply,
    encode_command,
)

WATCHDOG_CODE = 0x8130  # 603Fh COMM_WATCHDOG (E-4003)


def _pct(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    return s[min(len(s) - 1, int(q * (len(s) - 1) + 0.5))]


def _controlword(sw: int, prev: int, reset: bool = True) -> int:
    """6040h z bieżącego 6041h (jak lrt_cia402): fault reset → shutdown → switch on → enable.
    `reset=False`: fault zostaje (po włączeniu napędów, żeby watchdog był widoczny do końca)."""
    if sw & 0x4F in (0x08, 0x0F):  # FAULT: zbocze bitu 7
        if not reset:
            return 0x06
        return 0x00 if prev == 0x80 else 0x80
    state = sw & 0x6F
    if state == 0x21:  # READY_TO_SWITCH_ON
        return 0x07
    if state in (0x23, 0x27):  # SWITCHED_ON, OPERATION_ENABLED
        return 0x0F
    return 0x06  # NOT_READY (rozruch napędu), SWITCH_ON_DISABLED


def probe(host: str, port: int = PORT, frames: int = 2000, cycle_ms: float = 1.0, axes: int = 4,
          drain_s: float = 0.5, stall_at: int | None = None, stall_ms: float = 0.0) -> dict:
    """Wysyła `frames` ramek i zwraca statystyki. `stall_at`/`stall_ms`: celowa przerwa wysyłki
    (symulacja zawieszenia VM-A) przed ramką `stall_at`."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((host, port))
    sock.setblocking(False)
    cycle_ns = int(cycle_ms * 1e6)
    sent_at: dict[int, int] = {}
    rtt_ms: list[float] = []
    periods_ms: list[float] = []
    rejected = 0
    plant = {"frames_lost": 0, "frames_late": 0, "jitter_us_max": 0}
    watchdog = False
    actual: list[int] | None = None  # pozycje z ostatniej odpowiedzi (cel CSP = trzymanie)
    status: list[int] = [0] * axes
    cws: list[int] = [0x06] * axes
    enabled_at: int | None = None

    def receive(timeout: float) -> None:
        nonlocal rejected, watchdog, actual, status, enabled_at
        while True:
            ready, _, _ = select.select([sock], [], [], timeout)
            if not ready:
                return
            timeout = 0.0
            try:
                data = sock.recv(2048)
            except (BlockingIOError, ConnectionRefusedError):
                return
            now = time.monotonic_ns()
            try:
                rep = decode_reply(data)
            except FrameError:
                rejected += 1
                continue
            t0 = sent_at.pop(rep.seq, None)
            if t0 is not None:
                rtt_ms.append((now - t0) / 1e6)
            plant["frames_lost"] = max(plant["frames_lost"], rep.frames_lost)
            plant["frames_late"] = max(plant["frames_late"], rep.frames_late)
            plant["jitter_us_max"] = max(plant["jitter_us_max"], rep.jitter_us)
            # Fault sprzed włączenia (np. watchdog po poprzednim pomiarze) kasuje sekwencja startu.
            if enabled_at is not None:
                watchdog |= any(a.error_code == WATCHDOG_CODE for a in rep.axes)
            actual = [a.actual_pos for a in rep.axes]
            status = [a.statusword for a in rep.axes]

    start = time.monotonic_ns()
    last = None
    for i in range(frames):
        seq = i + 1
        if stall_at is not None and seq == stall_at:
            time.sleep(stall_ms / 1000.0)
            start = time.monotonic_ns() - i * cycle_ns  # dalej równo, bez nadrabiania
        due = start + i * cycle_ns
        while (wait := due - time.monotonic_ns()) > 0:
            receive(wait / 1e9)
        now = time.monotonic_ns()
        if last is not None:
            periods_ms.append((now - last) / 1e6)
        last = now
        if len(status) == axes:
            if enabled_at is None and all(sw & 0x6F == 0x27 for sw in status):
                enabled_at = i
            cws = [0x06 if i >= frames - 20 else _controlword(sw, cw, enabled_at is None)
                   for sw, cw in zip(status, cws, strict=True)]
        targets = actual if actual is not None and len(actual) == axes else [0] * axes
        cmd = Command(seq=seq, time_ns=i * cycle_ns,
                      axes=[AxisCommand(controlword=cw, mode=8, target_pos=t)
                            for cw, t in zip(cws, targets, strict=True)])
        sent_at[seq] = now
        try:
            sock.send(encode_command(cmd))
        except (BlockingIOError, ConnectionRefusedError):
            pass
        receive(0.0)
    receive(drain_s)
    sock.close()
    return {
        "host": host, "port": port, "frames": frames, "cycle_ms": cycle_ms,
        "replies": len(rtt_ms), "missing": frames - len(rtt_ms), "rejected": rejected,
        "rtt_ms": {"p50": _pct(rtt_ms, 0.5), "p99": _pct(rtt_ms, 0.99),
                   "max": max(rtt_ms, default=float("nan"))},
        "send_period_ms": {"p50": _pct(periods_ms, 0.5), "p99": _pct(periods_ms, 0.99),
                           "max": max(periods_ms, default=float("nan"))},
        "plant": plant, "watchdog": watchdog, "enabled_at_frame": enabled_at,
    }


def verdict(r: dict, max_missing_pct: float = 1.0) -> int:
    if r["replies"] == 0:
        return 2
    if r["watchdog"] or r["missing"] > r["frames"] * max_missing_pct / 100.0:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="10.77.0.20", help="adres Plant (VM-B w lrtnet)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--frames", type=int, default=5000)
    ap.add_argument("--cycle-ms", type=float, default=1.0, help="okres wysyłki (servo-thread)")
    ap.add_argument("--axes", type=int, default=4, help="liczba osi jak [PLANT]AXES w INI")
    ap.add_argument("--max-missing-pct", type=float, default=1.0)
    ap.add_argument("--json", type=Path, default=None, help="zapisz wynik do pliku JSON")
    args = ap.parse_args(argv)
    r = probe(args.host, args.port, args.frames, args.cycle_ms, args.axes)
    code = verdict(r, args.max_missing_pct)
    rtt, per, pl = r["rtt_ms"], r["send_period_ms"], r["plant"]
    print(f"LRT-NET {r['host']}:{r['port']}: ramek {r['frames']}, odpowiedzi {r['replies']}, "
          f"brak {r['missing']}, odrzucone {r['rejected']}")
    print(f"  RTT [ms]: p50 {rtt['p50']:.3f}  p99 {rtt['p99']:.3f}  maks. {rtt['max']:.3f}")
    print(f"  okres wysyłki [ms]: p50 {per['p50']:.3f}  p99 {per['p99']:.3f}  "
          f"maks. {per['max']:.3f}")
    print(f"  Plant: utracone {pl['frames_lost']}, spóźnione {pl['frames_late']}, "
          f"jitter odbioru maks. {pl['jitter_us_max']} µs, watchdog E-4003: "
          f"{'TAK' if r['watchdog'] else 'nie'}")
    at = r["enabled_at_frame"]
    print(f"  napędy: włączone po {at} ramkach" if at is not None
          else "  napędy: NIE włączone (watchdog niewidoczny; wydłuż --frames)")
    print(["wynik: OK", "wynik: ŁĄCZE NIE W NORMIE", "wynik: BRAK ODPOWIEDZI Plant"][code])
    if args.json:
        args.json.write_text(json.dumps(r, indent=2), encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
