PYTHON ?= python3

.PHONY: install lint test test-core test-c plant-matrix wheel-check
install:
	$(PYTHON) -m pip install -c requirements-dev.lock -e ".[dev]"
lint:
	$(PYTHON) -m ruff check .
test:
	$(PYTHON) -m pytest -q
test-core:
	$(PYTHON) -m pytest -q -m "not linuxcnc and not plant" tests/test_architecture.py tests/test_lite_cli.py tests/test_lite_config.py tests/test_lnx.py tests/test_machine_config.py tests/test_tools_db.py tests/test_gen_basic.py tests/test_gen_drilling.py tests/test_gen_pockets.py tests/test_gen_contours.py
test-c:
	$(MAKE) -C plant/core test
plant-matrix:
	$(MAKE) -C plant/core shared
	$(PYTHON) tools/run_scenario.py --matrix --no-report
wheel-check:
	$(PYTHON) -m build --wheel
	$(PYTHON) tools/check_wheel.py dist/linumert_lite-0.1.0-py3-none-any.whl
