#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Bezpieczna edycja Zero detalu bez importowania LinuxCNC/QtVCP. Model-Author: Codex."""

import argparse
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "core"), str(ROOT / "screens/linumert")]

import linumert_shell_model as model  # noqa: E402
from linumert_offsets_page import OffsetsPage  # noqa: E402
from PyQt5 import QtWidgets  # noqa: E402


class OfflineAction:
    def CALL_MDI(self, _command):
        raise RuntimeError("Podgląd offline: polecenia maszyny są wyłączone")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv[:1])
    with tempfile.TemporaryDirectory(prefix="linumert-preview-") as temporary:
        shell = SimpleNamespace(s=model.ShellState(), c=model.load_tokens()["kolory"],
                                preview=True, action=OfflineAction(),
                                info=SimpleNamespace(INIPATH=str(Path(temporary) / "offline.ini")))
        window = QtWidgets.QWidget()
        window.setObjectName("lrtRoot")
        window.setStyleSheet(model.shell_qss(model.load_tokens()))
        window.setWindowTitle("PODGLĄD OFFLINE — linumeRT · Zero detalu")
        layout = QtWidgets.QVBoxLayout(window)
        banner = QtWidgets.QLabel("PODGLĄD OFFLINE — edycja bez połączenia z maszyną. "
                                  "Zapisy tylko tymczasowe; zamknięcie usuwa próby.")
        banner.setWordWrap(True)
        layout.addWidget(banner)
        page = OffsetsPage(shell)
        page.shape.setCurrentIndex(3)
        page.zero_button.setToolTip("Offline — ustawianie zer maszyny jest wyłączone")
        layout.addWidget(page, 1)
        try:
            import yaml

            machine = yaml.safe_load((ROOT / "config/sim/linumert_xyz/machine.yaml").read_text())
            bodies = [{**b, "attached": b["attached_to"]} for b in machine["collision_bodies"]]
            page.scene_event({"ev": "machine", "name": machine["machine"]["name"],
                              "bodies": bodies})
        except (ImportError, OSError, KeyError, ValueError):
            pass  # podgląd z domyślnym stołem nadal działa
        window.resize(1280, 800)
        window.show()
        app.processEvents()
        assert "linuxcnc" not in sys.modules and "qtvcp.core" not in sys.modules
        print("PODGLĄD OFFLINE GOTOWY — bez LinuxCNC, zapisy w katalogu tymczasowym", flush=True)
        if args.snapshot:
            args.snapshot.parent.mkdir(parents=True, exist_ok=True)
            return 0 if window.grab().save(str(args.snapshot)) else 1
        return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
