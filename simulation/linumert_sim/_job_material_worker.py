"""One disposable low-priority job diagnostic process.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json
import os
import sys
from pathlib import Path

from linumert.programs.linuxcnc_check import limit_worker_lifetime


def main(argv):
    source, = argv
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    limit_worker_lifetime(str(data["timeout"]))
    os.nice(10)
    from .job_material import diagnose

    result = diagnose(data)
    result["worker_nice"] = os.getpriority(os.PRIO_PROCESS, 0)
    print(json.dumps(result, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(3) from None
