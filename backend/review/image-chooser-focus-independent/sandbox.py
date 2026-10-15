"""Operate only the fresh 8770 image-chooser sandbox; never reuse review DBs."""

import copy
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
work = Path(sys.argv[1]).resolve()
assert work.parent == Path("/tmp") and work.name.startswith("y3gym-image-focus-independent-")
action = sys.argv[2]

if action == "configure":
    assert not (work / "instance.json").exists()
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", 8770))
    sys.path.insert(0, str(BACKEND))
    from config import settings as original

    suffix = secrets.token_hex(6)
    database = "test_y3gym_focus_ind_" + suffix
    config = copy.deepcopy(original.DATABASES["default"])
    args = {k.lower(): config[k] for k in ["USER", "PASSWORD", "HOST", "PORT"]}
    with psycopg.connect(dbname="postgres", **args, autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname IN (%s,%s)",
                [database, database + "_runner"],
            )
            assert not cursor.fetchall()
            cursor.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(
                    sql.Identifier(database)
                )
            )
    spec = {
        "scratch": str(work),
        "database": database,
        "test_database": database + "_runner",
        "origin": "http://localhost:8770",
        "port": 8770,
        "media": str(work / "media"),
        "initialized": False,
    }
    (work / "instance.json").write_text(json.dumps(spec, indent=2))
    (work / "image_focus_ind_settings.py").write_text(f"""from config.settings import *
import copy
from pathlib import Path
DATABASES = copy.deepcopy(DATABASES)
DATABASES["default"]["NAME"] = {database!r}
DATABASES["default"]["TEST"] = {{"NAME": {database + "_runner"!r}}}
BASE_DIR = Path({str(work)!r})
MEDIA_ROOT = BASE_DIR / "media"
WAGTAILADMIN_BASE_URL = "http://localhost:8770"
SESSION_COOKIE_NAME = "image_focus_ind_{suffix}_session"
CSRF_COOKIE_NAME = "image_focus_ind_{suffix}_csrf"
KAKAO_MAP_JS_KEY = ""
""")
    print(json.dumps(spec))
    sys.exit()

spec = json.loads((work / "instance.json").read_text())
assert spec["port"] == 8770 and spec["origin"] == "http://localhost:8770"
assert spec["database"].startswith("test_y3gym_focus_ind_")
environment = os.environ.copy()
environment.update(
    DJANGO_SETTINGS_MODULE="image_focus_ind_settings",
    PYTHONPATH=os.pathsep.join([str(work), str(BACKEND)]),
    Y3GYM_KAKAO_MAP_JS_KEY="",
    PYTHONDONTWRITEBYTECODE="1",
)
pid_path = work / "server.pid"

if action == "initialize":
    assert not spec["initialized"], "No reseed permitted"
    os.environ.update(environment)
    sys.path[:0] = [str(work), str(BACKEND)]
    import django

    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection

    from news.tests.review_fixtures import bootstrap_browser_review

    assert settings.DATABASES["default"]["NAME"] == spec["database"]
    assert settings.MEDIA_ROOT == work / "media" and not settings.KAKAO_MAP_JS_KEY
    assert not connection.introspection.table_names(), "Only initialize an empty new DB"
    call_command("migrate", interactive=False, verbosity=0)
    bootstrap_browser_review()
    from django.contrib.auth import get_user_model

    credentials = json.loads((work / ".local-credentials").read_text())
    username = "focus-review-" + spec["database"][-6:]
    user = get_user_model().objects.get(username="cms-review-editor")
    user.username = username
    user.save(update_fields=["username"])
    (work / ".local-credentials").write_text(
        json.dumps({username: credentials["cms-review-editor"]})
    )
    (work / ".local-credentials").chmod(0o600)
    spec["username"] = username
    from PIL import Image, ImageDraw

    fixture = Image.new("RGB", (640, 480), "#466b78")
    ImageDraw.Draw(fixture).rectangle((50, 50, 220, 330), fill="#e4af66")
    fixture.save(work / "fixture.png")
    (work / "fixture.png").chmod(0o600)
    spec["initialized"] = True
    (work / "instance.json").write_text(json.dumps(spec, indent=2))
    print("Fresh isolated database migrated and TEST fixtures initialized")
elif action == "start":
    assert spec["initialized"]
    if pid_path.exists():
        assert not Path(f"/proc/{int(pid_path.read_text())}").exists()
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", 8770))
    with (work / "server.log").open("ab") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "manage.py",
                "runserver",
                "127.0.0.1:8770",
                "--noreload",
                "--insecure",
            ],
            cwd=BACKEND,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    pid_path.write_text(str(process.pid))
    for _ in range(60):
        assert process.poll() is None
        try:
            with socket.create_connection(("127.0.0.1", 8770), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Own server did not start")
    print(
        json.dumps(
            {"pid": process.pid, "origin": spec["origin"], "real_sdk_enabled": False}
        )
    )
elif action == "stop":
    pid = int(pid_path.read_text())
    proc = Path(f"/proc/{pid}")
    assert (proc / "cwd").resolve() == BACKEND
    command = (proc / "cmdline").read_bytes().split(b"\0")
    assert b"manage.py" in command and b"127.0.0.1:8770" in command
    env = (proc / "environ").read_bytes().split(b"\0")
    assert b"DJANGO_SETTINGS_MODULE=image_focus_ind_settings" in env
    assert any(str(work).encode() in v for v in env if v.startswith(b"PYTHONPATH="))
    assert b"Y3GYM_KAKAO_MAP_JS_KEY=" in env
    assert repr(spec["database"]) in (work / "image_focus_ind_settings.py").read_text()
    assert spec["media"] == str(work / "media")
    os.kill(pid, signal.SIGTERM)
    for _ in range(50):
        if not proc.exists():
            break
        time.sleep(0.1)
    assert not proc.exists()
    print("Only identified 8770 process stopped")
else:
    raise ValueError("configure, initialize, start or stop")
