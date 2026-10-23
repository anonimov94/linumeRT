# SPDX-License-Identifier: GPL-2.0-or-later
"""Organic Vector: sculpted islands and circular control instruments. Model-Author: Codex."""
from linumert_skin_screen import SkinScreen


class OrganicVectorScreen(SkinScreen):
    LAYOUT = (("dro", 0, 0, 6, 3), ("program", 6, 0, 6, 3),
              ("machine", 0, 3, 6, 4), ("toolpath", 0, 7, 6, 5),
              ("status", 6, 3, 3, 3), ("feed", 6, 6, 3, 3),
              ("tools", 6, 9, 3, 3), ("overrides", 9, 3, 3, 4),
              ("manual", 9, 7, 3, 2), ("workpiece", 9, 9, 3, 3))

    def build(self):
        self.mount()
        self.console_widget = self.console(("cycle", "space", "F", "S", "G0", "space",
                                            "coolant", "spindle", "estop"))
