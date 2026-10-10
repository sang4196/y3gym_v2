"""Record one local command without overwriting prior evidence."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

output = Path(__file__).resolve().parent
name, *command = sys.argv[1:]
assert name.replace("-", "").isalnum()
assert not (output / f"{name}-command.json").exists(), "Use a new command output name"
started = time.monotonic()
print(f"Starting {name}", flush=True)
with (output / f"{name}.txt").open("x") as log:
    result = subprocess.run(
        command, cwd=output.parents[1], stdout=log, stderr=subprocess.STDOUT
    )
record = {
    "command": command,
    "cwd": str(output.parents[1]),
    "environment_overrides": {
        k: v
        for k, v in os.environ.items()
        if k
        in {
            "Y3GYM_RUN_BRANCH_BROWSER",
            "Y3GYM_RUN_BRAND_BROWSER",
            "Y3GYM_BRANCH_REVIEW_DIR",
            "Y3GYM_BRAND_REVIEW_DIR",
            "Y3GYM_POPUP_REVIEW_DIR",
        }
    },
    "exit_code": result.returncode,
    "elapsed_seconds": round(time.monotonic() - started, 3),
}
with (output / f"{name}-command.json").open("x") as handle:
    json.dump(record, handle, indent=2)
    handle.write("\n")
print(json.dumps(record), flush=True)
print((output / f"{name}.txt").read_text()[-6000:])
raise SystemExit(result.returncode)
