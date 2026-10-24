# SPDX-License-Identifier: GPL-2.0-or-later
"""Classic Digital: rectangular digital instrument console. Model-Author: Codex.

Classic × Neon (Model-Author: Claude): role 'toolpath' i 'machine' rysuje szybki renderer
QPainter ze wspólną sceną — zbliżenie na detal i cała maszyna z następnym punktem i DTG.
"""
from linumert_neon_render import SettingsStore
from linumert_neon_view import NeonDetailPanel, NeonPathView, PathScene
from linumert_skin_screen import SkinScreen
from linumert_skin_strings import text
from PyQt5 import QtWidgets


class ClassicDigitalScreen(SkinScreen):
    AXES = "XYZAB"
    LAYOUT = (("dro", 0, 0, 5, 3), ("program", 5, 0, 5, 3),
              ("toolpath", 0, 3, 7, 6), ("machine", 0, 9, 7, 3),
              ("feed", 7, 3, 3, 4), ("tools", 7, 7, 3, 2),
              ("workpiece", 7, 9, 3, 3), ("alarms", 10, 0, 2, 4),
              ("status", 10, 4, 2, 4), ("overrides", 10, 8, 2, 4))
    NEON_ROLES = ("toolpath", "machine")

    def build(self):
        self.mount()
        self.console_widget = self.console(("cycle", "edit", "dry_run", "block_delete",
                                            "space", "mode", "M01", "M3", "M8", "estop"))

    @property
    def path_scene(self):
        return self.shared.get("path_scene")

    def body(self, role):
        if role not in self.NEON_ROLES:
            return super().body(role)
        scene = self.path_scene
        if scene is None:
            if not self.viewport_factory:
                # Monitor na żywo: uczciwy stan programu; studium układu: zwykły opis.
                note = self.shared.get("program_note")
                if note is None:
                    return super().body(role)
                label = QtWidgets.QLabel(note)
                label.setWordWrap(True)
                return label
            from linumert.programs.toolpath import demo_toolpath
            scene = self.shared["path_scene"] = PathScene(
                demo_toolpath(), parent=self.shared.get("owner", self))
        # Sposób renderowania każdego widoku zapisany w profilu operatora (⚙ w rogu widoku).
        store = self.shared.setdefault("render_store", SettingsStore())
        if role == "toolpath":
            view = NeonDetailPanel(scene, self.palette, store)
        else:
            view = NeonPathView(scene, "machine", self.palette, store)
        view.setToolTip(text("neon_scene" if not scene.live else "neon_live", self.preferences))
        self.viewports[role] = view
        return view
