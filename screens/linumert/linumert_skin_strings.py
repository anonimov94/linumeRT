# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared strings for the skin prototype, independent of palette and layout.

Model-Author: Codex. Alarm identifiers remain outside the translation catalog.
This is not a translation of every existing QtDragon/linumeRT page.
"""

from types import MappingProxyType

from linumert_skin_contract import PresentationPreferences

_EN = {
    "edit": "Edit", "dry_run": "Dry run", "block_delete": "Block delete",
    "apply": "Apply", "cancel": "Cancel",
    'feed_spindle': 'Feed / spindle',
    'overrides': 'Overrides',
    'machine_status': 'Machine status',
    'power': 'Power',
    'spindle': 'Spindle',
    'coolant': 'Coolant',
    'door': 'Door',
    'estop_status': 'E-STOP status',
    "preview": "Presentation prototype — no machine connection",
    "maximize": "Maximize / restore panel",
    "skin": "Skin", "theme": "Color theme", "language": "Language",
    "start": "Start", "homing": "Homing", "work_offset": "Work offset",
    "tools": "Tools", "program": "Program", "simulation": "Simulation",
    "production": "Production", "diagnostics": "Diagnostics", "settings": "Settings",
    "machine": "Machine", "toolpath": "Toolpath", "workpiece": "Workpiece",
    "alarms": "Alarms", "stop": "Stop", "feed_hold": "Feed hold",
    "mode_manual": "Manual / JOG", "mode_mdi": "MDI", "mode_auto": "AUTO",
    "estop_active": "E-STOP active", "estop_clear": "E-STOP circuit closed",
    "status_unknown": "Machine status unavailable",
    "homed": "Homed", "not_homed": "Not homed",
    "machine_on": "Machine enabled", "machine_off": "Machine disabled",
    "renderer_pending": "3D renderer not connected",
    "offline_scene": "Illustrative model · drag to orbit · wheel to zoom",
    "sample_program": "Sample program — not loaded into CNC",
    "demo_controls": "Preview only — machine commands disabled",
}
_PL = {
    "edit": "Edycja", "dry_run": "Próba", "block_delete": "Pomijanie bloków",
    "apply": "Zastosuj", "cancel": "Anuluj",
    'feed_spindle': 'Posuw / wrzeciono',
    'overrides': 'Korekcje',
    'machine_status': 'Stan maszyny',
    'power': 'Zasilanie',
    'spindle': 'Wrzeciono',
    'coolant': 'Chłodziwo',
    'door': 'Drzwi',
    'estop_status': 'Stan E-STOP',
    "preview": "Prototyp prezentacji — bez połączenia z maszyną",
    "maximize": "Powiększ / przywróć panel",
    "skin": "Skórka", "theme": "Motyw kolorystyczny", "language": "Język",
    "start": "Start", "homing": "Bazowanie", "work_offset": "Zero detalu",
    "tools": "Narzędzia", "program": "Program", "simulation": "Symulacja",
    "production": "Produkcja", "diagnostics": "Diagnostyka", "settings": "Ustawienia",
    "machine": "Maszyna", "toolpath": "Ścieżka", "workpiece": "Detal",
    "alarms": "Alarmy", "stop": "Stop", "feed_hold": "Wstrzymanie posuwu",
    "mode_manual": "Ręczne / JOG", "mode_mdi": "MDI", "mode_auto": "AUTO",
    "estop_active": "E-STOP aktywny", "estop_clear": "Obwód E-STOP zamknięty",
    "status_unknown": "Stan maszyny niedostępny",
    "homed": "Zbazowana", "not_homed": "Niezbazowana",
    "machine_on": "Maszyna włączona", "machine_off": "Maszyna wyłączona",
    "renderer_pending": "Renderer 3D niepodłączony",
    "offline_scene": "Model poglądowy · przeciągnij, aby obrócić · kółko: zoom",
    "sample_program": "Program przykładowy — niewczytany do CNC",
    "demo_controls": "Tylko podgląd — komendy maszyny wyłączone",
}
STRINGS = MappingProxyType({"en": MappingProxyType(_EN), "pl": MappingProxyType(_PL)})


def text(key: str, preferences: PresentationPreferences) -> str:
    """Unknown keys raise KeyError rather than silently mixing languages."""
    return STRINGS[preferences.language][key]
