# linumeRT - zadania deweloperskie. Wymaga Pythona >= 3.11.
PYTHON ?= python3
# W CI i w venv zostaw puste; w systemowym Pythonie Debiana: PIP_FLAGS=--break-system-packages
PIP_FLAGS ?=

.PHONY: install lint test test-c test-san test-linuxcnc

install:
	$(PYTHON) -m pip install $(PIP_FLAGS) -e ".[dev]"

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m pytest

# Testy rdzenia dynamiki Plant w C (od sesji 011).
test-c:
	@if [ -f plant/core/Makefile ]; then $(MAKE) -C plant/core test; \
	else echo "test-c: brak plant/core/Makefile - pomijam"; fi

# Te same testy C z ASan/UBSan (osobny katalog plant/core/build-san).
test-san:
	$(MAKE) -C plant/core test-san

# Testy z LinuxCNC RIP pod Xvfb (sesja 003; wymaga tools/ci/build-linuxcnc.sh).
test-linuxcnc:
	PYTHON=$(PYTHON) xvfb-run -a -s '-screen 0 1440x1100x24' bash tools/ci/test-linuxcnc.sh
