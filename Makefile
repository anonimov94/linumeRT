# linumeRT - zadania deweloperskie. Wymaga Pythona >= 3.11.
PYTHON ?= python3
# W CI i w venv zostaw puste; w systemowym Pythonie Debiana: PIP_FLAGS=--break-system-packages
PIP_FLAGS ?=

.PHONY: install lint test test-c test-linuxcnc

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

# No-op do sesji 003 (LinuxCNC w srodowisku agenta).
test-linuxcnc:
	@if [ -x tools/ci/build-linuxcnc.sh ]; then $(PYTHON) -m pytest -m linuxcnc; \
	else echo "test-linuxcnc: brak tools/ci/build-linuxcnc.sh (sesja 003) - pomijam"; fi
