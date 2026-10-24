# SPDX-License-Identifier: GPL-2.0-or-later
"""HMI review contract: inventory must track the actual UI and handlers."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hmi_inventory", ROOT / "tools/hmi_inventory.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def test_hmi_inventory_matches_current_sources():
    assert (ROOT / inventory.OUTPUT).read_text(encoding="utf-8") == inventory.render()
