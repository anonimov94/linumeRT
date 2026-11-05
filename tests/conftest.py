import os
from pathlib import Path

import pytest

# Ścieżka referencyjna Pythona w całym przebiegu, chyba że wywołujący ustawił inaczej
# (`make test-c`: LINUMERT_NATIVE=1). Porównanie obu ścieżek: tests/test_native.py.
os.environ.setdefault("LINUMERT_NATIVE", "0")

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _linuxcnc_cleanup(request):
    """Po teście z markerem `linuxcnc` nie zostają procesy LinuxCNC/HAL (sesja 008)."""
    yield
    if request.node.get_closest_marker("linuxcnc") is not None:
        from rip_support import cleanup_linuxcnc

        cleanup_linuxcnc()
