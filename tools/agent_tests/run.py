"""Run checks with live output and retain a report. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import argparse
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def git_value(repo, *args):
    try:
        result = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except OSError:
        return None


def run_checks(repo, model, output, commands):
    """Run every check, including after a failure; never turn missing tools green."""
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "model": model,
        "started_at": datetime.now(UTC).isoformat(),
        "commit": git_value(repo, "rev-parse", "HEAD"),
        "working_tree_status": git_value(repo, "status", "--porcelain"),
        "platform": platform.platform(),
        "python": sys.version,
        "checks": [],
    }
    for name, command in commands:
        print(f"\n=== {name} ===", flush=True)
        log_path = output / f"{name}.log"
        with log_path.open("w", encoding="utf-8") as log:
            try:
                with subprocess.Popen(
                    command, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                ) as process:
                    for line in process.stdout:
                        log.write(line)
                        log.flush()
                        print(line, end="", flush=True)
                    code = process.wait()
            except OSError as error:
                code = 127
                log.write(f"{error}\n")
                print(error, flush=True)
        report["checks"].append({
            "name": name, "command": command, "exit_code": code, "log": log_path.name,
        })
        # Save after every check so completed results survive later interruption.
        (output / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    report["passed"] = bool(commands) and all(c["exit_code"] == 0 for c in report["checks"])
    report["finished_at"] = datetime.now(UTC).isoformat()
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n{'PASS' if report['passed'] else 'FAIL'} — {output / 'report.json'}", flush=True)
    return 0 if report["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["Codex", "Claude", "Manual"], required=True)
    parser.add_argument("--linuxcnc", action="store_true", help="Also run RIP sim and QtDragon")
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    output = REPO / "state" / "test-runs" / f"{stamp}-{args.model}"
    commands = [
        ("diff", ["git", "diff", "--check"]),
        ("lint", [sys.executable, "-m", "ruff", "check", "."]),
        ("pytest", [sys.executable, "-m", "pytest", "-v"]),
    ]
    if args.linuxcnc:
        commands.append(("linuxcnc", ["make", "test-linuxcnc", f"PYTHON={sys.executable}"]))
    return run_checks(REPO, args.model, output, commands)


if __name__ == "__main__":
    raise SystemExit(main())
