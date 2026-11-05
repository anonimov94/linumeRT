"""Filesystem adapter shared by job CLI and WebHMI; no CNC commands.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sqlite3
import sys
import threading
import zipfile
from pathlib import Path

from linumert.machine.schema import MachineConfigError
from linumert.tools.db import ToolDB

from . import job
from .lnx import parse_lnx

MAX_SOURCE_BYTES = 1024 * 1024
JOB_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


def source_name(name: str) -> bool:
    return (isinstance(name, str) and 4 < len(name) <= 128 and name.endswith(".lnx")
            and not name.startswith(".") and not any(c in name for c in "/\\\x00")
            and all(c.isprintable() for c in name))


class JobService:
    """Only configured input/output roots; each preparation re-reads a RO tool snapshot."""

    def __init__(self, programs_dir: Path, machine: Path, tools_db: Path, jobs_dir: Path,
                 library_dir: Path | None = None):
        self.programs_dir = Path(programs_dir).resolve(strict=True)
        if not self.programs_dir.is_dir():
            raise ValueError("Źródła zadań muszą być katalogiem")
        self.machine = Path(machine).resolve(strict=True)
        self.tools_db = Path(tools_db).resolve(strict=True)
        self.jobs_dir = Path(jobs_dir).resolve()
        self.library_dir = library_dir
        self._preparing = threading.Lock()
        self._checking = threading.Lock()

    def _machine(self):
        from linumert.machine.drives.machine_drives import load_machine_drives

        return load_machine_drives(self.machine, self.library_dir)

    def context(self) -> dict:
        machine, _ = self._machine()
        programs = sorted(p.name for p in self.programs_dir.iterdir()
                          if source_name(p.name) and not p.is_symlink() and p.is_file()
                          and p.stat().st_size <= MAX_SOURCE_BYTES)
        return {"available": True, "machine": machine.machine.name, "tools": self.tools_db.name,
                "programs": programs, "offsets": list(job.OFFSETS)}

    def _target(self, name: str) -> Path:
        if not JOB_NAME.fullmatch(name):
            raise ValueError("Nazwa pakietu: 1–64 liter ASCII, cyfr, _ lub -; "
                             "pierwsza litera/cyfra")
        path = self.jobs_dir / name
        if path.is_symlink():
            raise ValueError("Pakiet nie może być dowiązaniem")
        return path

    def prepare(self, program: str, name: str, origin: tuple[float, float, float],
                offset: str = "G54") -> dict:
        if not self._preparing.acquire(blocking=False):
            raise ValueError("Trwa przygotowanie innego zadania; spróbuj ponownie")
        try:
            target = self._target(name)
            if target.exists():
                raise FileExistsError(f"Pakiet już istnieje: {name}")
            if not source_name(program):
                raise ValueError("Wybierz plik .lnx z katalogu źródeł")
            source = self.programs_dir / program
            if source.is_symlink() or not source.is_file():
                raise ValueError("Brak zwykłego pliku źródłowego .lnx")
            with source.open("rb") as handle:
                data = handle.read(MAX_SOURCE_BYTES + 1)
            if len(data) > MAX_SOURCE_BYTES:
                raise ValueError("Źródło .lnx przekracza 1 MiB")
            text = data.decode("utf-8")
            parsed = parse_lnx(json.loads(text))
            machine, instances = self._machine()
            drives = {name: {"template": inst.template_id, "parameters": inst.params}
                      for name, inst in instances.items()}
            with ToolDB(self.tools_db, readonly=True) as database:
                database.db.execute("BEGIN")
                tools = {tool.number: tool for tool in database.tools()}
            files = job.render(parsed, machine, drives, tools, origin, offset, source_text=text)
            job.publish(files, target)
            return self.describe(name)
        finally:
            self._preparing.release()

    def describe(self, name: str) -> dict:
        manifest, files = job.read(self._target(name))
        return {"name": name, "manifest": manifest, "report": json.loads(files["prepare.json"]),
                "gcode": files["program.ngc"], "setup": json.loads(files["setup.json"])}

    def preflight(self, name: str, start_mm: tuple[float, float, float],
                  expected_job_id: str, *, checker=None) -> dict:
        from .job_check import check, save

        if not self._checking.acquire(blocking=False):
            raise ValueError("Trwa kontrola innego zadania; spróbuj ponownie")
        try:
            report = (checker or check)(self._target(name), start_mm,
                                        expected_job_id=expected_job_id)
            reports = self.jobs_dir / ".preflight"
            if reports.is_symlink():
                raise ValueError("Katalog raportów nie może być dowiązaniem")
            reports.mkdir(exist_ok=True)
            save(report, reports / f"{report['job_id']}-{report['report_id']}.json")
            return report
        finally:
            self._checking.release()

    def archive(self, name: str) -> bytes:
        manifest, files = job.read(self._target(name))
        files["manifest.json"] = job.json_text(manifest)
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for filename, text in sorted(files.items()):
                entry = zipfile.ZipInfo(f"{name}/{filename}", date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, text.encode("utf-8"))
        return data.getvalue()


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("program", type=Path)
    parser.add_argument("--machine", type=Path, required=True)
    parser.add_argument("--tools", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="nowy katalog pakietu")
    parser.add_argument("--origin", type=float, nargs=3, required=True, metavar=("X", "Y", "Z"),
                        help="zero detalu w mm układu maszyny, przed korekcją długości")
    parser.add_argument("--offset", choices=job.OFFSETS, default="G54")
    parser.add_argument("--drive-library", type=Path, default=None)


def run(args: argparse.Namespace) -> int:
    try:
        service = JobService(args.program.parent, args.machine, args.tools,
                             args.out.parent, args.drive_library)
        result = service.prepare(args.program.name, args.out.name, tuple(args.origin), args.offset)
    except (ValueError, OSError, sqlite3.Error, MachineConfigError) as error:
        print(f"Prepare: {error}", file=sys.stderr)
        return 2
    print(job.json_text({"name": result["name"], "job_id": result["manifest"]["job_id"],
                         "status": result["report"]["status"]}), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Przygotuj pakiet zadania linumeRT (bez ruchu)")
    add_arguments(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
