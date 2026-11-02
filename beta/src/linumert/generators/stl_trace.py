# SPDX-License-Identifier: GPL-2.0-or-later
"""Persist a chosen STL section as a tool-centre engraving path. Model-Author: Codex."""
from .base import Field
from .path_geometry import PathTrace


class StlSection(PathTrace):
    name = "stl_section"
    version = 1
    title = "STL — kontur przekroju XY"
    fields = (Field("source", "text", "Źródło i przekrój", default=""),) + PathTrace.fields


def register(registry=None):
    from .registry import DEFAULT_REGISTRY

    (registry or DEFAULT_REGISTRY).register(StlSection)
