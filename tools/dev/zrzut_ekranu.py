#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Zrzut ekranu linumeRT pod Xvfb (w obrazie z tools/dev/linuxcnc-gui.sh).

Model-Author: Claude · sesja 005.
Użycie (z katalogu repo):
  tools/dev/linuxcnc-gui.sh python3 tools/dev/zrzut_ekranu.py <plik.ini> <wynik.png> [sekundy]
Uruchamia Xvfb :99 (1920x1080), LinuxCNC z podanym INI, czeka i zapisuje cały ekran wirtualny.
"""

import glob
import os
import subprocess
import sys
import time


def main() -> int:
    ini, out = sys.argv[1], sys.argv[2]
    wait = float(sys.argv[3]) if len(sys.argv) > 3 else 25.0
    env = {**os.environ, "DISPLAY": ":99"}
    env.pop("XAUTHORITY", None)
    xvfb = subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1920x1080x24", "-nolisten", "tcp"])
    time.sleep(2)
    cnc = subprocess.Popen(["linuxcnc", ini], env=env, stdout=subprocess.DEVNULL,
                           stderr=subprocess.STDOUT)
    try:
        time.sleep(wait)
        failed = subprocess.run(["pgrep", "-f", "[s]how_errors.tcl"],
                                capture_output=True).returncode == 0
        if failed:
            for log in glob.glob("/tmp/linuxcnc.debug.*") + glob.glob("/tmp/linuxcnc.print.*"):
                with open(log, encoding="utf-8", errors="replace") as f:
                    print(f"--- {log}\n" + "".join(f.readlines()[-25:]), file=sys.stderr)
            return 1
        if cnc.poll() is not None:
            print(f"LinuxCNC zakończył się przed zrzutem (kod {cnc.returncode})", file=sys.stderr)
            return 1
        grab = ("import sys\nfrom PyQt5.QtWidgets import QApplication\n"
                "app = QApplication([])\n"
                "ok = app.primaryScreen().grabWindow(0).save(sys.argv[1], 'png')\n"
                "sys.exit(0 if ok else 1)\n")
        return subprocess.run([sys.executable, "-c", grab, out], env=env).returncode
    finally:
        cnc.terminate()
        try:
            cnc.wait(timeout=40)
        except subprocess.TimeoutExpired:
            cnc.kill()
        xvfb.terminate()


if __name__ == "__main__":
    sys.exit(main())
