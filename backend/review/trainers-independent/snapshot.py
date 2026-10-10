"""Read-only local preservation evidence; invoked through manage.py shell."""

import hashlib
import json
import os
import subprocess

from django.conf import settings
from django.db import connection, transaction

root = settings.PROTOTYPE_DIR.parent
output = root / "backend/review/trainers-independent"
label = os.environ["Y3GYM_INDEPENDENT_SNAPSHOT"]
assert label in {"before", "after"}
database = settings.DATABASES["default"]
assert database["HOST"] in {"127.0.0.1", "localhost"}
assert str(database["PORT"]) == "55438"
assert not connection.settings_dict["NAME"].startswith("test_")
paths = subprocess.check_output(
    ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    cwd=root,
    text=True,
).split("\0")
paths.extend(["backend/.env.local", "backend/.local-credentials"])
paths.extend(
    str(p.relative_to(root))
    for p in (root / "backend/.private-media").rglob("*")
    if p.is_file()
)
files = {
    p: hashlib.sha256((root / p).read_bytes()).hexdigest()
    for p in sorted(set(paths))
    if p
    and not p.startswith("backend/review/trainers-independent/")
    and (root / p).is_file()
}
db = {}
with transaction.atomic():
    with connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION READ ONLY")
        for name in sorted(connection.introspection.table_names()):
            cursor.execute(
                "SELECT row_to_json(t) FROM " + connection.ops.quote_name(name) + " t"
            )
            rows = cursor.fetchall()
            hashes = {
                str(row[0].get("id", index)): hashlib.sha256(
                    json.dumps(row[0], sort_keys=True, default=str).encode()
                ).hexdigest()
                for index, row in enumerate(rows)
            }
            db[name] = {"rows": len(rows), "hashes": hashes}
index = root / ".git/index"
result = {
    "root": str(root),
    "files": files,
    "index_sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
    "db": db,
}
target = output / f"snapshot-{label}.json"
with target.open("x") as handle:
    json.dump(result, handle, indent=2)
    handle.write("\n")
target.chmod(0o600)
print(
    json.dumps(
        {
            "snapshot": str(target),
            "file_count": len(files),
            "db_table_count": len(db),
            "database_read_only": True,
        }
    )
)
