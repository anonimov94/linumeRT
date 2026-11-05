# Architecture of linumeRT lite

## Dependency direction

`linumert.machine.drives` owns drive templates, overrides, mechanics and scales.
`linumert.machine` validates machine.yaml and exports simulation configurations.
`linumert.generators` + `linumert.programs` compile versioned .lnx to G-code.
`linumert.tools` owns SQLite tools and tool.tbl import/export.
`linumert.cnc` reads LinuxCNC state and supplies a fake backend for tests.
`linumert_plant` consumes the machine model and simulates drives/I/O using C and UDP.
`linumert_sim` consumes programs and tools to estimate stock removal and collisions.
`linumert.cli` wires these modules together using lazy imports.

Core must never import Plant, material simulation, GUI or HTTP frameworks.
Plant and material simulation must not import each other.
Boundary tests in `tests/test_architecture.py` enforce these rules.

## Entry points

`linumert-lite`: compile, generators, machine, config, simulate.
`linumert-plant`: drive library, machine build, headless UDP serve.
`linumert-headless`: read-only LinuxCNC DISPLAY process for sim/Plant.
It never resets E-STOP, enables motion or emits a safety heartbeat.
Default configuration keeps HMI bypass disabled. An explicit `config --test-mode`
sets the existing test bypass only for generated sim/Plant configurations.
The hardware target is rejected. Virtual tool changes are not physical M6 approval.

## Where to work

| Task | Module | Focused tests |
|---|---|---|
| New cycle | core/linumert/generators | test_gen_*.py, test_lite_cli.py |
| Machine/drive changes | core/linumert/machine | test_machine_*.py, test_drive_*.py, test_lite_config.py |
| Plant dynamics | plant/core + plant/server | C tests, test_plant_*.py, test_scenario*.py |
| Material simulation | simulation/linumert_sim | test_sim_*.py |
| Tool database | core/linumert/tools | test_tools_db.py, test_tool_*.py |

Keep simulation and hardware claims separate. The subset G-code parser is diagnostic,
not a replacement execution interpreter. LinuxCNC/rs274 validates full G-code semantics.
Do not delete old generator versions: old .lnx files select them explicitly.

Full edition source and old decisions are recoverable at base commit
`a593d6d4c55f503fbaf4c607099f2d89c61cc670`; they are not startup reading for lite agents.
