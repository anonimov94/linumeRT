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

# No-op do sesji 011 (rdzen dynamiki Plant w C).
test-c:
	@if [ -f plant/core/Makefile ]; then $(MAKE) -C plant/core test; \
	else echo "test-c: brak plant/core/Makefile (rdzen C powstaje w sesji 011) - pomijam"; fi

test-linuxcnc:
	PYTHON=$(PYTHON) xvfb-run -a -s '-screen 0 1440x900x24' bash tools/ci/test-linuxcnc.sh
