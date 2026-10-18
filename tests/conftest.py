from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _linuxcnc_cleanup(request):
    """Po teście z markerem `linuxcnc` nie zostają procesy LinuxCNC/HAL (sesja 008)."""
    yield
    if request.node.get_closest_marker("linuxcnc") is not None:
        from rip_support import cleanup_linuxcnc

        cleanup_linuxcnc()
