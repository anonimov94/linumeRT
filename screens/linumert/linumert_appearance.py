# SPDX-License-Identifier: GPL-2.0-or-later
"""Wygląd HMI: palety, własne kolory, walidacja czytelności i zapis ustawień.

Model-Author: Claude · 2026-10-25 · M2 (028, SKIN-02/03) na prośbę właściciela: zmiana kolorystyki
w działającym HMI. Moduł bez Qt: przelicza dziesięć ról kolorów (tło, panel, uniesienie, tekst,
tekst pomocniczy, akcent, ostrzeżenie, błąd, sukces, informacja) na pełny zestaw tokenów powłoki
(`docs/design/tokens.yaml`, sekcja `kolory`); pozostałe tokeny (linie, tła stanów, jaśniejszy
akcent) są wyliczane. Rozmiary, fonty i kompozycja ekranu nie zmieniają się.

Bezpieczeństwo prezentacji: kolor błędu, ostrzeżenia i sukcesu zachowuje znaczenie (czerwony,
bursztynowy, zielony), a każdy tekst i znacznik stanu musi mieć wymagany kontrast z tłem i panelem;
w przeciwnym razie ustawienia nie zostaną zapisane ani zastosowane. Zmiana wyglądu nie wpływa na
żadne polecenie CNC. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from pathlib import Path

VERSION = 1
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# (id roli, token powłoki, etykieta PL)
ROLES = (
    ("background", "bg", "Tło"),
    ("panel", "panel", "Panele"),
    ("raised", "raise", "Podniesienie (przyciski)"),
    ("text", "fg", "Tekst"),
    ("muted", "fg2", "Tekst pomocniczy"),
    ("accent", "teal", "Akcent"),
    ("warning", "amber", "Ostrzeżenie"),
    ("error", "err", "Błąd / E-STOP"),
    ("success", "ok", "Sukces / gotowość"),
    ("info", "info", "Informacja"),
)
ROLE_IDS = tuple(r[0] for r in ROLES)

# Zestawy jak w `linumert_skin_contract.PALETTES` (bez zależności od Qt i podglądów skórek).
PRESETS = {
    "classic-turquoise": ("Classic Turquoise", {
        "background": "#0a0c0f", "panel": "#12171d", "raised": "#182029", "text": "#e8eef4",
        "muted": "#9aa7b4", "accent": "#2dd4bf", "warning": "#fbbf24", "error": "#f87171",
        "success": "#4ade80", "info": "#7dd3fc"}),
    "graphite-gray": ("Graphite Gray", {
        "background": "#202020", "panel": "#404040", "raised": "#606060", "text": "#ffffff",
        "muted": "#e0e0e0", "accent": "#ffffff", "warning": "#fbbf24", "error": "#ffa0a0",
        "success": "#4ade80", "info": "#7dd3fc"}),
    "reactor-green": ("Reactor Green", {
        "background": "#0c110e", "panel": "#162019", "raised": "#213026", "text": "#edf7ee",
        "muted": "#a4b9a8", "accent": "#8bea76", "warning": "#fbbf24", "error": "#f87171",
        "success": "#4ade80", "info": "#7dd3fc"}),
    "ion-blue": ("Ion Blue", {
        "background": "#0c111a", "panel": "#151f2e", "raised": "#202e42", "text": "#edf3ff",
        "muted": "#a7b7d1", "accent": "#70b7ff", "warning": "#fbbf24", "error": "#f87171",
        "success": "#4ade80", "info": "#7dd3fc"}),
    "neon-punk": ("Neon Punk", {
        "background": "#07050d", "panel": "#0e0a18", "raised": "#161026", "text": "#f3eeff",
        "muted": "#ab9fcc", "accent": "#00f0ff", "warning": "#fbbf24", "error": "#f87171",
        "success": "#4ade80", "info": "#7dd3fc"}),
}
DEFAULT_PRESET = "classic-turquoise"


class AppearanceError(ValueError):
    """Niepoprawny plik ustawień albo wartość koloru."""


# ---- kolor ---------------------------------------------------------------------------------
def rgb(color: str) -> tuple[int, int, int]:
    if not isinstance(color, str) or not HEX.match(color):
        raise AppearanceError(f"{color!r}: oczekiwano koloru #rrggbb")
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def hex_of(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(v))) for v in (r, g, b)))


def mix(a: str, b: str, t: float) -> str:
    """Mieszanie kolorów: t = 0 → a, t = 1 → b."""
    ra, rb = rgb(a), rgb(b)
    return hex_of(*(x + (y - x) * t for x, y in zip(ra, rb, strict=True)))


def luminance(color: str) -> float:
    def lin(v: int) -> float:
        s = v / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """Współczynnik kontrastu WCAG (1…21)."""
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ---- walidacja ------------------------------------------------------------------------------
def check(colors: dict[str, str]) -> list[str]:
    """Lista problemów po polsku; pusta = ustawienia można zastosować i zapisać."""
    problems: list[str] = []
    for role, _token, label in ROLES:
        value = colors.get(role)
        try:
            rgb(value)  # type: ignore[arg-type]
        except AppearanceError:
            problems.append(f"{label}: niepoprawny kolor {value!r} (oczekiwano #rrggbb)")
    if problems:
        return problems
    bg, panel = colors["background"], colors["panel"]
    if contrast(bg, panel) < 1.02:
        problems.append("Tło i panele są nie do odróżnienia (zmień jedno z nich)")
    if contrast(colors["panel"], colors["raised"]) < 1.02:
        problems.append("Panele i przyciski są nie do odróżnienia (zmień jedno z nich)")
    # Tekst i znaczniki muszą być czytelne na tle i na panelu (WCAG: 4,5 tekst, 3 elementy).
    for role, label, need in (("text", "Tekst", 4.5), ("muted", "Tekst pomocniczy", 3.0),
                              ("accent", "Akcent", 3.0), ("warning", "Ostrzeżenie", 3.0),
                              ("error", "Błąd / E-STOP", 4.5), ("success", "Sukces", 3.0),
                              ("info", "Informacja", 3.0)):
        for base, base_name in ((bg, "tle"), (panel, "panelu")):
            ratio = contrast(colors[role], base)
            if ratio < need:
                problems.append(f"{label}: kontrast {ratio:.1f}:1 na {base_name}, wymagane "
                                f"{need}:1")
    # Znaczenie kolorów stanu nie może się zatrzeć (E-STOP, ostrzeżenia, gotowość).
    r, g, b = rgb(colors["error"])
    if not (r >= 1.3 * max(g, b) and r >= 140):
        problems.append("Błąd / E-STOP musi pozostać wyraźnie czerwony (dominuje składowa R)")
    r, g, b = rgb(colors["success"])
    if not (g >= 1.15 * max(r, b) and g >= 120):
        problems.append("Sukces musi pozostać wyraźnie zielony (dominuje składowa G)")
    r, g, b = rgb(colors["warning"])
    if not (r >= 140 and g >= 0.55 * r and g > b * 1.3):
        problems.append("Ostrzeżenie musi pozostać bursztynowe/żółte (R i G wysokie, B niskie)")
    return problems


# ---- tokeny powłoki --------------------------------------------------------------------------
def derived_tokens(colors: dict[str, str]) -> dict[str, str]:
    """Pełny zestaw tokenów `kolory` powłoki z dziesięciu ról."""
    bg, panel, raised = colors["background"], colors["panel"], colors["raised"]
    text, muted, accent = colors["text"], colors["muted"], colors["accent"]
    out = {role_token: colors[role] for role, role_token, _ in ROLES}
    out.update({
        "bg2": mix(bg, panel, 0.4),
        "line": mix(raised, muted, 0.22),
        "line2": mix(raised, muted, 0.4),
        "fg3": mix(muted, bg, 0.45),
        "teal2": mix(accent, text, 0.35),
        "tealbg": mix(bg, accent, 0.15),
        "amberbg": mix(bg, colors["warning"], 0.15),
        "okbg": mix(bg, colors["success"], 0.15),
        "errbg": mix(bg, colors["error"], 0.15),
        "infobg": mix(bg, colors["info"], 0.15),
    })
    return out


def apply_to_tokens(tokens: dict, colors: dict[str, str]) -> dict:
    """Kopia `tokens` z podmienionymi kolorami; rozmiary i fonty bez zmian."""
    problems = check(colors)
    if problems:
        raise AppearanceError("; ".join(problems))
    new = copy.deepcopy(tokens)
    new["kolory"] = {**new.get("kolory", {}), **derived_tokens(colors)}
    return new


# ---- ustawienia i zapis ---------------------------------------------------------------------
def default_colors() -> dict[str, str]:
    return dict(PRESETS[DEFAULT_PRESET][1])


def settings_path() -> Path:
    env = os.environ.get("LINUMERT_APPEARANCE")
    return Path(env) if env else Path.home() / ".config" / "linumert" / "appearance.json"


def load(path: Path | None = None) -> dict:
    """{'preset': id | 'custom', 'colors': {...}}; brak/uszkodzony plik = domyślny wygląd."""
    path = path or settings_path()
    fallback = {"preset": DEFAULT_PRESET, "colors": default_colors(), "note": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback
    except (OSError, ValueError) as exc:
        return {**fallback, "note": f"Plik wyglądu uszkodzony ({exc}); użyto domyślnego."}
    try:
        if data.get("version") != VERSION:
            raise AppearanceError("nieobsługiwana wersja ustawień wyglądu")
        colors = {role: data["colors"][role] for role in ROLE_IDS}
        problems = check(colors)
        if problems:
            raise AppearanceError("; ".join(problems))
        preset = data.get("preset", "custom")
        if preset != "custom" and preset not in PRESETS:
            preset = "custom"
        return {"preset": preset, "colors": colors, "note": ""}
    except (AppearanceError, KeyError, TypeError, AttributeError) as exc:
        return {**fallback, "note": f"Ustawienia wyglądu odrzucone ({exc}); użyto domyślnych."}


def save(preset: str, colors: dict[str, str], path: Path | None = None) -> Path:
    """Zapis atomowy; odmowa przy kolorach, które nie przechodzą kontroli czytelności."""
    problems = check(colors)
    if problems:
        raise AppearanceError("; ".join(problems))
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"version": VERSION, "preset": preset,
                          "colors": {r: colors[r] for r in ROLE_IDS}}, indent=1, sort_keys=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path


def reset(path: Path | None = None) -> None:
    (path or settings_path()).unlink(missing_ok=True)
