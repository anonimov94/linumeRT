# SPDX-License-Identifier: GPL-2.0-or-later
"""Kierowca bramki G2: 7 kroków operatora przez WebSocket WebHMI na LinuxCNC + Plant.

Model-Author: Claude · 2026-11-03. Uruchamia go ``tests/test_g2_webhmi_linuxcnc.py`` w
środowisku RIP. Wszystkie kroki operatora idą tymi samymi poleceniami WebSocket, które wysyła
przeglądarka. Jedyny krok poza bramą to reset zatrzasku E-STOP (``STATE_ESTOP_RESET`` →
``iocontrol.0.user-request-enable`` → ``estop_latch.reset`` w HAL): brama nie ma takiego
polecenia (D35/D37). Wynik: linia ``RESULT {json}``. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

import json
import os
import time

import linuxcnc
from linumert_webhmi import Gateway, create_app
from linumert_webhmi.backend import LinuxCNCBackend
from starlette.testclient import TestClient

TOKEN = "g2-webhmi-acceptance-token"
PROGRAM = "linumert_g2_odbior.ngc"
# Zero detalu w układzie maszyny [mm], z dala od celu sondy z machine.yaml (X 250–350,
# Y 350–450, góra Z −90 przy końcówce 60 mm): inaczej Plant zgłasza styk sondy w ruchu.
ZERO = {"X": 150.0, "Y": 600.0, "Z": -30.0}
TOL = 0.001  # kontrakt precyzji (CLAUDE.md §4)

for _ in range(240):  # NML bywa niegotowy; poll() mapuje narzędzia (~/.tool.mmap)
    try:
        if not os.path.exists(os.path.expanduser("~/.tool.mmap")):
            raise SystemError("brak danych narzedzi")
        s = linuxcnc.stat()
        s.poll()
        break
    except (linuxcnc.error, SystemError):
        time.sleep(0.5)
c = linuxcnc.command()
out = {"steps": {}}
gateway = Gateway(LinuxCNCBackend(module=linuxcnc))
seq = 0


def state():
    return gateway.snapshot()[1]


def wait(cond, timeout, what):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond(state()):
            return state()
        time.sleep(0.02)
    raise AssertionError(f"{what}: brak w {timeout} s; stan {json.dumps(state())[:1500]}")


def axis(st, name):
    return next(a for a in st["axes"] if a["name"] == name)


def settled(st):
    s.poll()
    return st["interp_state"] == "idle" and abs(s.current_vel) < 1e-4 and bool(s.inpos)


def send(ws, expected="ack", **payload):
    global seq
    seq += 1
    ws.send_json({"id": seq, **payload})
    while True:
        reply = ws.receive_json()
        if reply.get("id") == seq:
            assert reply["type"] == expected, (payload, reply)
            return reply


def step(name, **data):
    out["steps"][name] = data
    print("KROK", name, json.dumps(data), flush=True)


gateway.start()
try:
    with TestClient(create_app(gateway, TOKEN), base_url="http://127.0.0.1:8765") as client:
        with client.websocket_connect("/ws", headers={"host": "127.0.0.1:8765"}) as ws:
            ws.send_json({"auth": TOKEN})
            assert ws.receive_json()["type"] == "state"

            # 1. Włączenie: w E-STOP brama odmawia, po resecie zatrzasku w HAL power_on działa.
            st = wait(lambda st: st.get("task_state") == "estop", 20, "start w E-STOP")
            refused = send(ws, "error", cmd="power_on")["message"]
            c.state(linuxcnc.STATE_ESTOP_RESET)  # reset w HAL, poza bramą
            c.wait_complete()
            wait(lambda st: st["task_state"] == "estop_reset", 10, "reset zatrzasku HAL")
            send(ws, cmd="power_on")
            st = wait(lambda st: st["task_state"] == "on", 10, "power_on")
            start_alarms = [a["code"] for a in st["alarms"]]
            send(ws, cmd="reset")  # E-STOP ze startu: przyczyna ustała
            st = wait(lambda st: not st["alarms"], 5, "Reset alarmu startowego")
            step("1_wlaczenie", refused_in_estop=refused, task_state=st["task_state"],
                 start_alarms=start_alarms)

            # 2. Bazowanie wszystkich osi (Plant: krańcówki i indeks z machine.yaml).
            send(ws, cmd="home")
            st = wait(lambda st: st["all_homed"] and settled(st), 240, "bazowanie")
            step("2_bazowanie", all_homed=True,
                 position={a["name"]: a["position"] for a in st["axes"]})

            # Ustawienie nad przygotówką MDI z ekranu (operator, nie kierowca).
            send(ws, cmd="mode", mode="mdi")
            send(ws, cmd="mdi", text=f"G21 G90 G53 G0 Z{ZERO['Z']:.4f}")
            wait(lambda st: settled(st) and abs(axis(st, "Z")["position"] - ZERO["Z"]) < 0.01,
                 60, "MDI Z")
            send(ws, cmd="mdi", text=f"G53 G0 X{ZERO['X']:.4f} Y{ZERO['Y'] - 1.0:.4f}")
            wait(lambda st: settled(st) and abs(axis(st, "X")["position"] - ZERO["X"]) < 0.01,
                 60, "MDI XY")
            send(ws, cmd="mode", mode="manual")
            wait(lambda st: st["mode"] == "manual", 5, "MANUAL")

            # 3. JOG: przyrost +1 mm Y, potem ciągły z deadmanem (bez odświeżania staje).
            s.poll()
            y0 = s.position[1]  # pozycja zadana; rzeczywista ma uchyb nadążania Plant
            send(ws, cmd="jog_increment", axis="Y", speed=5, distance=1)
            for _ in range(30):  # przytrzymany przycisk: odświeżanie co 100 ms do dojazdu
                s.poll()
                if abs(s.position[1] - y0 - 1.0) < 1e-6:
                    break
                send(ws, cmd="jog_keepalive", axis="Y")
                time.sleep(0.1)
            send(ws, cmd="jog_stop", axis="Y")  # zwolnienie przycisku
            st = wait(settled, 20, "koniec przyrostu")
            s.poll()
            increment = s.position[1] - y0
            assert abs(increment - 1.0) < TOL, increment
            assert abs(axis(st, "Y")["position"] - ZERO["Y"]) < 0.02, axis(st, "Y")
            x0 = axis(st, "X")["position"]
            send(ws, cmd="jog", axis="X", speed=5)  # jedna wiadomość, bez odświeżania
            wait(lambda st: not st["jog_active"], 3, "deadman jogu")
            st = wait(settled, 10, "zatrzymanie po deadmanie")
            deadman = axis(st, "X")["position"] - x0
            # ≤ 0,4 s dzierżawy + hamowanie
            assert 0.05 < deadman < 5 * 0.4 + 0.5, (deadman, st["alarms"])
            send(ws, cmd="mode", mode="mdi")
            send(ws, cmd="mdi", text=f"G53 G0 X{ZERO['X']:.4f}")
            wait(lambda st: settled(st) and abs(axis(st, "X")["position"] - ZERO["X"]) < 0.01,
                 30, "powrót X")
            send(ws, cmd="mode", mode="manual")
            wait(lambda st: st["mode"] == "manual", 5, "MANUAL")
            step("3_jog", increment_mm=increment, deadman_mm=deadman)

            # 4. Zero detalu: bieżąca pozycja = 0 w aktywnym układzie (G10 L20 P0).
            send(ws, cmd="work_zero")
            st = wait(lambda st: st["mode"] == "manual" and all(
                abs(axis(st, n)["work_position"]) < TOL for n in "XYZ"), 10, "zero detalu")
            s.poll()
            offset = list(s.g5x_offset[:3])
            for i, n in enumerate("XYZ"):
                assert abs(offset[i] - axis(st, n)["position"]) < 0.02, (offset, st["axes"])
            step("4_zero_detalu", work_offset=st["work_offset"], g5x_offset=offset)

            # 5. Wczytanie programu z katalogu PROGRAM_PREFIX.
            st = wait(lambda st: PROGRAM in st.get("programs", []), 5, "lista programów")
            send(ws, cmd="open", name="../linumert_g2_odbior.ngc", expected="error")
            send(ws, cmd="open", name=PROGRAM)
            st = wait(lambda st: (st["program"] or "").endswith(PROGRAM), 10, "program")
            assert st["mode"] == "auto", st["mode"]
            step("5_program", program=st["program"], listed=len(st["programs"]))

            # 6. AUTO: przebieg programu, kwadrat 20 x 20 mm od zera detalu.
            send(ws, cmd="run")
            wait(lambda st: st["interp_state"] != "idle", 10, "start programu")
            seen = {"x": 0.0, "y": 0.0, "z": 10.0}
            end = time.monotonic() + 120
            while state()["interp_state"] != "idle" and time.monotonic() < end:
                st = state()
                seen["x"] = max(seen["x"], axis(st, "X")["work_position"])
                seen["y"] = max(seen["y"], axis(st, "Y")["work_position"])
                seen["z"] = min(seen["z"], axis(st, "Z")["work_position"])
                time.sleep(0.02)
            st = wait(settled, 30, "koniec programu")
            assert abs(seen["x"] - 20) < 0.05 and abs(seen["y"] - 20) < 0.05, (
                seen, st["alarms"], st["line"], st["mode"])
            assert abs(seen["z"] + 1) < 0.05, seen
            s.poll()
            end_z = s.position[2] - s.g5x_offset[2]  # zadana; rzeczywista ma uchyb Plant
            assert abs(end_z - 5) < TOL, (end_z, st["axes"])
            assert not st["alarms"], st["alarms"]
            step("6_auto", max_work=seen, end_z_cmd=end_z,
                 end_z_ferr=axis(st, "Z")["following_error"])

            # 7. Alarm i Reset: błąd LinuxCNC (limit programowy), potem E-STOP.
            send(ws, cmd="mode", mode="mdi")
            send(ws, cmd="mdi", text="G53 G0 X9999")
            st = wait(lambda st: any(a["code"] == "E-1000" for a in st["alarms"]), 10,
                      "alarm limitu")
            limit_alarm = st["alarms"][0]["text"]
            assert st["task_state"] == "on", st["task_state"]
            send(ws, cmd="reset")
            st = wait(lambda st: not st["alarms"], 5, "Reset kasuje alarm")
            send(ws, cmd="estop")
            st = wait(lambda st: any(a["code"] == "E-1100" for a in st["alarms"]), 10,
                      "alarm E-STOP")
            send(ws, cmd="reset")
            time.sleep(0.3)
            st = state()
            assert [a["code"] for a in st["alarms"]] == ["E-1100"], st["alarms"]
            assert st["task_state"] == "estop", "Reset nie może zwolnić E-STOP"
            c.state(linuxcnc.STATE_ESTOP_RESET)  # reset w HAL, poza bramą
            c.wait_complete()
            wait(lambda st: st["task_state"] == "estop_reset", 10, "reset HAL po E-STOP")
            send(ws, cmd="power_on")
            wait(lambda st: st["task_state"] == "on", 10, "power_on po E-STOP")
            send(ws, cmd="reset")
            st = wait(lambda st: not st["alarms"], 5, "Reset po ustaniu przyczyny")
            step("7_alarm_reset", limit_alarm=limit_alarm, estop_kept_until_hal_reset=True,
                 task_state=st["task_state"])
finally:
    gateway.stop()
    c.abort()
print("RESULT " + json.dumps(out), flush=True)
