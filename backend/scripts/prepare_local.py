"""Create local-only secrets once, without printing or replacing existing values."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env.local"
if target.exists():
    print("Existing .env.local preserved.")
else:
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        handle.write(
            f"DJANGO_SECRET_KEY={secrets.token_urlsafe(60)}\n"
            f"Y3GYM_DB_PASSWORD={secrets.token_urlsafe(32)}\n"
            "Y3GYM_DB_HOST=127.0.0.1\n"
            "Y3GYM_DB_PORT=55438\n"
            "Y3GYM_DB_NAME=y3gym_m1\n"
            "Y3GYM_DB_USER=y3gym_m1\n"
            "Y3GYM_PROTOTYPE_URL=http://localhost:8767\n"
        )
    print("Created .env.local with mode 0600. Values not printed.")
