"""Aplikacja web panelu Plant: FastAPI + WebSocket (sesja 022).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 022.

Panel działa w osobnym wątku obok pętli ramek LRT-NET i nigdy nie trzyma blokady serwera
dłużej niż krótka kopia stanu. WebSocket `/ws` wysyła nowe próbki telemetrii z częstotliwością
≤ 20 Hz (`PUSH_PERIOD_S`); rejestrator CSV zapisuje plik w wątku roboczym asyncio.
Akcje (parametry live, presety, pulpit, nagrywanie) idą przez REST `/api/...`.
Błąd danych → HTTP 400 z komunikatem po polsku; serwer LRT-NET działa dalej.
"""

from __future__ import annotations

import asyncio
import contextlib
import math
import socket
import threading
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..drive_template import PARAM_BY_PATH, TemplateError
from ..server import PlantServer
from . import presets as preset_store
from .record import NAME_RE as RECORD_NAME_RE
from .record import Recorder
from .telemetry import FIELDS, UNITS

STATIC = Path(__file__).resolve().parent / "static"
PUSH_PERIOD_S = 0.05  # 20 Hz — górna granica odświeżania panelu
RECORD_PERIOD_S = 0.05


class LiveChange(BaseModel):
    drive: str
    path: str
    value: float


class Mpg(BaseModel):
    detents: int


class AxisSel(BaseModel):
    axis: str


class StepSel(BaseModel):
    step: int


class Button(BaseModel):
    button: str


class Key(BaseModel):
    on: bool


class RecordStart(BaseModel):
    name: str | None = None


def _bad(exc: Exception) -> HTTPException:
    if isinstance(exc, TemplateError):
        text = "; ".join(str(i) for i in exc.issues) or str(exc)
    elif isinstance(exc, KeyError):
        text = str(exc.args[0]) if exc.args else "nieznany klucz"
    else:
        text = str(exc)
    return HTTPException(status_code=400, detail=text)


def _display(path: str, unit: str, rotary: bool) -> tuple[str, float]:
    """Jednostka i mnożnik wyświetlania (wartość w API pozostaje w jednostkach szablonu)."""
    if "|" in unit:
        unit = unit.split("|")[1 if rotary else 0].strip()
    if path == "mechanics.backlash":
        return ("°", 180.0 / math.pi) if rotary else ("mm", 1000.0)
    if path in ("motor.rotor_inertia", "mechanics.j_screw"):
        return "kg·cm²", 1e4
    return unit, 1.0


def _slider(path: str, base: float, params: dict[str, Any]) -> tuple[float, float]:
    p = PARAM_BY_PATH[path]
    if path == "electrical.supply_voltage":
        nom = params["electrical"]["nominal_voltage"]
        return 0.1 * nom, 1.5 * nom
    if path == "limits.torque_limit_permille":
        return 0.0, float(min(p.hi, max(1000, 2 * base)))
    lo = float(p.lo or 0.0)
    span = 4 * base if base > 0 else (0.0005 if path == "mechanics.backlash" else 1.0)
    return lo, float(min(p.hi, max(span, lo)))


class Panel:
    """Stan panelu nad jednym `PlantServer` (presety, rejestrator, opis napędów)."""

    def __init__(self, server: PlantServer, state_dir: Path):
        self.server = server
        self.presets_dir = state_dir / "presets"
        self.recorder = Recorder(server.telemetry, state_dir / "records")
        self._record_lock = threading.Lock()

    def drives(self) -> list[dict]:
        srv = self.server
        values = srv.live_values()
        out = []
        for d in srv.drives:
            letter = srv.machine.drive_letter(d)
            rotary = letter in srv.machine.model.rotary
            entry: dict[str, Any] = {"name": d, "axis": letter,
                                     "unit": "°" if rotary else "mm", "live": []}
            base = srv.live_base.get(d)
            for path, value in values.get(d, {}).items():
                p = PARAM_BY_PATH[path]
                section, key = path.split(".", 1)
                start = base[section][key]
                lo, hi = _slider(path, start, base)
                unit, scale = _display(path, p.unit, base["mechanics"]["kind"] == "rotary")
                entry["live"].append({"path": path, "value": value, "base": start,
                                      "min": lo, "max": hi, "unit": unit, "scale": scale,
                                      "int": p.kind == "int", "doc": p.doc})
            out.append(entry)
        return out

    def stats(self) -> dict:
        srv = self.server
        s = srv.stats
        return {"frames": s.received, "rejected": s.rejected, "lost": s.lost, "late": s.late,
                "jitter_us": s.jitter_us, "watchdog": srv.watchdog_tripped,
                "model_failed": srv.model_failed, "time": round(srv.machine.time, 4),
                "messages": list(srv.messages)[-8:]}

    def state(self) -> dict:
        srv = self.server
        return {"machine": srv.machine.model.name, "mode": srv.cfg.mode,
                "cycle_ns": srv.cfg.cycle_ns, "drives": self.drives(), "fields": FIELDS,
                "units": UNITS, "window_s": srv.telemetry.window_s,
                "push_hz": round(1 / PUSH_PERIOD_S),
                "desk": srv.desk.state() if srv.desk is not None else None,
                "stats": self.stats(), "record": self.recorder.status(),
                "presets": preset_store.list_presets(self.presets_dir)}

    def pump_record(self) -> None:
        with self._record_lock:
            self.recorder.pump()


def create_app(server: PlantServer, state_dir: Path | str = Path("state")) -> FastAPI:
    panel = Panel(server, Path(state_dir))

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI):
        async def record_loop() -> None:
            while True:
                await asyncio.sleep(RECORD_PERIOD_S)
                if panel.recorder.active:
                    await asyncio.to_thread(panel.pump_record)

        task = asyncio.create_task(record_loop())
        try:
            yield
        finally:
            task.cancel()
            with panel._record_lock:
                panel.recorder.stop()

    app = FastAPI(title="linumeRT Plant — panel", lifespan=lifespan)
    app.state.panel = panel
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/api/state")
    def state() -> dict:
        return panel.state()

    @app.get("/api/telemetry")
    def telemetry(since: int | None = None) -> dict:
        return server.telemetry.columns(since)

    # ---- parametry live i presety (REQ-VD-04) ------------------------------------------
    @app.post("/api/live")
    def live(change: LiveChange) -> dict:
        try:
            return server.set_live(change.drive, change.path, change.value)
        except (TemplateError, KeyError, ValueError) as exc:
            raise _bad(exc) from None

    @app.get("/api/live/log")
    def live_log() -> list[dict]:
        return server.live_log()

    @app.get("/api/presets")
    def presets() -> list[dict]:
        return preset_store.list_presets(panel.presets_dir)

    @app.post("/api/presets/{name}/load")
    def preset_load(name: str) -> dict:
        try:
            values = preset_store.load_preset(name, server.live_base, panel.presets_dir)
            changes = server.apply_live(values)
        except (preset_store.PresetError, TemplateError, KeyError, ValueError) as exc:
            raise _bad(exc) from None
        return {"name": name, "changes": changes}

    @app.post("/api/presets/{name}/save")
    def preset_save(name: str) -> dict:
        try:
            path = preset_store.save_preset(name, server.live_values(), panel.presets_dir)
        except preset_store.PresetError as exc:
            raise _bad(exc) from None
        return {"name": name, "file": path.name}

    # ---- wirtualny pulpit -------------------------------------------------------------
    def desk():
        if server.desk is None:
            raise HTTPException(400, "pulpit wyłączony: brak sekcji desk w plant.yaml")
        return server.desk

    def desk_call(fn, *args) -> dict:
        try:
            fn(*args)
        except ValueError as exc:
            raise _bad(exc) from None
        return server.desk.state()

    @app.post("/api/desk/mpg")
    def desk_mpg(body: Mpg) -> dict:
        return desk_call(desk().mpg, body.detents)

    @app.post("/api/desk/axis")
    def desk_axis(body: AxisSel) -> dict:
        return desk_call(desk().select_axis, body.axis)

    @app.post("/api/desk/step")
    def desk_step(body: StepSel) -> dict:
        return desk_call(desk().select_step, body.step)

    @app.post("/api/desk/press")
    def desk_press(body: Button) -> dict:
        return desk_call(desk().press, body.button)

    @app.post("/api/desk/key")
    def desk_key(body: Key) -> dict:
        return desk_call(desk().set_key, body.on)

    # ---- nagrywanie CSV ---------------------------------------------------------------
    @app.post("/api/record/start")
    def record_start(body: RecordStart) -> dict:
        with panel._record_lock:
            try:
                panel.recorder.start(body.name)
            except (RuntimeError, ValueError, OSError) as exc:
                raise _bad(exc) from None
            return panel.recorder.status()

    @app.post("/api/record/stop")
    def record_stop() -> dict:
        with panel._record_lock:
            panel.recorder.stop()
            return panel.recorder.status()

    @app.get("/api/records")
    def records() -> list[dict]:
        return panel.recorder.files()

    @app.get("/api/records/{name}")
    def record_file(name: str) -> FileResponse:
        path = panel.recorder.store / name
        if not RECORD_NAME_RE.match(name) or not path.is_file():
            raise HTTPException(404, f"brak nagrania {name}")
        return FileResponse(path, media_type="text/csv", filename=name)

    # ---- WebSocket: telemetria ≤ 20 Hz --------------------------------------------------
    @app.websocket("/ws")
    async def ws(sock: WebSocket) -> None:
        await sock.accept()
        since: int | None = None
        try:
            while True:
                cols = server.telemetry.columns(since)
                since = cols["next"]
                await sock.send_json({"telemetry": cols, "stats": panel.stats(),
                                      "desk": server.desk.state() if server.desk else None,
                                      "record": panel.recorder.status()})
                await asyncio.sleep(PUSH_PERIOD_S)
        except (WebSocketDisconnect, RuntimeError):
            return

    return app


class PanelThread:
    """Serwer uvicorn panelu w wątku tła (obok pętli UDP w wątku głównym)."""

    def __init__(self, server: PlantServer, listen: str, port: int,
                 state_dir: Path | str = Path("state")):
        self.app = create_app(server, state_dir)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((listen, port))
        self.port = self.sock.getsockname()[1]
        self.listen = listen
        config = uvicorn.Config(self.app, log_level="warning", lifespan="on")
        self.uv = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.uv.run, kwargs={"sockets": [self.sock]},
                                       name="plant-panel", daemon=True)

    def start(self, timeout: float = 10.0) -> PanelThread:
        self.thread.start()
        for _ in range(int(timeout / 0.01)):
            if self.uv.started:
                return self
            if not self.thread.is_alive():
                break
            threading.Event().wait(0.01)
        raise RuntimeError("panel Plant nie wystartował (uvicorn)")

    def close(self) -> None:
        self.uv.should_exit = True
        self.thread.join(timeout=5.0)
        self.sock.close()
