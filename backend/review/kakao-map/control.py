"""Operate only the identified map review server. Never scan/kill other servers."""

import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

scratch = Path(sys.argv[1]).resolve()
assert scratch.parent == Path("/tmp") and scratch.name.startswith("y3gym-kakao-map-")
spec = json.loads((scratch / "instance.json").read_text())
assert spec["database"].startswith("test_y3gym_kakao_map_")
assert spec["port"] in {8769, 8770}
backend = Path(__file__).resolve().parents[2]
action = sys.argv[2]
pid_path = scratch / "server.pid"


def identified_process():
    pid = int(pid_path.read_text())
    proc = Path(f"/proc/{pid}")
    if not proc.exists():
        return None
    command = (proc / "cmdline").read_bytes().split(b"\0")
    assert b"manage.py" in command
    assert f"127.0.0.1:{spec['port']}".encode() in command
    assert (proc / "cwd").resolve() == backend
    environment = (proc / "environ").read_bytes().split(b"\0")
    assert b"DJANGO_SETTINGS_MODULE=map_review_settings" in environment
    assert any(
        str(scratch).encode() in value
        for value in environment
        if value.startswith(b"PYTHONPATH=")
    )
    return pid


if action == "status":
    print(
        json.dumps(
            {
                "pid": identified_process(),
                "origin": spec["origin"],
                "database": spec["database"],
            }
        )
    )
elif action == "stop":
    pid = identified_process()
    if pid:
        os.kill(pid, signal.SIGTERM)
        for _ in range(50):
            if not Path(f"/proc/{pid}").exists():
                break
            time.sleep(0.1)
    print("Identified map review server stopped; no other process was signalled")
elif action == "start":
    assert identified_process() is None, "Identified review server is already running"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", spec["port"]))
    environment = os.environ.copy()
    environment.update(
        DJANGO_SETTINGS_MODULE="map_review_settings",
        PYTHONPATH=os.pathsep.join([str(scratch), str(backend)]),
        Y3GYM_KAKAO_MAP_JS_KEY="",
    )
    if "--real-sdk-confirmed" in sys.argv[3:]:
        key_path = scratch / "kakao-map-js-key"
        assert not key_path.is_symlink() and key_path.stat().st_mode & 0o777 == 0o600
        key = key_path.read_text().strip()
        assert re.fullmatch(r"[0-9a-fA-F]{32}", key), (
            "Check JavaScript key file privately"
        )
        environment["Y3GYM_KAKAO_MAP_JS_KEY"] = key
    with (scratch / "server.log").open("ab") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "manage.py",
                "runserver",
                f"127.0.0.1:{spec['port']}",
                "--noreload",
                "--insecure",
            ],
            cwd=backend,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    pid_path.write_text(str(process.pid))
    print(
        json.dumps(
            {"pid": process.pid, "origin": spec["origin"], "key_value_logged": False}
        )
    )
else:
    raise ValueError("Use status, stop or start")
