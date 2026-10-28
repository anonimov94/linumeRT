"""Model maszyny dla symulacji: bryły kolizyjne i granice napędów z machine.yaml.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-19 (symulacja HMI).

Z machine.yaml (jedno źródło prawdy, CLAUDE.md §5a) bierzemy `collision_bodies` (konwencja jak
w Plant, `linumert_plant/collisions.py`: `head`/`spindle` jadą z nosem wrzeciona, reszta stoi
w G53), zakresy osi oraz napędy: siła graniczna osi = moment szczytowy (ograniczony 6072h) /
przełożenie [m/rad], suma napędów osi (portal); wrzeciono = krzywa moment–prędkość szablonu.
Szablony napędów: `plant/library/drives/<template>.yaml` (bez walidacji, tylko potrzebne pola).
Wszystkie wartości graniczne są przykładowe — NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DRIVES_DIR = Path(__file__).resolve().parents[2] / "library" / "drives"
MOVING = ("head", "spindle")
FIXTURE = ("vise", "fixture")
DEFAULT_AXIS_FORCE = 1000.0   # [N] gdy brak napędu w modelu
DEFAULT_SPINDLE_W = 2200.0


@dataclass(frozen=True)
class Body:
    name: str
    shape: str                          # box | cylinder (oś Z)
    attached: str
    size: tuple[float, ...]
    position: tuple[float, float, float]

    @property
    def moving(self) -> bool:
        return self.attached in MOVING

    def z_range(self, nose_z: float = 0.0) -> tuple[float, float]:
        h = self.size[2] if self.shape == "box" else self.size[1]
        c = self.position[2] + (nose_z if self.moving else 0.0)
        return c - h / 2, c + h / 2

    def center(self, nose=(0.0, 0.0, 0.0)) -> tuple[float, float, float]:
        if not self.moving:
            return self.position
        return tuple(n + o for n, o in zip(nose, self.position, strict=True))


@dataclass
class Machine:
    name: str = "bez modelu"
    path: str = ""
    bodies: list[Body] = field(default_factory=list)
    travel: dict[str, tuple[float, float]] = field(default_factory=dict)
    axis_force: dict[str, float] = field(default_factory=dict)   # [N]
    spindle_curve: list[tuple[float, float]] = field(default_factory=list)  # [rad/s, N·m]
    spindle_power: float = DEFAULT_SPINDLE_W                     # [W]
    spindle_max_rpm: float | None = None

    def spindle_torque_limit(self, rpm: float) -> float:
        """Moment graniczny wrzeciona [N·m] przy obrotach `rpm` (krzywa albo P/ω)."""
        omega = abs(rpm) * 2 * math.pi / 60
        if self.spindle_curve:
            pts = self.spindle_curve
            if omega <= pts[0][0]:
                return pts[0][1]
            for (w0, t0), (w1, t1) in zip(pts, pts[1:], strict=False):
                if omega <= w1:
                    return t0 + (t1 - t0) * (omega - w0) / max(w1 - w0, 1e-9)
            return 0.0
        return self.spindle_power / max(omega, 1.0)

    def force_limit(self, axis: str) -> float:
        return self.axis_force.get(axis, DEFAULT_AXIS_FORCE)


def _template(name: str) -> dict:
    path = DRIVES_DIR / f"{name}.yaml"
    try:
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out.get(k, {}), v) if isinstance(v, dict) else v
    return out


def _drive(spec: dict) -> dict:
    return _merge(_template(spec.get("template", "")), spec.get("overrides") or {})


def _axis_force(drive: dict) -> float | None:
    motor, mech = drive.get("motor") or {}, drive.get("mechanics") or {}
    ratio = mech.get("ratio")
    if not ratio or mech.get("kind", "linear") != "linear":
        return None
    peak = float(motor.get("peak_torque") or motor.get("rated_torque") or 0)
    limit = (drive.get("limits") or {}).get("torque_limit_permille")
    if limit:
        peak = min(peak, float(motor.get("rated_torque", peak)) * float(limit) / 1000)
    return peak / float(ratio) if peak > 0 else None


def load_machine(path: str | Path) -> Machine:
    """machine.yaml → Machine (ValueError z opisem po polsku)."""
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except OSError as exc:
        raise ValueError(f"nie można odczytać {path}: {exc.strerror}") from None
    except yaml.YAMLError as exc:
        raise ValueError(f"niepoprawny YAML {path}: {exc}") from None
    m = Machine(name=(data.get("machine") or {}).get("name", path.stem), path=str(path))
    for b in data.get("collision_bodies") or []:
        try:
            m.bodies.append(Body(str(b["name"]), str(b.get("shape", "box")),
                                 str(b.get("attached_to", "table")),
                                 tuple(float(v) for v in b["size"]),
                                 tuple(float(v) for v in b.get("position", (0, 0, 0)))))
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"bryła kolizyjna bez nazwy/rozmiaru: {b}") from None
    drives = {d.get("id"): d for d in data.get("drives") or []}
    for ax in data.get("axes") or []:
        letter = str(ax.get("letter", "")).upper()
        if "travel" in ax:
            m.travel[letter] = tuple(float(v) for v in ax["travel"])
        forces = [_axis_force(_drive(drives[d])) for d in ax.get("drives", []) if d in drives]
        forces = [f for f in forces if f]
        if forces:
            m.axis_force[letter] = sum(forces)
    spindle = data.get("spindle") or {}
    if spindle.get("max_rpm"):
        m.spindle_max_rpm = float(spindle["max_rpm"])
    sd = drives.get(spindle.get("drive"))
    if sd:
        drv = _drive(sd)
        curve = (drv.get("motor") or {}).get("torque_curve") or []
        m.spindle_curve = [(float(w), float(t)) for w, t in curve]
    return m


# ---- kolizje brył (walce narzędzia o osi Z wobec brył maszyny) --------------------------------

def _cyl_hits(cx, cy, r, z0, z1, body: Body, nose) -> bool:
    b0, b1 = body.z_range(nose[2])
    if min(z1, b1) - max(z0, b0) <= 0:
        return False
    bx, by, _ = body.center(nose)
    if body.shape == "cylinder":
        return math.hypot(cx - bx, cy - by) < r + body.size[0] / 2
    hx, hy = body.size[0] / 2, body.size[1] / 2
    nx = min(max(cx, bx - hx), bx + hx)
    ny = min(max(cy, by - hy), by + hy)
    return math.hypot(cx - nx, cy - ny) < r


def collisions(machine: Machine, nose, cylinders) -> list[tuple[str, str]]:
    """Pary (element ruchomy, element maszyny) w kolizji.

    `cylinders` = [(nazwa, promień, z od, z do)] w układzie maszyny (narzędzie pod nosem);
    bryły `head`/`spindle` z modelu dochodzą same. Sprawdzane wobec brył stojących.
    """
    moving = list(cylinders)
    for b in machine.bodies:
        if b.moving and b.shape == "cylinder":
            z0, z1 = b.z_range(nose[2])
            c = b.center(nose)
            moving.append((b.name, b.size[0] / 2, z0, z1, c[0], c[1]))
    out = []
    for item in moving:
        name, r, z0, z1 = item[:4]
        cx, cy = (item[4], item[5]) if len(item) > 4 else (nose[0], nose[1])
        for b in machine.bodies:
            if b.moving:
                continue
            if _cyl_hits(cx, cy, r, z0, z1, b, nose):
                out.append((name, b.name))
    return out
