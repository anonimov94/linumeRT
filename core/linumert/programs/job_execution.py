"""Bind a verified job to a reproducible LinuxCNC sim/Plant configuration.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex

Export only. Does not start processes, connect CNC, reset safety or enable motion.
The immutable package is copied to a private working directory before execution;
LinuxCNC's mutable parameter/log files must never replace the original evidence.
"""

from __future__ import annotations

import contextlib
import copy
import json
import os
import tempfile
from pathlib import Path, PurePosixPath

from linumert.machine.configgen import joint_drives
from linumert.machine.drives.drive_real import counts_per_unit
from linumert.machine.drives.drive_template import validate_template
from linumert.machine.drives.machine_drives import resolve_machine_drives
from linumert.machine.lite_config import render_lite
from linumert.machine.schema import MachineConfig

from . import job
from .job_check import _snapshot
from .job_verification import validate as validate_verification

FORMAT = "linumert.job.execution"
MAX_BYTES = 64 * 1024 * 1024


def _relative(name):
    p = PurePosixPath(name)
    if (not isinstance(name, str) or "\\" in name or p.is_absolute()
            or not p.parts or any(v in (".", "..") for v in name.split("/"))
            or ":" in name or any(ord(c) < 32 for c in name)):
        raise ValueError("Nieprawidłowa ścieżka zasobu konfiguracji")
    return p


def frozen_inputs(config: MachineConfig, rows: dict, target: str):
    """Derived machine + per-instance templates; never consult today's library."""
    if target not in ("sim", "plant"):
        raise ValueError("Konfiguracja zadania obsługuje wyłącznie sim i plant")
    raw = config.model_dump(mode="json")
    raw.update(target=target, hardware=None)
    if set(rows) != {d.name for d in config.drives}:
        raise ValueError("Lista zamrożonych napędów nie odpowiada maszynie")
    library, mapping = {}, {}
    for index, entry in enumerate(raw["drives"]):
        name = entry["name"]
        row = rows[name]
        if set(row) != {"template", "parameters"} or row["template"] != entry["template"]:
            raise ValueError(f"Nieprawidłowy snapshot napędu {name}")
        parameters = validate_template(copy.deepcopy(row["parameters"]))
        if parameters != row["parameters"]:
            raise ValueError(f"Snapshot napędu {name} wymaga nowych wartości domyślnych")
        if parameters["id"] != row["template"]:
            raise ValueError(f"Id szablonu nie odpowiada snapshotowi napędu {name}")
        checksum = job.digest(job.json_text(parameters).encode())
        identifier = f"job_{index}_{checksum[:12]}"
        parameters["id"] = identifier
        library[identifier] = validate_template(parameters)
        entry.update(template=identifier, overrides={})
        mapping[name] = {"source_template": row["template"], "template": identifier,
                         "source_parameters_sha256": checksum}
    derived = MachineConfig.model_validate(raw)
    instances = resolve_machine_drives(derived, library)
    return derived, library, instances, mapping


def _parameters(setup):
    index = job.OFFSETS.index(setup["offset"]) + 1
    # Fresh private work offsets and G92; the program selects its frozen frame.
    values = {5210: 0, **dict.fromkeys(range(5211, 5220), 0), 5220: index}
    for offset in range(9):
        values.update(dict.fromkeys(range(5221 + offset * 20, 5231 + offset * 20), 0))
    values.update({5221 + (index - 1) * 20 + i: v
                   for i, v in enumerate(setup["origin_mm"])})
    return "".join(f"{key} {value:.17g}\n" for key, value in sorted(values.items()))


def render(path, verification: dict, target: str, *, test_mode=False, port=47700,
           expected_job_id=None):
    """Complete derived inputs, bound by hashes to the original job and verdict."""
    if type(test_mode) is not bool or type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Nieprawidłowy tryb testowy lub port Plant")
    manifest, source, config, setup = _snapshot(Path(path), expected_job_id)
    validate_verification(verification, manifest["job_id"], setup)
    derived, library, instances, mapping = frozen_inputs(config,
        json.loads(source["drives.json"]), target)
    scales = {name: counts_per_unit(instances[name].params) for _, name in joint_drives(derived)}
    files = render_lite(derived, target, test_mode=test_mode, scales=scales)
    ini = f"{derived.machine.name}.ini"
    _relative(ini)
    if target == "plant":
        files[ini] = files[ini].replace("PORT = 47700\n", f"PORT = {port}\n")
    files["tool.tbl"] = source["tool.tbl"]
    files["linumert.var"] = _parameters(setup)
    files.pop("nc_files/.keep", None)
    files["nc_files/program.ngc"] = source["program.ngc"]
    files["machine.yaml"] = job.json_text(derived.model_dump(mode="json"))
    files.update({f"drive_library/{key}.yaml": job.json_text(value)
                  for key, value in library.items()})
    files.update({f"job/{name}": text for name, text in source.items()})
    files["job/manifest.json"] = job.json_text(manifest)
    files["verification.json"] = job.json_text(verification)
    for name in files:
        _relative(name)
    if sum(len(text.encode()) for text in files.values()) > MAX_BYTES:
        raise ValueError("Konfiguracja zadania przekracza limit rozmiaru")
    identity = {"format": FORMAT, "version": 1, "job_id": manifest["job_id"],
        "verification_id": verification["report_id"], "target": target, "test_mode": test_mode,
        "status": "configured", "execution_authorization": False,
        "ini": ini, "program": "nc_files/program.ngc", "drive_mapping": mapping,
        "joint_scales": scales, "assumptions": verification["assumptions"],
        "launch": {"linuxcnc": ["linuxcnc", ini], "plant": ["linumert-plant", "serve",
            "machine.yaml", "--dir", "drive_library", "--lockstep", "--listen", "127.0.0.1",
            "--port", str(port)] if target == "plant" else None},
        "resources": {name: {"sha256": job.digest(text.encode()), "bytes": len(text.encode())}
                      for name, text in sorted(files.items())}}
    identity["execution_id"] = job.digest(job.json_text(identity).encode())
    files["execution.json"] = job.json_text(identity)
    current, _ = job.read(path)
    if current["job_id"] != manifest["job_id"]:
        raise ValueError("Pakiet zmienił się podczas eksportu konfiguracji")
    return files


def read(path):
    """Check bytes AND regeneration, including HAL, tools and frozen templates."""
    path = Path(path)
    if (path / "execution.json").is_symlink():
        raise ValueError("Manifest konfiguracji nie może być dowiązaniem")
    manifest = json.loads((path / "execution.json").read_text(encoding="utf-8"))
    identity = dict(manifest)
    execution_id = identity.pop("execution_id", None)
    if (manifest.get("format") != FORMAT or manifest.get("version") != 1
            or execution_id != job.digest(job.json_text(identity).encode())):
        raise ValueError("Nieprawidłowy manifest konfiguracji zadania")
    resources = manifest.get("resources", {})
    files = {}
    for name, description in resources.items():
        relative = _relative(name)
        if any((path / Path(*relative.parts[:i])).is_symlink()
               for i in range(1, len(relative.parts) + 1)):
            raise ValueError("Zasób konfiguracji nie może być dowiązaniem")
        data = (path / name).read_bytes()
        if description != {"sha256": job.digest(data), "bytes": len(data)}:
            raise ValueError(f"Zmieniony zasób konfiguracji: {name}")
        files[name] = data.decode()
    verification = json.loads(files["verification.json"])
    launch = manifest["launch"]["plant"]
    port = int(launch[-1]) if launch else 47700
    expected = render(path / "job", verification, manifest["target"],
        test_mode=manifest["test_mode"], port=port, expected_job_id=manifest["job_id"])
    actual = {**files, "execution.json": job.json_text(manifest)}
    if expected != actual:
        raise ValueError("Konfiguracja nie odpowiada zweryfikowanemu zadaniu")
    return manifest, files


def publish(files, out):
    """Exclusive atomic tree publication; no overwriting operator files."""
    out = Path(out)
    if out.exists() or out.is_symlink():
        raise FileExistsError("Katalog konfiguracji już istnieje")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{out.name}.execution-", dir=out.parent) as temporary:
        stage = Path(temporary)
        for name, text in files.items():
            _relative(name)
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
        read(stage)
        if os.name == "nt":
            os.rename(stage, out)
        else:
            out.mkdir()
            try:
                os.replace(stage, out)
            except BaseException:
                with contextlib.suppress(OSError):
                    out.rmdir()
                raise
    return out
