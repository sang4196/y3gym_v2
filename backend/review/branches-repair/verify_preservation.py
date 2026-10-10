"""Compare R1 work against the private pre-repair file/DB snapshots."""

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[3]
output = Path(__file__).resolve().parent
archive = Path(Path("/tmp/y3gym-m2-2-r1-current").read_text())
baseline = json.loads((archive / "files-before.json").read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


modified = [
    name for name, value in baseline["files"].items() if digest(root / name) != value
]
groups = {
    "prototype_including_design_and_prior_captures": [
        name for name in baseline["files"] if name.startswith("prototype/")
    ],
    "all_prior_backend_review_including_branches_and_independent": [
        name for name in baseline["files"] if name.startswith("backend/review/")
    ],
    "private_media": [name for name in baseline["files"] if "private-media/" in name],
    "secrets": ["backend/.env.local", "backend/.local-credentials"],
    "dependency_and_version_files": [
        "backend/uv.lock",
        "backend/pyproject.toml",
        "backend/.python-version",
        "prototype/package.json",
        "prototype/package-lock.json",
    ],
}
protected = {
    name: {
        "compared": len(files),
        "changedOrMissing": sum(file in modified for file in files),
    }
    for name, files in groups.items()
}
assert all(group["changedOrMissing"] == 0 for group in protected.values()), protected
index = (
    root
    / subprocess.check_output(
        ["git", "rev-parse", "--git-path", "index"], cwd=root, text=True
    ).strip()
)
assert digest(index) == baseline["index_sha256"]
before = json.loads((archive / "db-before.json").read_text())
after = json.loads((archive / "db-final.json").read_text())
tables = {}
for name in before.keys() | after.keys():
    old, new = before[name], after[name]
    tables[name] = {
        "before": old["rows"],
        "after": new["rows"],
        "changedOrMissingExistingRows": sum(
            new["hashes"].get(key) != value for key, value in old["hashes"].items()
        ),
    }
    assert old == new, name
new_source = [
    name
    for name in subprocess.check_output(
        ["rg", "--files"], cwd=root, text=True
    ).splitlines()
    if name not in baseline["files"]
    and not name.startswith("backend/review/branches-repair/")
]
report = {
    "checkedAt": datetime.now(timezone.utc).isoformat(),
    "status": "PASS",
    "baselineFiles": len(baseline["files"]),
    "protectedGroups": protected,
    "gitIndexUnchanged": True,
    "databaseTables": dict(sorted(tables.items())),
    "scope": "Existing file bytes and all captured DB rows/counts match. Raw source and row hashes remain only in a private /tmp archive.",
}
(output / "preservation.json").write_text(json.dumps(report, indent=2) + "\n")
(output / "changed-files.json").write_text(
    json.dumps(
        {
            "modifiedExisting": modified,
            "addedImplementation": sorted(new_source),
            "newEvidenceDirectory": "backend/review/branches-repair/",
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
)
print(
    f"PASS: {len(baseline['files'])} baseline files, {len(tables)} unchanged DB tables, Git index unchanged"
)
