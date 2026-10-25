"""Failure evidence for the Plant fixture. Model-Author: Codex; GPL-2.0-or-later."""

import threading

# Executed inside the standalone LinuxCNC driver, before any motion command.
DRIVER_DIAGNOSTICS = r'''
import atexit
from pathlib import Path
stage = "startup"

def snapshot(reason):
    data = {"reason": reason, "stage": stage, "monotonic": time.monotonic()}
    try:
        s.poll()
        while True:
            msg = e.poll()
            if not msg:
                break
            out["errors"].append(msg[1])
        data.update({name: getattr(s, name) for name in (
            "task_state", "task_mode", "interp_state", "current_vel",
            "position", "actual_position", "homed", "limit", "paused",
            "motion_line", "read_line", "exec_state")})
        data["joints"] = [{name: joint.get(name) for name in (
            "input", "output", "velocity", "ferror", "ferror_highmark",
            "homing", "homed", "enabled", "fault", "min_hard_limit", "max_hard_limit")}
            for joint in s.joint[:4]]
    except Exception as exc:
        data["snapshot_error"] = repr(exc)
    data["results"] = json.loads(json.dumps(out))
    return data

diagnostics_path = Path(sys.argv[0]).resolve().with_name("driver_diagnostics.json")

def save_diagnostics(path=diagnostics_path):
    data = snapshot("driver_exit")
    path.write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("DRIVER_DIAGNOSTICS " + json.dumps(data), flush=True)

atexit.register(save_diagnostics)
'''


def capture_console(proc, path):
    """Drain the merged LinuxCNC pipe while it runs, preserving output on failure."""
    def copy():
        with path.open("w", encoding="utf-8") as target:
            for line in proc.stdout:
                target.write(line)
                target.flush()

    thread = threading.Thread(target=copy, daemon=True)
    thread.start()
    return thread
