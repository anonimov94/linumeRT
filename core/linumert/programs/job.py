"""Deterministic preparation bundle; no machine commands or transport dependencies.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from linumert.generators import basic, drilling, pockets, surfacing
from linumert.generators.base import Issue
from linumert.generators.registry import GeneratorRegistry
from linumert.generators.tooling import check_steps
from linumert.machine.schema import MachineConfig
from linumert.tools.db import Tool
from linumert.tools.tbl import format_tbl

from .compiler import CompileError, compile_program
from .lexer import check
from .lnx import LnxProgram, dump_lnx, parse_lnx

FORMAT = "linumert.job"
VERSION = 1
RESOURCES = {"program.lnx", "program.ngc", "machine.yaml", "drives.json", "tools.json",
             "setup.json", "prepare.json", "tool.tbl"}
CUTTING = {"face_mill", "pocket_rect", "pocket_circle", "drill_holes"}
OFFSETS = ("G54", "G55", "G56", "G57", "G58", "G59")


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def registry() -> GeneratorRegistry:
    result = GeneratorRegistry()
    for module in (basic, drilling, pockets, surfacing):
        module.register(result)
    return result


def _steps(program, reg):
    budget = 0.0
    checked, issues = [], []
    if len(program.steps) > 1000:
        raise ValueError("Zadanie przekracza limit 1000 kroków przygotowania")
    for number, step in enumerate(program.steps, 1):
        if not step.enabled:
            continue
        generator = reg.get(step.generator, step.version)
        if generator is None:
            problem = Issue("P-5011", {"step": number, "name": step.generator,
                                       "version": step.version})
            issues.append(f"{problem.code}: {problem.message()}")
            continue
        values, problems = generator.normalize(step.params, number)
        if not problems:
            problems = generator.check(values, number)
        if problems:
            issues += [f"{p.code}: {p.message()}" for p in problems]
            continue
        if step.generator in CUTTING and "tool_d" in values:
            span = max(abs(values.get("x1", 0) - values.get("x0", 0)),
                       abs(values.get("y1", 0) - values.get("y0", 0)),
                       values.get("width", 0), values.get("height", 0),
                       2 * values.get("radius", 0), 1)
            budget += (1 + values["depth"] / values["step_down"]) * (
                1 + span / (values["tool_d"] * values["stepover"] / 100)) * 32
        if step.generator == "drill_holes":
            budget += (len(values["points"].split(";")) if values["pattern"] == "list"
                       else 1 if values["pattern"] == "single"
                       else values["count"] * (values["rows"] if values["pattern"] == "grid"
                                               else 1))
        if not math.isfinite(budget) or budget > 100_000:
            raise ValueError(f"krok {number}: przekroczony budżet przygotowania ścieżki")
        checked.append((number, step.generator, values))
    return checked, issues


def render(program: LnxProgram, machine: MachineConfig, drives: dict, tools: dict[int, Tool],
           origin: tuple[float, float, float], offset: str = "G54", *,
           source_text: str | None = None) -> dict[str, str]:
    """Validated machine/drives + tool snapshot → immutable package contents.

    The caller resolves drive templates using the machine model's public resolver.
    Origin is the selected work coordinate zero in machine mm, before tool offset.
    This stage deliberately does not claim an interpreted motion-limit check.
    """
    if source_text is not None and parse_lnx(json.loads(source_text)) != program:
        raise ValueError("Snapshot źródła nie odpowiada kompilowanemu programowi")
    if offset not in OFFSETS or len(origin) != 3 or not all(
            not isinstance(v, bool) and math.isfinite(v) for v in origin):
        raise ValueError("Ustawienie detalu: wymagane G54–G59 i trzy skończone współrzędne mm")
    axes = {axis.letter: axis for axis in machine.axes}
    if not set("XYZ") <= axes.keys():
        raise ValueError("Przygotowanie CAM 2D wymaga osi X, Y i Z")
    if set(drives) != {drive.name for drive in machine.drives}:
        raise ValueError("Snapshot napędów nie odpowiada modelowi maszyny")
    enabled = [s for s in program.steps if s.enabled]
    names = [s.generator for s in enabled]
    if (not names or names[0] != "header" or names[-1] != "program_end"
            or names.count("header") != 1 or names.count("program_end") != 1
            or not any(n in CUTTING for n in names)):
        raise ValueError("Zadanie wymaga jednego nagłówka, operacji obróbki i końca programu")
    unsupported = set(names) - CUTTING - {"header", "tool_change", "program_end"}
    if unsupported:
        raise ValueError("Prepare nie obsługuje jeszcze operacji: "
                         + ", ".join(sorted(unsupported)))
    reg = registry()
    current = None
    used = set()
    checked, issues = _steps(program, reg)
    for number, name, values in checked:
        if name == "header":
            expected = "G21" if program.units == "mm" else "G20"
            if values["units"] != expected or values["offset"] != offset:
                issues.append(f"krok {number}: nagłówek {values['units']} / {values['offset']} "
                              f"nie odpowiada jednostkom {program.units} i układowi {offset}")
        elif name == "tool_change":
            current = values["tool"]
            used.add(current)
            rpm = values["rpm"]
            if rpm > machine.spindle.max_rpm or 0 < rpm < machine.spindle.min_rpm:
                issues.append(f"krok {number}: obroty S{rpm:g} poza zakresem wrzeciona maszyny "
                              f"{machine.spindle.min_rpm:g}–{machine.spindle.max_rpm:g}")
        elif name in CUTTING and current is None:
            issues.append(f"krok {number}: obróbka wymaga wcześniejszego wyboru narzędzia")
    selected = [tools[n] for n in sorted(used) if n in tools]
    valid_tools = {}
    for tool in selected:
        validation = tool.validate()
        if validation:
            issues += [f"{issue.code}: {issue.message()}" for issue in validation]
            continue
        valid_tools[tool.number] = tool
        if tool.type in (None, "special_stl") or not (tool.tool_diameter() or 0) > 0:
            issues.append(f"T{tool.number}: wymagany znany profil i dodatnia średnica narzędzia")
        if tool.offsets.get("Z", 0) <= 0:
            issues.append(f"T{tool.number}: wymagany dodatni wymiar Z od nosa do końca narzędzia")
    issues += [f"{issue.code}: {issue.message()}"
               for issue in check_steps(checked, valid_tools.get, program.units)]
    if issues:
        raise ValueError("; ".join(issues))
    try:
        gcode = compile_program(program, reg, source="program.lnx", tools=tools.get,
                                safe_z=axes["Z"].soft_limits[1])
    except CompileError as exc:
        raise ValueError("; ".join(f"{i.code}: {i.message()}" for i in exc.issues)) from None
    syntax = check(gcode)
    if syntax:
        raise ValueError("; ".join(p.message() for p in syntax))
    setup = {"offset": offset, "origin_mm": list(origin), "linear_units": "mm"}
    report = {"status": "prepared", "checks": {
        "machine_model": "passed", "program_and_tools": "passed", "units_and_setup": "passed",
        "interpreter": "pending", "motion_limits": "pending", "material": "pending",
        "execution": "not_started"}, "tool_numbers": sorted(used)}
    files = {"program.lnx": source_text if source_text is not None else dump_lnx(program),
             "program.ngc": gcode,
             "machine.yaml": json_text(machine.model_dump(mode="json")),
             "drives.json": json_text(drives),
             "tools.json": json_text([asdict(t) for t in selected]),
             "tool.tbl": format_tbl([t.to_tbl() for t in selected]),
             "setup.json": json_text(setup), "prepare.json": json_text(report)}
    manifest = {"format": FORMAT, "version": VERSION, "name": program.name,
                "program_units": program.units, "machine_units": "mm",
                "generators": [{"name": s.generator, "version": s.version} for s in enabled],
                "resources": {name: {"sha256": digest(text.encode("utf-8")),
                                      "bytes": len(text.encode("utf-8"))}
                              for name, text in files.items()}}
    manifest["job_id"] = digest(json_text(manifest).encode("utf-8"))
    files["manifest.json"] = json_text(manifest)
    return files


def publish(files: dict[str, str], out: Path | str) -> Path:
    """Publish a complete directory, refusing every existing target including symlinks."""
    out = Path(out)
    if out.exists() or out.is_symlink():
        raise FileExistsError(f"Pakiet już istnieje: {out.name}")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{out.name}.prepare-", dir=out.parent) as temp:
        stage = Path(temp)
        if set(files) != RESOURCES | {"manifest.json"}:
            raise ValueError("Niekompletny zestaw plików pakietu")
        for name, text in files.items():
            (stage / name).write_text(text, encoding="utf-8", newline="\n")
        read(stage)
        if os.name == "nt":
            os.rename(stage, out)  # Windows refuses an existing destination.
        else:
            out.mkdir()  # Exclusive reservation; a second publisher cannot overwrite us.
            try:
                os.replace(stage, out)
            except BaseException:
                with contextlib.suppress(OSError):
                    out.rmdir()  # Never remove files added by another writer.
                raise
    return out


def read(path: Path | str) -> tuple[dict, dict[str, str]]:
    """Check package identity, resource whitelist, regular files and all byte hashes."""
    path = Path(path)
    if (path / "manifest.json").is_symlink():
        raise ValueError("Manifest nie może być dowiązaniem")
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or manifest.get("format") != FORMAT
            or manifest.get("version") != VERSION):
        raise ValueError("Nieobsługiwany format pakietu zadania")
    identity = dict(manifest)
    job_id = identity.pop("job_id", None)
    if job_id != digest(json_text(identity).encode("utf-8")):
        raise ValueError("Niezgodna suma kontrolna manifestu")
    if not isinstance(manifest.get("resources"), dict) or set(manifest["resources"]) != RESOURCES:
        raise ValueError("Nieprawidłowa lista zasobów zadania")
    files = {}
    for name, expected in manifest["resources"].items():
        if not isinstance(expected, dict) or set(expected) != {"sha256", "bytes"}:
            raise ValueError(f"Nieprawidłowy opis zasobu: {name}")
        resource = path / name
        if resource.is_symlink() or not resource.is_file():
            raise ValueError(f"Brak zwykłego pliku zasobu: {name}")
        data = resource.read_bytes()
        if digest(data) != expected["sha256"] or len(data) != expected["bytes"]:
            raise ValueError(f"Zmieniony zasób zadania: {name}")
        files[name] = data.decode("utf-8")
    return manifest, files
