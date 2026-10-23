# SPDX-License-Identifier: GPL-2.0-or-later
"""Explicit registry of independently composed Qt screens. Model-Author: Codex."""
from linumert_skin_classic import ClassicDigitalScreen
from linumert_skin_cyberdeck import CyberdeckScreen
from linumert_skin_industrial import IndustrialProScreen
from linumert_skin_organic import OrganicVectorScreen

SCREENS = {"classic-digital": ClassicDigitalScreen, "industrial-pro": IndustrialProScreen,
           "cyberdeck": CyberdeckScreen, "organic-vector": OrganicVectorScreen}
LAYOUTS = {name: screen.LAYOUT for name, screen in SCREENS.items()}
