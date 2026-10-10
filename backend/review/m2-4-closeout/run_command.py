"""Record one command without replacing prior evidence or exposing credentials."""

import argparse
import datetime
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("name")
parser.add_argument("command", nargs=argparse.REMAINDER)
args = parser.parse_args()
output = Path(__file__).resolve().parent
command = args.command[1:] if args.command[:1] == ["--"] else args.command
record = {
    "command": command,
    "cwd": str(Path.cwd()),
    "started": datetime.datetime.now(datetime.UTC).isoformat(),
}
with (output / f"{args.name}.txt").open("x") as log:
    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
record.update(
    exit_code=result.returncode, ended=datetime.datetime.now(datetime.UTC).isoformat()
)
with (output / f"{args.name}-command.json").open("x") as handle:
    json.dump(record, handle, ensure_ascii=False, indent=2)
print(json.dumps(record, ensure_ascii=False))
print((output / f"{args.name}.txt").read_text()[-3500:])
raise SystemExit(result.returncode)
