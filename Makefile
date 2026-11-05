# linumeRT - zadania deweloperskie. Wymaga Pythona >= 3.11.
PYTHON ?= python3
# W CI i w venv zostaw puste; w systemowym Pythonie Debiana: PIP_FLAGS=--break-system-packages
PIP_FLAGS ?=

.PHONY: install lint test test-c test-san test-linuxcnc plant-matrix native

install:
	$(PYTHON) -m pip install $(PIP_FLAGS) -e ".[dev]"

lint:
	$(PYTHON) tools/roadmap.py --check
	$(PYTHON) -m ruff check .

# Testy i pokrycie wymagań REQ (sesja 024, REQ-QA-01).
test:
	$(PYTHON) -m pytest
	$(PYTHON) tools/check_requirements.py

# Scenariusze Plant na 5 maszynach z config/machines (sesja 024, REQ-QA-02; job CI plant-matrix).
plant-matrix:
	$(MAKE) -C plant/core shared
	$(PYTHON) tools/run_scenario.py --matrix --out build/raporty/matrix
	$(PYTHON) tools/run_scenario.py --out build/raporty/scenariusze

# Testy C: rdzeń dynamiki Plant (od sesji 011) i biblioteka natywna core/native (2026-11-05),
# potem testy symulacji i CAM z włączoną biblioteką (LINUMERT_NATIVE=1). W `make test`
# conftest wymusza ścieżkę referencyjną Pythona, a tests/test_native.py porównuje obie.
NATIVE_TESTS := tests/test_native.py tests/test_sim_engine.py tests/test_sim_report.py \
	tests/test_sim_worker.py tests/test_sim_diagnostics.py tests/test_gen_relief.py \
	tests/test_gen_pockets.py tests/test_gen_contours.py tests/test_resume_preview.py \
	tests/test_render_mesh.py

test-c:
	@if [ -f plant/core/Makefile ]; then $(MAKE) -C plant/core test; \
	else echo "test-c: brak plant/core/Makefile - pomijam"; fi
	$(MAKE) -C core/native test shared
	LINUMERT_NATIVE=1 $(PYTHON) -m pytest -q $(NATIVE_TESTS)

# Biblioteka natywna dla ścieżek obliczeniowych poza RT (core/linumert/native.py).
native:
	$(MAKE) -C core/native shared

# Te same testy C z ASan/UBSan (osobne katalogi build-san).
test-san:
	$(MAKE) -C plant/core test-san
	$(MAKE) -C core/native test-san

# Testy z LinuxCNC RIP pod Xvfb (sesja 003; wymaga tools/ci/build-linuxcnc.sh).
test-linuxcnc:
	PYTHON=$(PYTHON) xvfb-run -a -s '-screen 0 1440x1100x24' bash tools/ci/test-linuxcnc.sh
