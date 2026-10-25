"""Biblioteka maszyn w panelu Plant: lista, kopia, zmiana nazwy, kosz, aktywacja, edycja YAML.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-25 · prośba właściciela: każdy parametr edytowalny, nowe maszyny,
edycja starych, usuwanie.

Maszyny to pliki `*.yaml` w jednym katalogu (domyślnie katalog aktywnego `machine.yaml`).
`machine.yaml` pozostaje jedynym źródłem prawdy (REQ-VM-01); każda zmiana przechodzi pełną
walidację REQ-VM-11 przed zapisem (jak `MachineEditor.save`). Usunięcie to przeniesienie do kosza
`<state>/machines/_kosz/` (można przywrócić), nie trwałe kasowanie; aktywnej maszyny nie wolno
usunąć ani przemianować. Aktywacja podmienia model w działającym Plant (tylko przy wyłączonych
napędach i tej samej liczbie osi LRT-NET, jak `MachineEditor.reload`); przy błędzie wraca
poprzednia maszyna. Moduł nie zależy od FastAPI. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

from ..drive_library import YAML_LOADER
from .editor import EditorError, MachineEditor, atomic_write_text

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_\-]{0,63}$")
FILE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_\-]{0,63}\.yaml$")
TRASH_RE = re.compile(r"^\d{8}_\d{6}(?:_[a-f0-9]{32})?__[A-Za-z][A-Za-z0-9_\-]{0,63}\.yaml$")


class MachineLibrary:
    def __init__(self, editor: MachineEditor, directory: Path | None = None):
        self.editor = editor
        self._directory = directory

    # ---- katalog i nazwy -------------------------------------------------------------
    @property
    def directory(self) -> Path:
        return Path(self._directory) if self._directory else self.editor.path.parent

    @property
    def trash(self) -> Path:
        return self.editor.state_dir / "machines" / "_kosz"

    def _file(self, file: str) -> Path:
        if not FILE_RE.fullmatch(file):
            raise EditorError(f"{file}: niepoprawna nazwa pliku (litery, cyfry, _, -, .yaml)")
        path = self.directory / file
        if not path.is_file():
            raise EditorError(f"brak maszyny {file}")
        return path

    @staticmethod
    def _name(name: str) -> str:
        if not NAME_RE.fullmatch(name or ""):
            raise EditorError(f"{name!r}: nazwa to litera, potem litery, cyfry, _ lub - (do 64)")
        return name

    def _is_active(self, path: Path) -> bool:
        try:
            return path.resolve() == self.editor.path.resolve()
        except EditorError:
            return False

    @staticmethod
    def _read(path: Path) -> dict:
        try:
            data = yaml.load(path.read_text(encoding="utf-8"), Loader=YAML_LOADER)
        except (OSError, yaml.YAMLError) as exc:
            raise EditorError(f"{path.name}: nie można wczytać ({exc})") from None
        if not isinstance(data, dict):
            raise EditorError(f"{path.name}: oczekiwano mapy YAML")
        return data

    def _write(self, path: Path, data: dict, comment: str) -> None:
        text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
        header = (f"# linumeRT · machine.yaml zapisany w panelu Plant "
                  f"{time.strftime('%Y-%m-%d %H:%M:%S')} — {comment}\n")
        atomic_write_text(path, header + text)

    # ---- lista -----------------------------------------------------------------------
    def catalog(self) -> list[dict[str, Any]]:
        out = []
        for path in sorted(self.directory.glob("*.yaml")):
            try:
                data = self._read(path)
            except EditorError:
                continue
            meta = data.get("machine")
            if not isinstance(meta, dict):
                continue                              # inny plik YAML w katalogu
            errors = self.editor.validate(data)
            out.append({"file": path.name, "name": meta.get("name", path.stem),
                        "type": meta.get("type", ""),
                        "axes": "".join(str(a.get("letter", "?")) for a in data.get("axes") or []),
                        "drives": len(data.get("drives") or []), "valid": not errors,
                        "errors": errors[:3], "active": self._is_active(path)})
        return out

    def trashed(self) -> list[dict[str, str]]:
        if not self.trash.is_dir():
            return []
        return [{"file": p.name, "machine": p.name.split("__", 1)[1]}
                for p in sorted(self.trash.glob("*.yaml")) if TRASH_RE.fullmatch(p.name)]

    # ---- operacje ----------------------------------------------------------------------
    def clone(self, source: str, new_name: str) -> dict:
        """Nowa maszyna jako kopia istniejącej (z nową nazwą w `machine.name`)."""
        src = self._file(source)
        name = self._name(new_name)
        target = self.directory / f"{name}.yaml"
        if target.exists():
            raise EditorError(f"maszyna {target.name} już istnieje")
        data = self._read(src)
        data.setdefault("machine", {})["name"] = name
        errors = self.editor.validate(data)
        if errors:
            raise EditorError(errors)
        self._write(target, data, f"kopia {src.name}")
        return {"file": target.name, "name": name, "based_on": src.name}

    def rename(self, file: str, new_name: str) -> dict:
        path = self._file(file)
        if self._is_active(path):
            raise EditorError("aktywnej maszyny nie można przemianować (najpierw aktywuj inną)")
        name = self._name(new_name)
        target = self.directory / f"{name}.yaml"
        if target.exists():
            raise EditorError(f"maszyna {target.name} już istnieje")
        data = self._read(path)
        data.setdefault("machine", {})["name"] = name
        errors = self.editor.validate(data)
        if errors:
            raise EditorError(errors)
        self._write(target, data, f"zmiana nazwy z {path.name}")
        path.unlink()
        return {"file": target.name, "name": name}

    def delete(self, file: str) -> dict:
        """Przeniesienie do kosza (nie trwałe usunięcie); aktywnej maszyny nie wolno."""
        path = self._file(file)
        if self._is_active(path):
            raise EditorError("aktywnej maszyny nie można usunąć (najpierw aktywuj inną)")
        self.trash.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        target = self.trash / f"{stamp}_{uuid.uuid4().hex}__{path.name}"
        shutil.move(str(path), str(target))
        return {"trashed": target.name}

    def restore(self, trashed: str) -> dict:
        if not TRASH_RE.fullmatch(trashed):
            raise EditorError(f"{trashed}: niepoprawna nazwa z kosza")
        src = self.trash / trashed
        if not src.is_file():
            raise EditorError(f"brak {trashed} w koszu")
        target = self.directory / trashed.split("__", 1)[1]
        if target.exists():
            raise EditorError(f"maszyna {target.name} już istnieje")
        shutil.move(str(src), str(target))
        return {"file": target.name}

    def activate(self, file: str) -> dict:
        """Podmienia maszynę w działającym Plant; przy błędzie przywraca poprzednią."""
        path = self._file(file)
        errors = self.editor.validate(self._read(path))
        if errors:
            raise EditorError(errors)
        cfg = self.editor.server.cfg
        previous = cfg.machine
        cfg.machine = path
        try:
            return {"file": path.name, **self.editor.reload()}
        except BaseException:
            cfg.machine = previous
            raise

    # ---- edycja dowolnego parametru jako YAML --------------------------------------------
    def get_text(self) -> dict:
        path = self.editor.path
        return {"file": path.name, "text": path.read_text(encoding="utf-8")}

    def parse_text(self, text: str) -> dict:
        try:
            data = yaml.load(text, Loader=YAML_LOADER)
        except yaml.YAMLError as exc:
            raise EditorError(f"YAML: {exc}") from None
        if not isinstance(data, dict):
            raise EditorError("YAML: oczekiwano mapy na najwyższym poziomie")
        return data

    def validate_text(self, text: str) -> list[str]:
        try:
            return self.editor.validate(self.parse_text(text))
        except EditorError as exc:
            return exc.errors

    def save_text(self, text: str, comment: str = "") -> dict:
        return self.editor.save(self.parse_text(text), comment)
