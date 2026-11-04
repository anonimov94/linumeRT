"""Usługa konfiguracji: ``machine.yaml`` → walidacja → INI/HAL (generator).

SPDX-License-Identifier: GPL-2.0-or-later

Jedno źródło prawdy konfiguracji to ``machine.yaml`` (wspólne dla LinuxCNC i Plant).
Usługa pozwala GUI:

- przejrzeć maszyny z ``config/machines`` wraz z wynikiem walidacji,
- wygenerować INI/HAL dla celu ``sim`` albo ``plant`` **najpierw do podglądu**
  (``write=false``), a dopiero potem zapisać (``write=true``),
- sprawdzić wdrożoną konfigurację LinuxCNC (``deployment.check_deployment``).

Generator nie dotyka sprzętu: weryfikacja fizyczna pozostaje osobnym krokiem odbioru.
"""

from __future__ import annotations

from pathlib import Path

from linumert.machine import configgen, deployment
from linumert.machine.schema import MachineConfigError, load_machine
from linumert.machine.validate import validate_machine

from ..errors import Conflict, InvalidRequest, NotFound
from ..schema import (
    ConfigGenerateOut,
    ConfigGenerateRequest,
    ConfigValidateOut,
    DeploymentCheckOut,
    DeploymentCheckRequest,
    MachineConfigList,
    MachineConfigName,
    MachineConfigOut,
    MachineConfigSummary,
)
from .paths import ProjectPaths


class MachineConfigService:
    """Operacje domeny ``config``."""

    domain = "config"

    def __init__(self, paths: ProjectPaths, drives_dir: Path | None = None):
        self.paths = paths
        self.drives_dir = drives_dir or paths.drives

    # ---- przegląd ----------------------------------------------------------
    def list(self) -> MachineConfigList:
        root = self.paths.machines
        items: list[MachineConfigSummary] = []
        for path in sorted(root.glob("*.y*ml")):
            axes: list[str] = []
            errors: list[str] = []
            try:
                cfg = load_machine(path)
                axes = [a.letter for a in cfg.axes]
                errors = validate_machine(cfg, self._templates())
            except MachineConfigError as exc:
                errors = list(exc.errors)
            except Exception as exc:  # uszkodzony YAML nie może położyć listy
                errors = [f"nie udało się wczytać: {exc}"]
            items.append(MachineConfigSummary(name=path.name, path=str(path), axes=axes,
                                              valid=not errors, errors=errors))
        return MachineConfigList(root=str(root), machines=items)

    def get(self, request: MachineConfigName) -> MachineConfigOut:
        path = self.paths.machine(request.name)
        try:
            cfg = load_machine(path)
        except MachineConfigError as exc:
            raise InvalidRequest(f"konfiguracja {path.name} jest niepoprawna: {exc}",
                                 details={"errors": exc.errors}) from exc
        return MachineConfigOut(
            name=cfg.machine.name, path=str(path),
            axes=[a.letter for a in cfg.axes],
            data=_plain(cfg),
        )

    def validate(self, request: MachineConfigName) -> ConfigValidateOut:
        path = self.paths.machine(request.name)
        try:
            cfg = load_machine(path)
        except MachineConfigError as exc:
            return ConfigValidateOut(ok=False, errors=list(exc.errors))
        errors = validate_machine(cfg, self._templates())
        return ConfigValidateOut(ok=not errors, errors=errors)

    # ---- generator ---------------------------------------------------------
    def generate(self, request: ConfigGenerateRequest) -> ConfigGenerateOut:
        path = self.paths.machine(request.name)
        try:
            cfg = load_machine(path)
        except MachineConfigError as exc:
            raise InvalidRequest(f"konfiguracja {request.name} jest niepoprawna: {exc}",
                                 details={"errors": exc.errors}) from exc
        errors = validate_machine(cfg, self._templates())
        if errors:
            raise Conflict(f"konfiguracja {request.name} nie przeszła walidacji",
                           details={"errors": errors})
        try:
            files = configgen.render(cfg, request.target)
        except (MachineConfigError, ValueError) as exc:
            raise InvalidRequest(f"generowanie konfiguracji nie powiodło się: {exc}") from exc
        written: list[str] = []
        if request.write:
            out_dir = (Path(request.out_dir) if request.out_dir
                       else self.paths.state / "konfiguracja")
            out_dir.mkdir(parents=True, exist_ok=True)
            for name, text in files.items():
                target = out_dir / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
                written.append(str(target))
        return ConfigGenerateOut(
            files=files, written=written,
            message=f"wygenerowano {len(files)} plików"
                    + (f", zapisano {len(written)}" if written else " (podgląd)"),
        )

    def check_deployment(self, request: DeploymentCheckRequest) -> DeploymentCheckOut:
        path = Path(request.ini)
        if not path.exists():
            path = self.paths.resolve(request.ini, self.paths.config,
                                      extensions=(".ini",))
        try:
            parser = deployment.read_deployment(path)
        except (OSError, deployment.__dict__.get("DeploymentError", Exception)) as exc:
            raise NotFound(f"nie udało się wczytać {path}: {exc}") from exc
        issues = deployment.check_deployment(parser)
        hal = [str(p) for p in deployment.hal_files_from_ini(path)]
        return DeploymentCheckOut(ok=not issues, issues=issues, hal_files=hal)

    # ---- pomocnicze --------------------------------------------------------
    def _templates(self) -> set[str] | None:
        if not self.drives_dir.exists():
            return None
        return {p.stem for p in self.drives_dir.glob("*.yaml")}


def _plain(cfg) -> dict:
    """Konfiguracja jako zwykły dict (pydantic → JSON) do podglądu w GUI."""
    try:
        return cfg.model_dump(mode="json", exclude_none=True)
    except Exception:
        return {}


__all__ = ["MachineConfigService"]
