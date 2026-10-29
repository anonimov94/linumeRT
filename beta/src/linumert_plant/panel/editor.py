"""Edytor wirtualnej obrabiarki i biblioteki napędów w panelu Plant (sesja 023, REQ-VM-12).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 023.

`machine.yaml` pozostaje jedynym źródłem prawdy (REQ-VM-01): edytor czyta i zapisuje ten plik
(mapa YAML), każdy zapis przechodzi pełną walidację REQ-VM-11 (schemat, spójność, napędy z
biblioteki, model rdzenia), a poprzednia i nowa wersja trafiają do historii
`<state>/machines/<nazwa>/historia/NNNN_<czas>.yaml`. Przeładowanie modelu w działającym
Plant (bez restartu VM) wolno tylko przy wyłączonych napędach i tej samej liczbie osi LRT-NET.
Geometria do widoku 3D (`scene()`) powstaje z modelu: zakresy osi, krańcówki, zderzaki,
ograniczenia programowe, strefy zakazane, bryły kolizyjne, gniazda magazynu, pozycje wymiany,
czujnik długości i bieżący koniec narzędzia (układ G53, mm). Moduł nie zależy od FastAPI.
"""

from __future__ import annotations

import copy
import os
import re
import stat
import tempfile
import time
from pathlib import Path
from typing import Any

import yaml

from linumert.machine.schema import MachineConfigError, parse_machine

from ..atc import pocket_positions
from ..drive_library import (
    YAML_LOADER,
    TemplateError,
    clone_instance,
    clone_template,
    load_library,
    resolve_instance,
    save_template,
)
from ..machine_drives import resolve_machine_drives

ENABLED_STATES = {"OPERATION_ENABLED", "QUICK_STOP_ACTIVE", "FAULT_REACTION_ACTIVE"}
PATH_RE = re.compile(r"^[A-Za-z_][\w]*(\.\w+)*$")


def atomic_write_text(path: Path, text: str) -> None:
    """Publish a complete configuration, retaining the old file on write failure."""
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class EditorError(ValueError):
    """Błąd edycji; `errors` = lista komunikatów po polsku ze ścieżkami pól."""

    def __init__(self, errors: list[str] | str):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("; ".join(self.errors))


def set_path(data: dict, path: str, value: Any) -> None:
    """Ustawia pole po ścieżce z kropkami (`axes.0.travel`, `toolchanger.base_position`)."""
    if not PATH_RE.match(path):
        raise EditorError(f"{path}: niepoprawna ścieżka pola")
    node: Any = data
    keys = path.split(".")
    for key in keys[:-1]:
        node = node[int(key)] if isinstance(node, list) else node.setdefault(key, {})
    last = keys[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value


def get_path(data: Any, path: str) -> Any:
    node = data
    for key in path.split("."):
        node = node[int(key)] if isinstance(node, list) else node[key]
    return node


class MachineEditor:
    """Edytor nad działającym `PlantServer` (plik maszyny z `server.cfg.machine`)."""

    def __init__(self, server, state_dir: Path, library_dir: Path | None = None):
        self.server = server
        self.state_dir = Path(state_dir)
        self.library_dir = library_dir

    # ---- plik maszyny ----------------------------------------------------------------
    @property
    def path(self) -> Path:
        if self.server.cfg.machine is None:
            raise EditorError("Plant uruchomiony bez ścieżki machine.yaml — edycja niemożliwa")
        return Path(self.server.cfg.machine)

    @property
    def history_dir(self) -> Path:
        return self.state_dir / "machines" / self.path.stem / "historia"

    def load(self) -> dict:
        try:
            return yaml.load(self.path.read_text(encoding="utf-8"), Loader=YAML_LOADER) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise EditorError(f"{self.path.name}: nie można wczytać ({exc})") from None

    def validate(self, data: dict) -> list[str]:
        """Pełna walidacja REQ-VM-11 + napędy z biblioteki + model rdzenia (bez uruchamiania)."""
        from ..build_machine import build_model

        try:
            cfg = parse_machine(copy.deepcopy(data))
            drives = resolve_machine_drives(cfg, load_library(self.library_dir))
            build_model(cfg, drives, seed=self.server.cfg.seed)
        except MachineConfigError as exc:
            return list(exc.errors)
        except TemplateError as exc:
            return [str(i) for i in exc.issues]
        return []

    def save(self, data: dict, comment: str = "") -> dict:
        errors = self.validate(data)
        if errors:
            raise EditorError(errors)
        hist = self.history_dir
        hist.mkdir(parents=True, exist_ok=True)
        versions = self.history()
        if not versions and self.path.exists():  # pierwsza edycja: zachowaj wersję wyjściową
            self._write_version(hist, 0, self.path.read_text(encoding="utf-8"), "wersja wyjściowa")
        number = (versions[-1]["number"] + 1) if versions else 1
        text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
        header = (f"# linumeRT · machine.yaml zapisany w panelu Plant "
                  f"{time.strftime('%Y-%m-%d %H:%M:%S')}" + (f" — {comment}" if comment else "")
                  + "\n")
        atomic_write_text(self.path, header + text)
        name = self._write_version(hist, number, header + text, comment)
        return {"version": number, "file": name, "path": str(self.path)}

    @staticmethod
    def _write_version(hist: Path, number: int, text: str, comment: str) -> str:
        name = f"{number:04d}_{time.strftime('%Y%m%d_%H%M%S')}.yaml"
        (hist / name).write_text(text, encoding="utf-8", newline="\n")
        if comment:
            (hist / (name[:-5] + ".txt")).write_text(comment + "\n", encoding="utf-8")
        return name

    def history(self) -> list[dict]:
        if not self.history_dir.is_dir():
            return []
        out = []
        for p in sorted(self.history_dir.glob("*.yaml")):
            note = p.with_suffix(".txt")
            out.append({"number": int(p.name[:4]), "file": p.name,
                        "comment": note.read_text(encoding="utf-8").strip() if note.exists()
                        else ""})
        return out

    def version(self, file: str) -> str:
        if not re.fullmatch(r"\d{4}_\d{8}_\d{6}\.yaml", file):
            raise EditorError(f"{file}: niepoprawna nazwa wersji")
        path = self.history_dir / file
        if not path.is_file():
            raise EditorError(f"brak wersji {file}")
        return path.read_text(encoding="utf-8")

    # ---- przeładowanie -----------------------------------------------------------------
    def reload(self) -> dict:
        """Nowy model z pliku w działającym Plant; tylko przy wyłączonych napędach."""
        from ..build_machine import build_model
        from ..core_binding import PlantMachine
        from ..machine_drives import load_machine_drives

        srv = self.server
        with srv._lock:
            on = [d for d in srv.drives if srv.machine.drive_state(d) in ENABLED_STATES]
        if on:
            raise EditorError(f"przeładowanie tylko przy wyłączonych napędach; włączone: "
                              f"{', '.join(on)} (wyłącz maszynę w LinuxCNC)")
        try:
            mcfg, drives = load_machine_drives(self.path, self.library_dir)
            machine = PlantMachine(build_model(mcfg, drives, seed=srv.cfg.seed))
        except MachineConfigError as exc:
            raise EditorError(list(exc.errors)) from None
        srv.reload_machine(machine, {n: i.params for n, i in drives.items()})
        return {"machine": machine.model.name, "drives": srv.drives,
                "time": round(srv.machine.time, 4)}

    # ---- drzewo i geometria ------------------------------------------------------------
    @staticmethod
    def tree(data: dict) -> list[dict]:
        """Węzły drzewa maszyny (kinematyka → osie → magazyn → pozycje → strefy → bryły)."""
        nodes = []
        kin = data.get("kinematics") or {}
        nodes.append({"id": "kinematics", "path": "kinematics", "title": "Kinematyka",
                      "sub": str(kin.get("preset") or "łańcuch własny")})
        for i, ax in enumerate(data.get("axes") or []):
            travel = ax.get("travel") or ["?", "?"]
            hs = ax.get("hardstops") or {}
            stops = "/".join(str((hs.get(k) or {}).get("position", "—")) for k in ("min", "max"))
            nodes.append({"id": f"axis_{ax.get('letter')}", "path": f"axes.{i}",
                          "title": f"Oś {ax.get('letter')}"
                          + (f" ({'+'.join(ax.get('drives', []))})"
                             if len(ax.get("drives", [])) > 1 else ""),
                          "sub": f"{travel[0]}…{travel[1]} · zderzaki {stops} · "
                                 f"{(ax.get('homing') or {}).get('method', '—')}"})
        nodes.append({"id": "drives", "path": "drives", "title": "Napędy",
                      "sub": f"{len(data.get('drives') or [])} instancji"})
        tc = data.get("toolchanger") or {}
        nodes.append({"id": "toolchanger", "path": "toolchanger", "title": "Magazyn",
                      "sub": f"{tc.get('type', 'manual')} · {tc.get('slots', 0)} gniazd"})
        nodes.append({"id": "positions", "path": "positions", "title": "Pozycje",
                      "sub": "wymiana · czujnik narzędzia · safe_z"})
        nodes.append({"id": "zones", "path": "forbidden_zones", "title": "Strefy zakazane",
                      "sub": str(len(data.get("forbidden_zones") or []))})
        nodes.append({"id": "bodies", "path": "collision_bodies", "title": "Bryły kolizyjne",
                      "sub": str(len(data.get("collision_bodies") or []))})
        return nodes

    def scene(self) -> dict:
        """Elementy widoku 3D z modelu działającego Plant (mm, układ G53 / stołu)."""
        srv = self.server
        cfg = srv.machine.model.config
        axes = {a.letter: a for a in cfg.axes}
        out: dict[str, Any] = {"machine": cfg.machine.name, "type": cfg.machine.type,
                               "boxes": [], "points": [], "lines": [], "cylinders": []}

        def rng(letter: str, attr: str, fallback=(0.0, 0.0)) -> tuple[float, float]:
            ax = axes.get(letter)
            return tuple(getattr(ax, attr)) if ax is not None else fallback

        def box(kind: str, name: str, lo, hi, editable: str | None = None) -> None:
            out["boxes"].append({"kind": kind, "name": name, "min": [float(v) for v in lo],
                                 "max": [float(v) for v in hi], "edit": editable})

        z = rng("Z", "travel", (-100.0, 0.0))
        box("travel", "zakres mechaniczny", (rng("X", "travel")[0], rng("Y", "travel")[0], z[0]),
            (rng("X", "travel")[1], rng("Y", "travel")[1], z[1]))
        zs = rng("Z", "soft_limits", z)
        box("soft", "ograniczenia programowe",
            (rng("X", "soft_limits")[0], rng("Y", "soft_limits")[0], zs[0]),
            (rng("X", "soft_limits")[1], rng("Y", "soft_limits")[1], zs[1]))
        for letter, ax in axes.items():
            for side in ("min", "max"):
                sign = "−" if side == "min" else "+"
                sw = getattr(ax.limits, side)
                if sw is not None:
                    out["points"].append({"kind": "limit", "axis": letter,
                                          "name": f"krańcówka {letter}{sign}",
                                          "value": sw.position, "input": sw.input})
                hs = getattr(ax.hardstops, side)
                if hs is not None:
                    out["points"].append({"kind": "hardstop", "axis": letter,
                                          "name": f"zderzak {letter}{sign}",
                                          "value": hs.position})
        for zone in cfg.forbidden_zones:
            box("zone", zone.name, zone.min, zone.max)
        for i, body in enumerate(cfg.collision_bodies):
            if body.shape == "box":
                half = [s / 2 for s in body.size]
                box("body", f"{body.name} ({body.attached_to})",
                    [p - h for p, h in zip(body.position, half, strict=True)],
                    [p + h for p, h in zip(body.position, half, strict=True)],
                    f"collision_bodies.{i}.position")
            else:
                out["cylinders"].append({"kind": "body", "name": f"{body.name} "
                                         f"({body.attached_to})", "center": list(body.position),
                                         "d": body.size[0], "h": body.size[1]})
        tc = cfg.toolchanger
        if tc.type != "manual" and tc.slots:
            for n, p in enumerate(pocket_positions(tc), 1):
                out["cylinders"].append({"kind": "pocket", "name": f"gniazdo {n}",
                                         "center": list(p), "d": 20.0, "h": 10.0,
                                         "edit": "toolchanger.base_position"})
        pos = cfg.positions
        if pos.manual_change is not None:
            out["points"].append({"kind": "change", "name": "wymiana ręczna",
                                  "xyz": list(pos.manual_change),
                                  "edit": "positions.manual_change"})
        if pos.tool_setter is not None:
            out["points"].append({"kind": "toolsetter", "name": "czujnik narzędzia",
                                  "xyz": list(pos.tool_setter.position),
                                  "edit": "positions.tool_setter.position"})
        with srv._lock:
            out["tool"] = [round(v, 3) for v in srv.nose()]
        return out

    # ---- napędy ----------------------------------------------------------------------
    def templates(self) -> list[dict]:
        lib = load_library(self.library_dir)
        return [{"id": t["id"], "name": t["name"], "type": t["type"], "version": t["version"],
                 "based_on": t.get("based_on"), "live": t.get("live", [])}
                for t in lib.values()]

    def template(self, tid: str) -> dict:
        lib = load_library(self.library_dir)
        if tid not in lib:
            raise EditorError(f"brak szablonu {tid}")
        return lib[tid]

    def instances(self) -> list[dict]:
        data = self.load()
        out = []
        cfg = self.server.machine.model.config
        letters = {d: a.letter for a in cfg.axes for d in a.drives}
        for entry in data.get("drives") or []:
            name = entry.get("id", entry.get("name"))
            out.append({"id": name, "template": entry.get("template"),
                        "overrides": entry.get("overrides") or {},
                        "axis": letters.get(name, "S" if name == cfg.spindle.drive else "")})
        return out

    def clone(self, source: str, new_id: str, name: str | None = None) -> dict:
        """REQ-VD-03: kopia szablonu albo instancji z maszyny jako nowy szablon w bibliotece."""
        lib = load_library(self.library_dir)
        if source in lib:
            new = clone_template(lib[source], new_id, name=name)
        else:
            entry = next((e for e in self.load().get("drives") or []
                          if e.get("id", e.get("name")) == source), None)
            if entry is None:
                raise EditorError(f"brak szablonu ani instancji „{source}”")
            entry = {"id": entry.get("id", entry.get("name")), "template": entry["template"],
                     "overrides": entry.get("overrides") or {}}
            new = clone_instance(resolve_instance(entry, lib), new_id, name=name)
        path = save_template(new, self.library_dir)
        return {"id": new["id"], "based_on": new["based_on"], "file": path.name}

    def diff(self, tid: str) -> list[dict]:
        """Różnice szablonu względem `based_on` (ścieżka, wartość bazowa, wartość)."""
        lib = load_library(self.library_dir)
        tpl = self.template(tid)
        base = lib.get(tpl.get("based_on") or "")
        if base is None:
            return []
        out = []
        for section, values in tpl.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    old = (base.get(section) or {}).get(key)
                    if old != value:
                        out.append({"path": f"{section}.{key}", "base": old, "value": value})
            elif (section not in ("id", "version", "based_on", "name")
                  and base.get(section) != values):
                out.append({"path": section, "base": base.get(section), "value": values})
        return out
