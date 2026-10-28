# linumeRT headless (beta) — zadania deweloperskie. Wymaga Pythona >= 3.11.
# Aplikacja bez GUI: nie ma tu Xvfb, Qt ani OpenGL — testy idą bez serwera X.
PYTHON ?= python3
PIP_FLAGS ?=

.PHONY: install lint test test-service test-c serve contract check-no-gui clean

install:
	$(PYTHON) -m pip install $(PIP_FLAGS) -e ".[dev]"

lint:
	$(PYTHON) -m ruff check src tests tools
	$(PYTHON) tools/check_no_gui.py

# Testy aplikacji headless i przejętego rdzenia leżą razem w tests/ — rdzeń liczy
# ścieżki względem korzenia beta/ (parents[1]), więc nie może leżeć poziom głębiej.
test:
	$(PYTHON) -m pytest tests -q

# Tylko warstwa usługi (kontrakt, transporty, CLI, SDK) — bez przejętego rdzenia.
test-service:
	$(PYTHON) -m pytest tests/test_contract.py tests/test_machine_service.py \
		tests/test_services.py tests/test_transport_rest.py tests/test_transport_ws.py \
		tests/test_cli_sdk.py tests/test_no_gui.py -q

# Rdzeń dynamiki Plant w C (C11, bez zależności).
test-c:
	@if [ -f plant_core/Makefile ]; then $(MAKE) -C plant_core test; \
	else echo "test-c: brak plant_core/Makefile - pomijam"; fi

serve:
	$(PYTHON) -m linumert_headless serve --backend fake --host 127.0.0.1 --port 8080 \
		--print-contract

# Kontrakt operacji dla GUI (codegen w dowolnym języku).
contract:
	$(PYTHON) -m linumert_headless contract --out api/contract.json

# Strażnik: w beta nie ma Qt, OpenGL ani panelu web.
check-no-gui:
	$(PYTHON) tools/check_no_gui.py

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info state
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
