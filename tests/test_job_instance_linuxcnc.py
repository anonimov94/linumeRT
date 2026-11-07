"""Boot a frozen job on actual Plant + WebHMI HAL without enabling it.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex. Contract report fixture is constructed, not an interpreter proof.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import rip_support as rip
from test_job_instance import configuration as configuration
from test_job_instance import package as package

pytestmark = pytest.mark.linuxcnc


def test_private_instance_boots_estop_and_stops_only_its_processes(configuration, tmp_path):
    root = rip.rip_root()
    if rip.leftovers():
        pytest.skip("another LinuxCNC process is active")
    work = tmp_path / "instance"
    env = {**os.environ, "PATH": f"{Path(sys.executable).parent}:{os.environ['PATH']}"}
    with rip.installed_modules(root, tmp_path, ("lrt_net", "lrt_cia402", "lrt_estop2")):
        with (tmp_path / "host.log").open("w") as log:
            host = subprocess.Popen([sys.executable, "-m", "linumert_webhmi.job_instance",
                                     str(configuration), "--out", str(work), "--port", "8793",
                                     "--token=--instance-live-test-token-123"],
                                    env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    assert host.poll() is None, (tmp_path / "host.log").read_text()
                    try:
                        record = json.loads((work / "instance.json").read_text())
                        req = urllib.request.Request("http://127.0.0.1:8793/api/state",
                            headers={"X-Linumert-Token": record["token"]})
                        with urllib.request.urlopen(req, timeout=1) as response:
                            state = json.load(response)["state"]
                        break
                    except (OSError, ValueError):
                        time.sleep(.1)
                else:
                    pytest.fail((tmp_path / "host.log").read_text())
                assert state["task_state"] == "estop" and not state["all_homed"], state
                assert state["hmi_hal"] and not state["execution"]["can_start"]
                assert state["execution"]["job_id"] == record["job_id"]
                req = urllib.request.Request("http://127.0.0.1:8793/api/command", method="POST",
                    data=b'{"cmd":"run"}', headers={"X-Linumert-Token": record["token"],
                                                   "Content-Type": "application/json"})
                with pytest.raises(urllib.error.HTTPError) as refused:
                    urllib.request.urlopen(req, timeout=2)
                assert refused.value.code == 409
                assert (work / "evidence/linumert.var").read_bytes() == (
                    configuration / "linumert.var").read_bytes()
            finally:
                host.terminate()
                host.wait(timeout=45)
        assert not rip.leftovers(), rip.leftovers()
