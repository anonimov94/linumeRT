"""Exercise the distributable outside the checkout, with no source PYTHONPATH.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def main() -> None:
    wheel = Path(sys.argv[1]).resolve(strict=True)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        forbidden = ("linumert_webhmi/", "screens/", "linumert_plant/panel/")
        assert not any(name.startswith(forbidden) for name in names)
        assert any(name.endswith("templates/servo_400w.yaml") for name in names)
        assert "linumert/machine/resources/lrt_m6.ngc" in names
    with tempfile.TemporaryDirectory(prefix="linumert-lite-wheel-") as directory:
        work = Path(directory)
        site = work / "site"
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "--target",
                        str(site), str(wheel)], check=True, capture_output=True, text=True)
        code = '''
import json, os, pathlib, sys
sys.path.insert(0, sys.argv[1])
import linumert
assert pathlib.Path(linumert.__file__).is_relative_to(pathlib.Path(sys.argv[1]))
from linumert.cli import main, registry
from linumert.machine.drives.drive_library import load_library
from linumert.machine.schema import parse_machine
from linumert.machine.lite_config import render_lite
assert len(load_library()) >= 7
assert registry().get('pocket_rect', 1) and registry().get('pocket_rect', 2)
machine = json.loads(sys.argv[2])
files = render_lite(parse_machine(machine), 'sim')
assert 'macros/lrt_m6.ngc' in files and 'tool.tbl' in files
pathlib.Path('machine.yaml').write_text(json.dumps(machine))
from linumert_sim.machine import load_machine
assert load_machine('machine.yaml').axis_force['X'] > 0
pathlib.Path('part.lnx').write_text(json.dumps({'name': 'wheel', 'steps': [
    {'generator': 'drill_holes', 'version': 1, 'params': {'depth': 2}}]}))
assert main(['compile', 'part.lnx', '--out', 'part.ngc']) == 0
assert pathlib.Path('part.ngc').read_text().endswith('M2\\n')
pathlib.Path('cut.ngc').write_text('G21 G90\\nG0 X0 Y0 Z5\\nG1 X10 F600\\nM2\\n')
assert main(['simulate', 'cut.ngc', '--out', 'report.json']) == 0
assert json.loads(pathlib.Path('report.json').read_text())['segments'] > 0
from linumert_plant.__main__ import main as plant
assert plant(['drive', 'list']) == 0
if sys.argv[3]:
    os.environ['LINUMERT_PLANT_LIB'] = sys.argv[3]
    assert plant(['machine', 'build', 'machine.yaml', '--run']) == 0
print('Installed wheel: CAM, simulation, templates, config resources, Plant CLI PASS')
'''
        import yaml

        machine = Path(__file__).resolve().parents[1] / "config/machines/mill_servo_table.yaml"
        data = yaml.safe_load(machine.read_text(encoding="utf-8"))
        library = machine.parents[2] / "plant/core/build/libplant_core.so"
        native = str(library) if library.is_file() and sys.platform != "win32" else ""
        subprocess.run([sys.executable, "-I", "-c", code, str(site), json.dumps(data), native],
                       cwd=work, check=True)


if __name__ == "__main__":
    main()
