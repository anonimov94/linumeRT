# linumeRT lite — instructions

Backend only: no GUI, HTTP server, CAM 3D, ISO or new hardware support.
Read this file, `docs/ARCHITECTURE.md` and the README of the module being changed.
The current user request has priority. Do not resume the full edition roadmap.

- One task changes one module and its callers/tests. State the acceptance criterion first.
- `linumert.machine.drives` owns templates, mechanics and scales. Never import Plant in core.
- Plant and material simulation are independent consumers of core; neither imports the other.
- Keep LinuxCNC as the authoritative execution interpreter/planner. Subset parsing is diagnostic.
- Preserve `.lnx` generator versions, HAL signal contracts, units and safety behavior.
- No implicit E-STOP reset, motion enable or watchdog bypass. `--test-mode` is sim/Plant only.
- Run `python -m ruff check .` and affected pytest files. Before delivery run full `pytest`.
- Changes to Plant C require `make -C plant/core test` and Plant Python tests on Linux.
- Build/install the wheel outside the source tree when changing packaging or CLI resources.
- Retain copyright, provenance and GPL notices. Hardware remains unverified.
- No subagents unless explicitly requested. Never claim an independent review that did not happen.
- Never merge this lite branch into the full edition without an explicit user request.
