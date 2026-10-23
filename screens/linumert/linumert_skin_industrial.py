# SPDX-License-Identifier: GPL-2.0-or-later
"""Industrial Pro: large machine, central coordinates, right program. Model-Author: Codex."""
from linumert_skin_screen import SkinScreen


class IndustrialProScreen(SkinScreen):
    LAYOUT = (("machine", 0, 0, 7, 4), ("workpiece", 7, 0, 3, 2),
              ("overrides", 7, 2, 3, 2), ("dro", 0, 4, 5, 4),
              ("feed", 5, 4, 2, 4), ("tools", 7, 4, 3, 4),
              ("alarms", 10, 0, 2, 8), ("toolpath", 0, 8, 6, 4),
              ("program", 6, 8, 6, 4))

    def build(self):
        self.mount()
        self.console_widget = self.console(("power", "mode", "space", "cycle",
                                            "space", "coolant", "door", "M8", "estop"))
