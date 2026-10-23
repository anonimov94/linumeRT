# SPDX-License-Identifier: GPL-2.0-or-later
"""Classic Digital: rectangular digital instrument console. Model-Author: Codex."""
from linumert_skin_screen import SkinScreen


class ClassicDigitalScreen(SkinScreen):
    AXES = "XYZAB"
    LAYOUT = (("dro", 0, 0, 5, 3), ("program", 5, 0, 5, 3),
              ("toolpath", 0, 3, 7, 6), ("machine", 0, 9, 7, 3),
              ("feed", 7, 3, 3, 4), ("tools", 7, 7, 3, 2),
              ("workpiece", 7, 9, 3, 3), ("alarms", 10, 0, 2, 4),
              ("status", 10, 4, 2, 4), ("overrides", 10, 8, 2, 4))

    def build(self):
        self.mount()
        self.console_widget = self.console(("cycle", "edit", "dry_run", "block_delete",
                                            "space", "mode", "M01", "M3", "M8", "estop"))
