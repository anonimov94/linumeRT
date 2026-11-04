# SPDX-License-Identifier: GPL-2.0-or-later
"""Kierowca: watchdog HAL bramy WebHMI na LinuxCNC + Plant, łańcuch HMI bez obejścia.

Model-Author: Claude · 2026-11-04. Uruchamia go ``tests/test_webhmi_watchdog_linuxcnc.py``
w środowisku RIP (``@POSTGUI@`` podmienia test). Brama działa w tym procesie (``--hal`` bez
uvicorn): piny ``linumert.hmi-*``, ``halcmd -f`` pliku postgui WebHMI, sesja przeglądarki
przez WebSocket aplikacji (``{"alive":1}`` jak klient ``connection.js``).
Wynik: linia ``RESULT {json}``. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

import json
import os
import subprocess
import threading
import time

import linuxcnc
from linumert_webhmi import Gateway, create_app
from linumert_webhmi.backend import CommandError, LinuxCNCBackend
from linumert_webhmi.hal_link import open_hal
from linumert_webhmi.schema import Command
from starlette.testclient import TestClient

TOKEN = "webhmi-watchdog-acceptance"

for _ in range(240):  # NML bywa niegotowy; poll() mapuje narzędzia (~/.tool.mmap)
    try:
        if not os.path.exists(os.path.expanduser("~/.tool.mmap")):
            raise SystemError("brak danych narzedzi")
        linuxcnc.stat().poll()
        break
    except (linuxcnc.error, SystemError):
        time.sleep(0.5)

out = {}
pins, component = open_hal(time.monotonic())
post = subprocess.run(["halcmd", "-f", "@POSTGUI@"], capture_output=True, text=True)
out["postgui_rc"] = post.returncode
out["postgui_err"] = post.stderr[-500:]
gateway = Gateway(LinuxCNCBackend(module=linuxcnc), hal_pins=pins)
gateway.start()
# Karta przeglądarki przez prawdziwą aplikację: WebSocket, token i {"alive":1} co 100 ms,
# dopóki "żyje" (milczenie przy otwartym gnieździe = zawieszona karta).
client = TestClient(create_app(gateway, TOKEN), base_url="http://127.0.0.1:8765")
alive = threading.Event()
alive.set()
opened = threading.Event()


def browser():
    with client.websocket_connect("/ws", headers={"host": "127.0.0.1:8765"}) as ws:
        ws.send_json({"auth": TOKEN})
        ws.receive_json()
        opened.set()
        while True:
            if alive.is_set():
                ws.send_text('{"alive":1}')
            time.sleep(0.1)


threading.Thread(target=browser, daemon=True).start()
opened.wait(10)


def halget(name):
    return subprocess.run(["halcmd", "getp", name], capture_output=True,
                          text=True).stdout.strip()


def task():
    return gateway.snapshot()[1].get("task_state")


def wait_task(target, timeout):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if task() == target:
            return round(time.monotonic() - t0, 2)
        time.sleep(0.02)
    return None


def command(**kw):
    try:
        gateway.execute(Command(**kw))  # polecenia REST; życie karty tylko z WebSocket
        return "ok"
    except CommandError as error:
        return str(error)


def acknowledge_and_power():
    r = {"single_reset": command(cmd="reset")}
    time.sleep(1.5)
    r["after_single"] = task()
    r["double_reset"] = command(cmd="reset", double=True)
    r["to_estop_reset_s"] = wait_task("estop_reset", 5)
    r["power_on"] = command(cmd="power_on")
    r["to_on_s"] = wait_task("on", 5)
    time.sleep(0.5)
    r["wd_ok"] = halget("watchdog.ok-out")
    r["hmi_chain"] = halget("lrt_hmi_bypass.out")
    return r


time.sleep(1.0)
out["start"] = {"task": task(), "wd_ok": halget("watchdog.ok-out"),
                "bypass": halget("lrt_hmi_bypass.in1"),
                "hmi_hal": gateway.snapshot()[1]["hmi_hal"]}
out["ack1"] = acknowledge_and_power()

alive.clear()  # karta milczy: brama przestaje przełączać hmi-heartbeat
out["silent_to_estop_s"] = wait_task("estop", 8)
out["silent_wd_ok"] = halget("watchdog.ok-out")
alive.set()
time.sleep(0.5)
# Reset z innego procesu (bez potwierdzenia w zatrzasku HAL) nie zamyka łańcucha HMI.
direct = linuxcnc.command()
direct.state(linuxcnc.STATE_ESTOP_RESET)
direct.wait_complete()
time.sleep(1.5)
out["direct_reset_task"] = task()
out["ack2"] = acknowledge_and_power()

gateway.stop()  # zawieszona brama: brak obiegów, brak zboczy (stan czytamy wprost z NML)
s = linuxcnc.stat()
t0 = time.monotonic()
while time.monotonic() - t0 < 8:
    s.poll()
    if s.task_state == linuxcnc.STATE_ESTOP:
        break
    time.sleep(0.02)
out["frozen_to_estop_s"] = round(time.monotonic() - t0, 2)
out["frozen_task"] = s.task_state
out["frozen_wd_ok"] = halget("watchdog.ok-out")
print("RESULT " + json.dumps(out), flush=True)
