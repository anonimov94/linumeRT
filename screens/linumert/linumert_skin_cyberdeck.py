# SPDX-License-Identifier: GPL-2.0-or-later
"""Cyberdeck: asymmetric angular cockpit with a lower control deck. Model-Author: Codex."""
from linumert_skin_screen import SkinScreen


class CyberdeckScreen(SkinScreen):
    STATUS_LOCATION = "footer"
    LAYOUT = (("dro", 0, 0, 6, 4), ("program", 0, 4, 6, 3),
              ("toolpath", 0, 7, 6, 5), ("machine", 6, 0, 6, 4),
              ("tools", 6, 4, 3, 4), ("diagnostics", 6, 8, 3, 4),
              ("overrides", 9, 4, 3, 3), ("manual", 9, 7, 3, 3),
              ("workpiece", 9, 10, 3, 2))

    def build(self):
        self.mount()
        self.console_widget = self.console(("mode", "cycle", "space", "M3", "M8", "power", "estop"))
