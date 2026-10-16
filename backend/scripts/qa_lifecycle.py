"""Owned QA runs. Legacy inventory is observational and never adopts resources."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import hmac
import json
import os
import re
import select
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

PROJECT = Path(__file__).resolve().parents[2]
BACKEND = PROJECT / "backend"
RUNS = PROJECT / ".local" / "qa"
PYTHON = BACKEND / ".venv/bin/python"


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return digest(Path(path).read_bytes())


def proc_info(pid, strict=False):
    """Selected process facts only; never return complete argv/environment."""
    try:
        p = Path("/proc") / str(pid)
        text = (p / "stat").read_text()
        tail = text[text.rfind(")") + 2 :].split()
        if tail[0] == "Z":
            return None
        args = (p / "cmdline").read_bytes().split(b"\0")
        env = dict(
            v.split(b"=", 1)
            for v in (p / "environ").read_bytes().split(b"\0")
            if b"=" in v
        )
        return {
            "pid": int(pid),
            "start_ticks": int(tail[19]),
            "cwd": str((p / "cwd").resolve(strict=True)),
            "exe": str((p / "exe").resolve(strict=True)),
            "argv_sha256": digest(b"\0".join(args)),
            "uid": p.stat().st_uid,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "settings": env.get(b"DJANGO_SETTINGS_MODULE", b"").decode(
                errors="replace"
            ),
            "pythonpath": env.get(b"PYTHONPATH", b"")
            .decode(errors="replace")
            .split(":"),
            "run_id": env.get(b"Y3GYM_QA_RUN_ID", b"").decode(errors="replace"),
            "run_token": env.get(b"Y3GYM_QA_RUN_TOKEN", b"").decode(errors="replace"),
            "port_args": [
                int(m[1])
                for a in args
                if (m := re.fullmatch(rb"(?:127\.0\.0\.1|localhost):(\d+)", a))
            ],
        }
    except (OSError, ValueError, ProcessLookupError):
        try:
            state = (Path("/proc") / str(pid) / "stat").read_text()
            tail = state[state.rfind(")") + 2 :].split()
            if tail[0] == "Z":
                return None
        except FileNotFoundError:
            if strict and (Path("/proc") / str(pid)).exists():
                raise Refused("Recorded PID still exists; stat unavailable")
            return None
        except OSError:
            pass
        if strict and (Path("/proc") / str(pid)).exists():
            raise Refused("Recorded PID exists but identity lookup failed; preserve")
        return None


def size_info(path):
    allocated = logical = count = errors = 0
    if path.is_symlink():
        return {
            "allocated_bytes": 0,
            "logical_bytes": 0,
            "files": 0,
            "errors": 0,
            "symlink_not_followed": True,
        }
    todo = [path]
    while todo:
        p = todo.pop()
        try:
            s = p.lstat()
            allocated += s.st_blocks * 512
            logical += s.st_size
            if stat.S_ISREG(s.st_mode):
                count += 1
            elif stat.S_ISDIR(s.st_mode):
                todo.extend(p.iterdir())
        except OSError:
            errors += 1
    return {
        "allocated_bytes": allocated,
        "logical_bytes": logical,
        "files": count,
        "errors": errors,
    }


def inventory():
    refs = {}
    for base in [BACKEND / "review", PROJECT / "docs"]:
        for p in base.rglob("*"):
            if (
                p.is_file()
                and p.suffix in {".md", ".json", ".py", ".mjs", ".sh"}
                and "qa-lifecycle" not in str(p)
            ):
                try:
                    text = p.read_text()
                except (OSError, UnicodeError):
                    continue
                for candidate in set(re.findall(r"/tmp/(y3gym-[A-Za-z0-9_-]+)", text)):
                    refs.setdefault("/tmp/" + candidate, []).append(
                        str(p.relative_to(PROJECT))
                    )
    processes = [
        v
        for p in Path("/proc").iterdir()
        if p.name.isdigit() and (v := proc_info(p.name))
    ]
    listeners = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True).stdout
    for process in processes:
        ports = set(process["port_args"])
        for line in listeners.splitlines()[1:]:
            if f"pid={process['pid']}," in line:
                try:
                    ports.add(int(line.split()[3].rsplit(":", 1)[1]))
                except (ValueError, IndexError):
                    pass
        process["port_args"] = sorted(ports)
    entries = []
    tmp_dirs = [p for p in Path("/tmp").iterdir() if p.is_dir() or p.is_symlink()]
    paths = sorted(p for p in tmp_dirs if p.name.startswith("y3gym-"))
    paths += [
        PROJECT / ".local",
        BACKEND / ".private-media",
        BACKEND / ".env.local",
        BACKEND / ".local-credentials",
        BACKEND / ".venv",
        BACKEND / ".static",
        PROJECT / "prototype/node_modules",
    ]
    for path in paths:
        if not path.exists() and not path.is_symlink():
            entries.append(
                {
                    "path": str(path),
                    "states": ["불명"],
                    "exists": False,
                    "purpose": "not present at initial inventory",
                    "cleanup_allowed": False,
                }
            )
            continue
        spec = {}
        if path.is_dir() and not path.is_symlink():
            candidate = path / "instance.json"
            try:
                if candidate.is_file() and not candidate.is_symlink():
                    raw = json.loads(candidate.read_text())
                    spec = {
                        k: raw[k]
                        for k in ["scratch", "port", "database", "media", "initialized"]
                        if k in raw
                    }
            except (OSError, ValueError):
                pass
        matches = [
            p
            for p in processes
            if p["cwd"] == str(path)
            or p["cwd"].startswith(str(path) + "/")
            or str(path) in p["pythonpath"]
        ]
        related = refs.get(str(path), [])
        attributed = any(
            p["cwd"] == str(BACKEND) and str(path) in p["pythonpath"] for p in matches
        )
        proof = []
        if attributed:
            proof.append(
                "actual process cwd=project/backend and PYTHONPATH contains this exact directory"
            )
        if related:
            proof.append(
                "exact path referenced by repository QA/documents; historical temporary dependency"
            )
        if spec.get("scratch") == str(path):
            proof.append(
                "instance scratch matches exact path; attribution alone is insufficient ownership"
            )
        if path.is_relative_to(PROJECT):
            proof.append("existing project runtime/original; explicitly protected")
        states = []
        if matches:
            states.append("실행중")
        failure_refs = []
        dependencies = []
        for ref in related:
            doc = PROJECT / ref
            try:
                text = doc.read_text()
                if doc.name == "failures.json" or (
                    doc.suffix == ".json"
                    and re.search(r"\"status\"\s*:\s*\"FAIL", text)
                ):
                    failure_refs.append(ref)
                if doc.suffix in {".py", ".mjs", ".sh"} or any(
                    str(path) in line
                    and re.search(r"python|node |bash |guard|shell", line, re.I)
                    for line in text.splitlines()
                ):
                    dependencies.append(ref)
            except OSError:
                pass
        direct_failure = []
        for ref in failure_refs:
            try:
                data = json.loads((PROJECT / ref).read_text())
                if (
                    isinstance(data, dict)
                    and any(
                        data.get(k) == str(path)
                        for k in ["work", "private_work", "scratch", "run_dir"]
                    )
                    and str(data.get("status", "")).startswith("FAIL")
                ):
                    direct_failure.append(ref)
            except (ValueError, OSError):
                pass
        if direct_failure:
            states.append("실패재현보존")
        completed = []
        if (attributed or related) and not matches and path.is_dir():
            for exitfile in path.glob("*.exit"):
                try:
                    if (
                        exitfile.stat().st_size < 16
                        and exitfile.read_text().strip() == "0"
                    ):
                        completed.append(exitfile.name)
                except OSError:
                    pass
        if completed and related and not dependencies and not failure_refs:
            states.append("정리후보")
        if any(p["port_args"] and 8776 in p["port_args"] for p in matches):
            states.append("사용자검수대기")
            proof.append(
                "explicit keep-user-environment instruction; NAV01 limited user confirmation now complete, other review scope not blanket-approved"
            )
        if not attributed and not path.is_relative_to(PROJECT) and not related:
            states.append("불명")
        if not states:
            states = ["불명"]
        entries.append(
            {
                "path": str(path),
                "exists": True,
                "states": states,
                "purpose": "project legacy QA/runtime"
                if attributed or related
                else "original/dependency runtime"
                if path.is_relative_to(PROJECT)
                else "name-only unconfirmed candidate; not traversed",
                **(
                    size_info(path)
                    if attributed or related or path.is_relative_to(PROJECT)
                    else {
                        "allocated_bytes": None,
                        "size_not_scanned": "name alone is not project attribution",
                    }
                ),
                "processes": [
                    {
                        "pid": p["pid"],
                        "start_ticks": p["start_ticks"],
                        "cwd": p["cwd"],
                        "exe": p["exe"],
                        "settings": p["settings"],
                        "ports": p["port_args"],
                        "identity_evidence": "observed cwd/PYTHONPATH, not filename/mtime ownership",
                    }
                    for p in matches
                ],
                "instance_selected_fields": spec,
                "preservation_reasons": proof
                or ["unknown ownership/lifecycle; preserve"],
                "temporary_QA_references": related[:12],
                "reference_count": len(related),
                "failure_preservation_evidence": direct_failure,
                "failure_document_references_relationship_unconfirmed": failure_refs,
                "possible_executable_tmp_dependencies": dependencies,
                "completed_exit_evidence": completed,
                "completion_evidence_scope": "only the named exit files; environment-wide completion is unverified",
                "candidate_additional_conditions": [
                    "verify complete environment outcome, unused resources and all temporary-code dependencies",
                    "separate deletion authorization; legacy remains outside this tool",
                ],
                "cleanup_allowed": False,
                "cleanup_candidate_reason": "conditional proposal only: some recorded exit0 and no observed process; overall completion/dependencies require confirmation"
                if "정리후보" in states
                else "insufficient lifecycle evidence or retained dependency; no cleanup authorization",
            }
        )
    # Include project-attributed static/server processes even outside /tmp candidates.
    project_processes = [
        {
            "pid": p["pid"],
            "start_ticks": p["start_ticks"],
            "cwd": p["cwd"],
            "exe": p["exe"],
            "settings": p["settings"],
            "ports": p["port_args"],
        }
        for p in processes
        if p["cwd"] == str(PROJECT)
        or p["cwd"].startswith(str(PROJECT) + "/")
        or str(BACKEND) in p["pythonpath"]
    ]
    return {
        "schema": 1,
        "observed_at": now(),
        "mode": "read-only, no adoption/stop/delete/DB modification",
        "project": str(PROJECT),
        "name_matching_tmp_candidates_not_ownership": sum(
            1
            for p in paths
            if p.parent == Path("/tmp")
            and p.name.startswith("y3gym-")
            and not p.is_symlink()
        ),
        "state_labels": [
            "실행중",
            "사용자검수대기",
            "실패재현보존",
            "정리후보",
            "불명",
        ],
        "entries": entries,
        "project_attributed_processes": project_processes,
        "DB_service_observation": {
            "port": 55438,
            "listening_observed": ":55438 " in listeners,
            "role": "existing local PostgreSQL service; not lifecycle-managed",
        },
        "foreign_or_system_tmp_directories_not_traversed": len(tmp_dirs)
        - sum(p.name.startswith("y3gym-") for p in tmp_dirs),
        "root_local_initially_present": (PROJECT / ".local").exists(),
        "legacy_cleanup_candidates_authorized": 0,
    }


def write_inventory(output):
    report = inventory()
    output = Path(output)
    if output.exists():
        raise ValueError("Inventory output exists; choose a new evidence path")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# QA 실행 환경 초기 읽기 전용 인벤토리",
        "",
        "이름 일치 후보는 소유확정이 아니다. 기존 환경은 이번 도구의 cleanup 대상에 편입하지 않는다. 크기는 lstat 기반 대략 allocated 크기이며 symlink를 따라가지 않는다. 원본/다른 프로젝트/불명 경로를 보존한다.",
        "",
        "| 경로 | 용도 | 상태 | 대략 MiB | 실제 PID/포트 | 보존 근거 |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for v in report["entries"]:
        ps = (
            ", ".join(
                f"{p['pid']}/" + ",".join(map(str, p["ports"]))
                for p in v.get("processes", [])
            )
            or "없음/미확인"
        )
        lines.append(
            f"| `{v['path']}` | {v['purpose']} | {'·'.join(v['states'])} | {(v.get('allocated_bytes') or 0) / 1048576:.2f} | {ps} | {'; '.join(v.get('preservation_reasons', ['initially absent']))} |"
        )
    output.with_suffix(".md").write_text("\n".join(lines) + "\n")
    return {
        "inventory": str(output),
        "tmp_name_candidates": report["name_matching_tmp_candidates_not_ownership"],
        "entries": len(report["entries"]),
        "project_processes": len(report["project_attributed_processes"]),
        "authorized_legacy_cleanup": 0,
    }


class Refused(RuntimeError):
    pass


ID = re.compile(r"qa-\d{8}T\d{6}Z-[a-f0-9]{12}")
SCHEMA = "y3gym.qa.v1"


def require(value, message):
    if not value:
        raise Refused(message)


def private_json(path, value):
    if path.exists() or path.is_symlink():
        secure_file(path)
    temp = path.parent / (".write-" + uuid.uuid4().hex)
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    os.replace(temp, path)


def secure_file(path):
    v = path.lstat()
    require(
        stat.S_ISREG(v.st_mode) and v.st_uid == os.getuid() and v.st_nlink == 1,
        "Control file identity is not a private regular owned file",
    )
    require(not v.st_mode & 0o077, "Control file must have mode0600")


def private_read(path):
    secure_file(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        return json.load(stream)


def layout(create=False):
    require(
        PROJECT.is_dir() and (PROJECT / ".git").exists(),
        "Canonical project checkout required",
    )
    for path in [PROJECT / ".local", RUNS, RUNS / ".registry"]:
        require(not path.is_symlink(), "Managed root cannot contain symlinks")
        if not path.exists():
            if not create:
                return False
            path.mkdir(mode=0o700)
        v = path.lstat()
        require(
            stat.S_ISDIR(v.st_mode)
            and v.st_uid == os.getuid()
            and not v.st_mode & 0o077,
            "Managed root requires owned mode0700 directories",
        )
    marker = RUNS / ".registry/root.json"
    identity = [RUNS.stat().st_dev, RUNS.stat().st_ino]
    if not marker.exists():
        require(
            create and not list(RUNS.glob("qa-*")),
            "Unmarked root cannot adopt existing runs",
        )
        private_json(
            marker, {"schema": SCHEMA, "project": str(PROJECT), "inode": identity}
        )
    value = private_read(marker)
    require(
        value == {"schema": SCHEMA, "project": str(PROJECT), "inode": identity},
        "Managed root identity changed",
    )
    return True


@contextlib.contextmanager
def lock(create=False):
    require(layout(create), "Managed root not present")
    path = RUNS / ".registry/lock"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def registry_path(run_id):
    require(
        bool(ID.fullmatch(run_id)),
        "Use one exact run-id, never a root or external path",
    )
    return RUNS / ".registry" / f"{run_id}.json"


def save(run, value):
    private_json(run / "manifest.json", value)
    entry = {**value, "manifest_sha256": file_sha(run / "manifest.json")}
    private_json(registry_path(value["id"]), entry)


def load(run_id):
    require(layout(), "Managed root absent")
    entry = private_read(registry_path(run_id))
    run = RUNS / run_id
    require(
        entry["schema"] == SCHEMA
        and entry["path"] == str(run)
        and entry["id"] == run_id,
        "Registry ownership/path mismatch",
    )
    if entry["state"] == "DELETED":
        require(
            not run.exists() and not run.is_symlink(),
            "Tombstoned path was recreated; preserve it",
        )
        return run, entry, None
    require(
        not run.is_symlink() and run.resolve(strict=True) == run and run.parent == RUNS,
        "Run path escapes managed root",
    )
    v = run.lstat()
    require(
        stat.S_ISDIR(v.st_mode) and v.st_uid == os.getuid() and not v.st_mode & 0o077,
        "Run owner/mode changed",
    )
    require([v.st_dev, v.st_ino] == entry["inode"], "Run directory identity changed")
    marker = private_read(run / "owner.json")
    require(
        marker["schema"] == SCHEMA
        and marker["id"] == run_id
        and digest(marker["token"].encode()) == entry["owner_hash"],
        "Ownership marker does not match registry",
    )
    secure_file(run / "manifest.json")
    require(
        file_sha(run / "manifest.json") == entry["manifest_sha256"],
        "Manifest changed outside lifecycle CLI",
    )
    value = private_read(run / "manifest.json")
    expected = "test_y3gym_qa_" + run_id[-12:] + "_" + entry["owner_hash"][:12]
    require(
        value["database_names"] == [expected, expected + "_runner"],
        "External database name refused",
    )
    return run, value, marker["token"]


def copy_source(run):
    target = run / "source"
    target.mkdir(mode=0o700)
    manifest = {}
    folders = [
        BACKEND / "config",
        BACKEND / "news",
        BACKEND / "scripts",
        PROJECT / "prototype",
        PROJECT / "deploy",
    ]
    files = [
        BACKEND / "manage.py",
        BACKEND / "pyproject.toml",
        BACKEND / "uv.lock",
        PROJECT / "Dockerfile",
        PROJECT / ".dockerignore",
        PROJECT / "compose.production.yaml",
    ]
    for folder in folders:
        for base, dirs, names in os.walk(folder):
            dirs[:] = [
                n
                for n in dirs
                if n
                not in {
                    ".git",
                    ".local",
                    ".venv",
                    "node_modules",
                    "__pycache__",
                    "review",
                    ".ruff_cache",
                    ".private-media",
                    ".static",
                }
                and not (Path(base) / n).is_symlink()
            ]
            for name in names:
                p = Path(base) / name
                allowed_suffixes = {
                    ".py",
                    ".html",
                    ".css",
                    ".js",
                    ".mjs",
                    ".cjs",
                    ".json",
                    ".svg",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                    ".woff",
                    ".woff2",
                    ".ttf",
                    ".sh",
                    ".yaml",
                    ".caddy",
                }
                if (
                    (
                        p.suffix in allowed_suffixes
                        or name
                        in {"Caddyfile", "Caddyfile.qa", "LICENSE.txt", "GENERATED.md"}
                        or name.startswith("Dockerfile.")
                    )
                    and not any(
                        word in name.lower()
                        for word in ["credential", "secret-key", ".env"]
                    )
                    and not p.is_symlink()
                    and name not in {".env.local", ".local-credentials"}
                    and not name.endswith((".pyc", ".pyo"))
                ):
                    files.append(p)
    files += [p for p in (BACKEND / "review/home-news").glob("*.mjs")]
    for source in files:
        relative = source.relative_to(PROJECT)
        destination = target / relative
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(source.read_bytes())
        destination.chmod(0o600)
        manifest[str(relative)] = file_sha(source)
    private_json(run / "source-manifest.json", manifest)
    return len(manifest)


def create(mode, purpose, resource_backend="postgres"):
    require(mode in {"auto", "manual"} and purpose.strip(), "Mode and purpose required")
    require(resource_backend in {"postgres", "docker"}, "Unknown resource backend")
    os.umask(0o077)
    with lock(True):
        run_id = (
            "qa-"
            + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid.uuid4().hex[:12]
        )
        run = RUNS / run_id
        require(
            not registry_path(run_id).exists(),
            "Run-id collision with registry/tombstone refused",
        )
        run.mkdir(mode=0o700)
        token = uuid.uuid4().hex + uuid.uuid4().hex
        owner_hash = digest(token.encode())
        private_json(
            run / "owner.json", {"schema": SCHEMA, "id": run_id, "token": token}
        )
        for name in ["tmp", "media", "output", "logs", "cache", "browser-profile"]:
            (run / name).mkdir(mode=0o700)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        db = "test_y3gym_qa_" + run_id[-12:] + "_" + owner_hash[:12]
        value = {
            "schema": SCHEMA,
            "id": run_id,
            "path": str(run),
            "inode": [run.stat().st_dev, run.stat().st_ino],
            "uid": os.getuid(),
            "owner_hash": owner_hash,
            "created_at": now(),
            "mode": mode,
            "resource_backend": resource_backend,
            "purpose": purpose,
            "state": "MANUAL_PENDING" if mode == "manual" else "PREPARED",
            "retention_reason": "manual review pending" if mode == "manual" else "",
            "cleanup_condition": "review complete, no live owned processes/connections, explicit exact-run cleanup",
            "port": port,
            "processes": [],
            "driver": None,
            "initialized": False,
            "database_names": [db, db + "_runner"],
            "databases": {},
            "external_DB_exception": "PostgreSQL physical files stay in the existing local service volume; only unique logical DBs with ownership comments are managed. No cluster/volume policy changes.",
            "outcome": None,
            "evidence": None,
        }
        if resource_backend == "docker":
            value["external_DB_exception"] = (
                "Docker QA uses only owned containers/networks/named volumes; existing PostgreSQL is never contacted"
            )
        save(run, value)
        try:
            value["source_files"] = copy_source(run)
            secret = run / "secret-key"
            secret.write_text(uuid.uuid4().hex + uuid.uuid4().hex)
            secret.chmod(0o600)
            settings = (
                """from config.settings import *
from pathlib import Path
import copy
BASE_DIR = Path(__file__).resolve().parent
PROTOTYPE_DIR = BASE_DIR / 'source/prototype'
STATICFILES_DIRS = [('prototype', PROTOTYPE_DIR)]
STATIC_ROOT = BASE_DIR / 'static'
MEDIA_ROOT = BASE_DIR / 'media'
DATABASES = copy.deepcopy(DATABASES)
DATABASES['default']['TEST'] = {'NAME': __RUNNER__}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': __LOCATION__}}
SESSION_COOKIE_NAME = __SESSION__
CSRF_COOKIE_NAME = __CSRF__
KAKAO_MAP_JS_KEY = ''
WAGTAILADMIN_BASE_URL = __ORIGIN__
TEST_RUNNER = 'qa_test_runner.Runner'
""".replace("__RUNNER__", repr(db + "_runner"))
                .replace("__LOCATION__", repr(run_id))
                .replace("__SESSION__", repr(run_id + "_session"))
                .replace("__CSRF__", repr(run_id + "_csrf"))
                .replace("__ORIGIN__", repr(f"http://localhost:{port}"))
            )
            (run / "qa_settings.py").write_text(settings)
            (run / "qa_settings.py").chmod(0o600)
            save(run, value)
        except BaseException:
            value["state"] = "RETAINED"
            value["retention_reason"] = (
                "creation interrupted/failed; inspect before explicit completion"
            )
            save(run, value)
            raise
    return run_id


def environment(run, value, token):
    from dotenv import dotenv_values

    donor = (
        dotenv_values(BACKEND / ".env.local")
        if value.get("resource_backend") != "docker"
        else {}
    )
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("Y3GYM_") and any(
            s in key
            for s in ["ORIGIN", "PASSWORD", "POSTS", "WORK", "REVIEW_DIR", "RUN_"]
        ):
            env.pop(key)
    for key in ["Y3GYM_DB_USER", "Y3GYM_DB_PASSWORD", "Y3GYM_DB_HOST", "Y3GYM_DB_PORT"]:
        if value.get("resource_backend") == "docker":
            env.pop(key, None)
        else:
            require(
                bool(donor.get(key)),
                "Local PostgreSQL connection configuration missing",
            )
            env[key] = donor[key]
    env.update(
        Y3GYM_DB_NAME=value["database_names"][0],
        DJANGO_SECRET_KEY=(run / "secret-key").read_text(),
        DJANGO_SETTINGS_MODULE="qa_settings",
        PYTHONPATH=os.pathsep.join(
            [str(run), str(run / "source/backend/scripts"), str(run / "source/backend")]
        ),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONUNBUFFERED="1",
        Y3GYM_KAKAO_MAP_JS_KEY="",
        Y3GYM_QA_RUN_ID=value["id"],
        Y3GYM_QA_RUN_TOKEN=token,
        Y3GYM_QA_RUN_DIR=str(run),
        Y3GYM_QA_PROJECT_ROOT=str(PROJECT),
        Y3GYM_QA_ORIGIN=f"http://localhost:{value['port']}",
        TMPDIR=str(run / "tmp"),
        TMP=str(run / "tmp"),
        TEMP=str(run / "tmp"),
        XDG_CACHE_HOME=str(run / "cache"),
        XDG_CONFIG_HOME=str(run / "browser-profile/config"),
        XDG_DATA_HOME=str(run / "browser-profile/data"),
    )
    for kind in ["BRAND", "BRANCH", "TRAINER", "HOME_NEWS", "POPUP", "WITHDRAWAL"]:
        env["Y3GYM_" + kind + "_REVIEW_DIR"] = str(run / "output" / kind.lower())
    cache = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or str(
        Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
        / "ms-playwright"
    )
    require(
        cache == "0" or Path(cache).is_dir(),
        "Existing Playwright browser cache not found; no download fallback",
    )
    env["PLAYWRIGHT_BROWSERS_PATH"] = cache
    env["NODE_OPTIONS"] = "--import=" + str(
        run / "source/backend/scripts/qa_browser_loader.mjs"
    )
    if value.get("resource_backend") == "docker":
        env["Y3GYM_QA_OWNER_HASH"] = value["owner_hash"]
    return env


def db_connect():
    import psycopg
    from dotenv import dotenv_values

    donor = dotenv_values(BACKEND / ".env.local")
    bindings = re.findall(
        r"127\.0\.0\.1:(\d+):5432", (BACKEND / "compose.yaml").read_text()
    )
    require(
        donor.get("Y3GYM_DB_HOST") in {"localhost", "127.0.0.1"}
        and donor.get("Y3GYM_DB_PORT") in bindings,
        "Only the existing declared loopback PostgreSQL service is permitted",
    )
    return psycopg.connect(
        dbname="postgres",
        user=donor["Y3GYM_DB_USER"],
        password=donor["Y3GYM_DB_PASSWORD"],
        host=donor["Y3GYM_DB_HOST"],
        port=donor["Y3GYM_DB_PORT"],
        autocommit=True,
    )


def db_state(cursor, name):
    cursor.execute(
        "SELECT oid,shobj_description(oid,'pg_database') FROM pg_database WHERE datname=%s",
        [name],
    )
    return cursor.fetchone()


def provision(run, value, token):
    from psycopg import sql

    with db_connect() as connection, connection.cursor() as cursor:
        for name in value["database_names"]:
            state = db_state(cursor, name)
            if state:
                require(
                    value["databases"].get(name) == state[0]
                    and state[1] == "y3gym-qa-owner:" + token,
                    "Existing/unmarked DB refused; no fallback/adoption",
                )
                continue
            require(
                name not in value["databases"],
                "Registered DB disappeared before provisioning",
            )
            cursor.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(
                    sql.Identifier(name)
                )
            )
            cursor.execute(
                sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                    sql.Identifier(name), sql.Literal("y3gym-qa-owner:" + token)
                )
            )
            value["databases"][name] = db_state(cursor, name)[0]
            save(run, value)


def initialize(run_id, fixtures=False):
    with lock():
        run, value, token = load(run_id)
        require(
            token is not None
            and not value["initialized"]
            and not value.get("initialization_started"),
            "Already initialized/deleted or prior initialization interrupted",
        )
        require(not owned_processes(run, value, token), "Run is active")
        value["initialization_started"] = True
        save(run, value)
        provision(run, value, token)
        env = environment(run, value, token)
        commands = [
            [str(PYTHON), "-B", "manage.py", "migrate", "--noinput", "--verbosity", "0"]
        ]
        if fixtures:
            commands += [
                [
                    str(PYTHON),
                    "-B",
                    "manage.py",
                    "shell",
                    "-c",
                    "from news.tests.review_fixtures import bootstrap_browser_review; bootstrap_browser_review()",
                ]
            ]
        with (run / "logs/initialize.log").open("xb") as log:
            for argv in commands:
                result = subprocess.run(
                    argv,
                    cwd=run / "source/backend",
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    umask=0o077,
                )
                require(
                    result.returncode == 0,
                    "Initialization failed; private log retained, never reinitialize existing data",
                )
        value["initialized"] = True
        save(run, value)
    return {"id": run_id, "initialized": True, "fixtures": fixtures}


def identity(info):
    return {
        k: info[k]
        for k in ["pid", "start_ticks", "cwd", "exe", "argv_sha256", "uid", "boot_id"]
    }


def capture_owned(pid, run, value, token):
    # /proc fields may cross a fork/exec boundary. Persist only two stable owned observations.
    previous = None
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        info = proc_info(pid, strict=True)
        if info is None:
            return None
        if (
            info["run_token"] == token
            and info["run_id"] == value["id"]
            and Path(info["cwd"]).is_relative_to(run)
        ):
            current = identity(info)
            if current == previous:
                return info
            previous = current
        else:
            previous = None
        time.sleep(0.01)
    raise Refused(
        "New process identity did not stabilize; preserve for status/inspection"
    )


def browser_process_records(run, token):
    path = run / "output/browser-processes.jsonl"
    if not path.exists():
        return []
    secure_file(path)
    records = {}
    for line in path.read_text().splitlines():
        signed = json.loads(line)
        payload = signed["payload_json"]
        require(
            hmac.compare_digest(
                hmac.new(token.encode(), payload.encode(), hashlib.sha256).hexdigest(),
                signed["signature"],
            ),
            "Browser birth record signature mismatch",
        )
        event = json.loads(payload)
        if event["event"] == "spawn":
            records[event["record"]["pid"]] = event["record"]
        elif event["event"] == "exit":
            old = records.get(event["pid"])
            if old and old["start_ticks"] == event["start_ticks"]:
                records.pop(event["pid"])
    return list(records.values())


def owned_processes(run, value, token):
    found = {}
    browser_records = browser_process_records(run, token)
    if value.get("resource_backend") == "docker":
        # Signed container-namespace PIDs are not host PIDs. Docker label/ID guards
        # own those processes and remove their exact containers at cleanup.
        browser_records = [
            r for r in browser_records if r.get("pid_namespace") != "owned-docker"
        ]
    for record in value["processes"] + browser_records:
        info = proc_info(record["pid"], strict=True)
        if info:
            require(
                identity(info) == record
                and info["run_token"] == token
                and info["run_id"] == value["id"],
                "Recorded process identity mismatch; fail closed",
            )
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        info = proc_info(p.name)
        if info and info["run_token"] == token and info["run_id"] == value["id"]:
            require(
                Path(info["cwd"]).is_relative_to(run),
                "Token-bearing process has unexpected cwd; fail closed",
            )
            found[info["pid"]] = identity(info)
    return list(found.values())


def driver_live(value):
    record = value.get("driver")
    info = proc_info(record["pid"], strict=True) if record else None
    return bool(info and identity(info) == record)


def stop_processes(run, value, token):
    require(
        not driver_live(value) or value["driver"]["pid"] == os.getpid(),
        "Auto driver still running; stop its operation before cleanup",
    )
    for _ in range(3):
        records = owned_processes(run, value, token)
        if not records:
            return
        descriptors = []
        try:
            for record in records:
                fd = os.pidfd_open(record["pid"])
                descriptors.append(fd)
                info = proc_info(record["pid"], strict=True)
                require(
                    info and identity(info) == record and info["run_token"] == token,
                    "PID reused or identity unavailable before stop",
                )
            # Validate every target before sending any signal. pidfd binds the exact kernel process.
            for fd in descriptors:
                signal.pidfd_send_signal(fd, signal.SIGTERM)
            poller = select.poll()
            for fd in descriptors:
                poller.register(fd, select.POLLIN)
            waiting = set(descriptors)
            deadline = time.monotonic() + 8
            while waiting and time.monotonic() < deadline:
                for fd, event in poller.poll(100):
                    if event & select.POLLIN:
                        waiting.discard(fd)
            require(
                not waiting,
                "Owned process did not exit; no escalation/resource deletion",
            )
        finally:
            for fd in descriptors:
                os.close(fd)
    require(
        not owned_processes(run, value, token), "New owned descendants remain; preserve"
    )


def listener_owned(pid, port):
    text = subprocess.check_output(["ss", "-ltnp", "sport = :" + str(port)], text=True)
    return f"127.0.0.1:{port}" in text and f"pid={pid}," in text


def http_ready(port):
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    began = time.monotonic()
    url = f"http://127.0.0.1:{port}/admin/login/"
    try:
        with build_opener(ProxyHandler({}), NoRedirect()).open(
            url, timeout=15
        ) as response:
            require(
                response.status == 200
                and response.headers.get_content_type() == "text/html",
                "Owned server login HTTP readiness failed",
            )
            body = response.read(2 * 1024 * 1024)
            require(b'name="username"' in body, "Login readiness content missing")
    except (TimeoutError, OSError):
        raise Refused(
            "Owned TCP listener has not proven login HTTP readiness; private run preserved"
        )
    return {
        "url": url,
        "HTTP_status": 200,
        "seconds": time.monotonic() - began,
        "response_body_not_stored": True,
    }


def start(run_id):
    with lock():
        run, value, token = load(run_id)
        require(token and value["initialized"], "Initialize isolated run first")
        require(
            value["state"] in {"MANUAL_PENDING", "PREPARED", "RETAINED"},
            "Run state does not permit start",
        )
        require(not owned_processes(run, value, token), "Run already active")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", value["port"]))
        env = environment(run, value, token)
        with (run / "logs/server.log").open("ab") as log:
            child = subprocess.Popen(
                [
                    str(PYTHON),
                    "-B",
                    "manage.py",
                    "runserver",
                    f"127.0.0.1:{value['port']}",
                    "--noreload",
                    "--insecure",
                ],
                cwd=run / "source/backend",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                umask=0o077,
            )
        info = capture_owned(child.pid, run, value, token)
        require(info is not None, "Server exited before identity capture")
        value["processes"] = [identity(info)]
        save(run, value)
    for _ in range(100):
        info = capture_owned(child.pid, run, value, token)
        require(info is not None, "Server startup failed; inspect private log")
        try:
            with socket.create_connection(("127.0.0.1", value["port"]), 0.1):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise Refused("Owned server startup timeout; status/stop required")
    require(
        listener_owned(child.pid, value["port"]),
        "Requested port is not bound by the recorded owned server; no other process is stopped",
    )
    ready = http_ready(value["port"])
    return {
        "HTTP_ready": ready,
        "id": run_id,
        "pid": child.pid,
        "origin": f"http://localhost:{value['port']}",
        "state": value["state"],
    }


def stop(run_id):
    with lock():
        run, value, token = load(run_id)
        require(token, "Run deleted")
        stop_processes(run, value, token)
        value["processes"] = []
        save(run, value)
    return {"id": run_id, "live_owned_processes": 0, "state": value["state"]}


def complete(run_id, reason):
    require(reason.strip(), "Completion reason required")
    with lock():
        run, value, token = load(run_id)
        require(token, "Run deleted")
        require(
            not driver_live(value) and not owned_processes(run, value, token),
            "Run still in use; stop first",
        )
        value.pop("cleanup_started", None)
        value.pop("cleanup_failure", None)
        value.update(
            state="READY",
            retention_reason="",
            completion_reason=reason,
            completed_at=now(),
        )
        save(run, value)
    return {"id": run_id, "state": "READY"}


def retain(run_id, reason, condition):
    require(
        reason.strip() and condition.strip(),
        "Retention reason and cleanup condition required",
    )
    with lock():
        run, value, token = load(run_id)
        require(token, "Run deleted")
        value.update(
            state="RETAINED", retention_reason=reason, cleanup_condition=condition
        )
        save(run, value)
    return {
        "id": run_id,
        "state": "RETAINED",
        "reason": reason,
        "cleanup_condition": condition,
    }


def tree_plan(run):
    result = []
    for base, dirs, names in os.walk(run, followlinks=False):
        for name in dirs + names:
            p = Path(base) / name
            v = p.lstat()
            require(
                not stat.S_ISLNK(v.st_mode),
                "Symlink found in run tree; preserve and inspect",
            )
            require(
                stat.S_ISDIR(v.st_mode)
                or (stat.S_ISREG(v.st_mode) and v.st_nlink == 1),
                "Special/hardlinked file refused",
            )
            require(v.st_uid == os.getuid(), "Run tree includes foreign-owned file")
            result.append(
                [str(p.relative_to(run)), v.st_mode, v.st_ino, v.st_size, v.st_mtime_ns]
            )
    return sorted(result)


def cleanup_plan(run, value, token):
    require(
        value["state"] == "READY",
        "Active/manual pending/retained run is protected; complete explicitly first",
    )
    require(
        not driver_live(value) and not owned_processes(run, value, token),
        "Run still active",
    )
    resources = []
    # Query every reserved name, even when interrupted before ownership registration.
    docker_resources = []
    if value.get("resource_backend") == "docker":
        from qa_docker import inspect_resources

        docker_resources = inspect_resources(value)
    else:
        with db_connect() as connection, connection.cursor() as cursor:
            for name in value["database_names"]:
                state = db_state(cursor, name)
                if state:
                    require(
                        state[0] == value["databases"].get(name)
                        and state[1] == "y3gym-qa-owner:" + token,
                        "DB owner marker/OID mismatch",
                    )
                    cursor.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname=%s", [name]
                    )
                    require(
                        cursor.fetchone()[0] == 0,
                        "Database has active connections; preserve",
                    )
                    resources.append({"name": name, "oid": state[0]})
    tree = tree_plan(run)
    plan = {
        "run_id": value["id"],
        "path": str(run),
        "inode": value["inode"],
        "files": tree,
        "databases": resources,
        "docker_resources": docker_resources,
    }
    return {**plan, "plan_id": digest(json.dumps(plan, sort_keys=True).encode())}


def _cleanup(run_id, dry_run=False, expected_plan=None):
    from psycopg import sql

    with lock():
        run, value, token = load(run_id)
        if token is None:
            return {"id": run_id, "already_cleaned": True, "state": "DELETED"}
        try:
            plan = cleanup_plan(run, value, token)
        except Refused as error:
            if dry_run:
                return {
                    "id": run_id,
                    "eligible": False,
                    "reason": str(error),
                    "state": value["state"],
                }
            raise
        safe = {
            "id": run_id,
            "eligible": True,
            "plan_id": plan["plan_id"],
            "path": str(run),
            "file_entries": len(plan["files"]),
            "database_names": [v["name"] for v in plan["databases"]],
        }
        if dry_run:
            return safe
        require(
            expected_plan == plan["plan_id"],
            "Exact current dry-run plan-id required; stale/missing plan refused",
        )
        # Preserve sanitized lifecycle evidence before deleting a resource.
        evidence = export_evidence(run, value, "explicit-cleanup")
        value["cleanup_started"] = {"plan_id": plan["plan_id"], "time": now()}
        save(run, value)
        if value.get("resource_backend") == "docker":
            from qa_docker import remove_resources

            remove_resources(value, plan["docker_resources"])
        if plan["databases"]:
            with db_connect() as connection, connection.cursor() as cursor:
                for resource in plan["databases"]:
                    current = db_state(cursor, resource["name"])
                    require(
                        current
                        and current[0] == resource["oid"]
                        and current[1] == "y3gym-qa-owner:" + token,
                        "DB changed after dry-run",
                    )
                    cursor.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname=%s",
                        [resource["name"]],
                    )
                    require(cursor.fetchone()[0] == 0, "DB became active")
                    cursor.execute(
                        sql.SQL("DROP DATABASE {}").format(
                            sql.Identifier(resource["name"])
                        )
                    )
        require(
            shutil.rmtree.avoids_symlink_attacks, "Descriptor-safe rmtree unavailable"
        )
        tree_plan(run)
        require(load(run_id)[1]["inode"] == plan["inode"], "Run root changed")
        fd = os.open(RUNS, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            shutil.rmtree(run_id, dir_fd=fd)
        finally:
            os.close(fd)
        tombstone = {
            **value,
            "state": "DELETED",
            "deleted_at": now(),
            "cleanup_plan_id": plan["plan_id"],
            "evidence": str(evidence),
            "cleanup_result": {
                "folder_absent": not run.exists(),
                "databases_dropped": [v["name"] for v in plan["databases"]],
                "docker_resources_removed": len(plan["docker_resources"]),
            },
        }
        private_json(registry_path(run_id), tombstone)
        result = {
            **safe,
            "state": "DELETED",
            "evidence": str(evidence),
            "cleanup": tombstone["cleanup_result"],
        }
        destination = evidence / f"cleanup-{uuid.uuid4().hex[:8]}.json"
        destination.write_text(json.dumps(result, indent=2) + "\n")
        return result


def export_evidence(run, value, phase):
    from qa_redaction import redact, secrets_for

    tree_plan(run)
    destination = BACKEND / "review/qa-lifecycle/runs" / value["id"]
    current = BACKEND
    for part in destination.relative_to(BACKEND).parts:
        current = current / part
        require(
            not current.is_symlink(), "Evidence destination cannot contain symlinks"
        )
        current.mkdir(exist_ok=True)
        require(
            current.is_dir() and current.resolve() == current,
            "Evidence destination escape refused",
        )
    known = secrets_for(
        run, PROJECT, include_project=value.get("resource_backend") != "docker"
    )
    data = {
        "schema": SCHEMA,
        "run_id": value["id"],
        "created_at": value["created_at"],
        "mode": value["mode"],
        "phase": phase,
        "state": value["state"],
        "outcome": value["outcome"],
        "source_files": value.get("source_files"),
        "source_manifest_sha256": file_sha(run / "source-manifest.json"),
        "external_DB_exception": value["external_DB_exception"],
        "raw_DB_credentials_media_profiles_environment_not_exported": True,
    }
    result = run / "output/suite-result.json"
    if result.is_file():
        raw = json.loads(result.read_text())
        data["tests"] = {
            k: raw[k]
            for k in [
                "collected",
                "run",
                "pass",
                "fail",
                "error",
                "skip",
                "executed_ids",
                "failure_locations",
                "runtime_scope",
            ]
            if k in raw
        }
    logs = []
    for log in (run / "logs").glob("*.log"):
        secure_file(log)
        raw = log.read_bytes()
        limit = 2 * 1024 * 1024
        excerpt = (
            raw
            if len(raw) <= limit
            else raw[: limit // 2]
            + b"\n[TRUNCATED; private original hash retained]\n"
            + raw[-limit // 2 :]
        )
        logs.append(
            {
                "file": log.name,
                "raw_bytes": len(raw),
                "raw_sha256": digest(raw),
                "truncated": len(raw) > limit,
                "diagnostic": redact(excerpt.decode(errors="replace"), known),
            }
        )
    data["sanitized_logs"] = logs
    browser_runtime = run / "output/browser-runtime.jsonl"
    if browser_runtime.is_file():
        data["browser_runtime"] = [
            {
                k: v
                for k, v in json.loads(line).items()
                if k
                in [
                    "exe",
                    "executable",
                    "pid",
                    "start_ticks",
                    "profile",
                    "tmpdir",
                    "browserCache",
                    "ownedRun",
                    "identity_basis",
                    "pid_namespace",
                ]
            }
            for line in browser_runtime.read_text().splitlines()
        ]
    summaries = []
    for report_path in (run / "output").rglob("*.json"):
        if report_path == result:
            continue
        try:
            report = json.loads(report_path.read_text())
            if isinstance(report, dict) and report.get("status") in ["PASS", "FAIL"]:
                summaries.append(
                    {
                        "path": str(report_path.relative_to(run)),
                        "status": report["status"],
                        "checks": len(report.get("checks", [])),
                        "errors": len(report.get("errors", [])),
                    }
                )
        except (ValueError, OSError):
            pass
    data["browser_result_summaries"] = summaries
    data["private_output_files"] = sum(p.is_file() for p in (run / "output").rglob("*"))
    docker_result = run / "output/docker-result.json"
    if value.get("resource_backend") == "docker" and docker_result.is_file():
        data["docker_validation"] = json.loads(docker_result.read_text())

    def scrub(value):
        if isinstance(value, dict):
            return {k: scrub(v) for k, v in value.items()}
        if isinstance(value, list):
            return [scrub(v) for v in value]
        if isinstance(value, str):
            for secret in known:
                value = value.replace(secret, "[REDACTED]")
        return value

    serialized = json.dumps(scrub(data), ensure_ascii=False, indent=2)
    require(
        not any(secret in serialized for secret in known),
        "Secret redaction check failed; preserve private run",
    )
    path = destination / f"evidence-{phase}-{uuid.uuid4().hex[:8]}.json"
    with path.open("x") as stream:
        stream.write(serialized + "\n")
    return destination


def status(run_id=None):
    if not layout():
        return {"runs": [], "managed_root_exists": False}
    ids = (
        [run_id]
        if run_id
        else sorted(p.stem for p in (RUNS / ".registry").glob("qa-*.json"))
    )
    result = []
    for name in ids:
        try:
            run, value, token = load(name)
            procs = owned_processes(run, value, token) if token else []
            interrupted = (
                value["state"] == "RUNNING"
                or value.get("initialization_started")
                and not value["initialized"]
            ) and not driver_live(value)
            result.append(
                {
                    "id": name,
                    "state": value["state"],
                    "mode": value["mode"],
                    "purpose": value["purpose"],
                    "retention_reason": value["retention_reason"],
                    "cleanup_condition": value["cleanup_condition"],
                    "live_owned_processes": procs,
                    "interrupted_driver": bool(interrupted),
                    "external_resources": resource_observation(value, token)
                    if token
                    else [],
                    "orphaned_owned_processes": bool(procs and interrupted),
                    "database_names": value["database_names"],
                    "external_DB_exception": value["external_DB_exception"],
                    "path": str(run),
                    "port": value["port"],
                }
            )
        except (Refused, OSError, ValueError) as error:
            result.append(
                {
                    "id": name,
                    "state": "UNKNOWN_PROTECTED",
                    "reason": type(error).__name__
                    if not isinstance(error, Refused)
                    else str(error),
                }
            )
    registered = set(ids)
    unknown = [
        p.name
        for p in RUNS.iterdir()
        if p.name != ".registry" and p.name not in registered
    ]
    return {
        "runs": result,
        "unknown_paths_preserved": unknown,
        "managed_root": str(RUNS),
    }


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("inventory")
    p.add_argument("--output", required=True)
    p = sub.add_parser("create")
    p.add_argument("--mode", choices=["auto", "manual"], required=True)
    p.add_argument("--purpose", required=True)
    p.add_argument(
        "--resource-backend", choices=["postgres", "docker"], default="postgres"
    )
    p = sub.add_parser("status")
    p.add_argument("run_id", nargs="?")
    p = sub.add_parser("initialize")
    p.add_argument("run_id")
    p.add_argument("--fixtures", action="store_true")
    for name in ["start", "stop"]:
        p = sub.add_parser(name)
        p.add_argument("run_id")
    p = sub.add_parser("complete")
    p.add_argument("run_id")
    p.add_argument("--reason", required=True)
    p = sub.add_parser("retain")
    p.add_argument("run_id")
    p.add_argument("--reason", required=True)
    p.add_argument("--cleanup-condition", required=True)
    p = sub.add_parser("cleanup")
    p.add_argument("run_id")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--plan")
    p = sub.add_parser("auto")
    p.add_argument("--purpose", required=True)
    p.add_argument(
        "--resource-backend", choices=["postgres", "docker"], default="postgres"
    )
    p.add_argument(
        "--browser",
        choices=["brand", "branch", "trainer", "home_news"],
        action="append",
        default=[],
    )
    p.add_argument("--retain-on-failure")
    p.add_argument("--cleanup-condition")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--tests", nargs="+")
    group.add_argument("--command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action == "auto":
            result, code = auto(
                args.purpose,
                args.tests,
                args.command,
                args.browser,
                args.retain_on_failure,
                args.cleanup_condition,
                args.resource_backend,
            )
            print(json.dumps(result, ensure_ascii=False))
            return code
        if args.action == "inventory":
            result = write_inventory(args.output)
        elif args.action == "create":
            result = {"id": create(args.mode, args.purpose, args.resource_backend)}
        elif args.action == "status":
            result = status(args.run_id)
        elif args.action == "initialize":
            result = initialize(args.run_id, args.fixtures)
        elif args.action == "start":
            result = start(args.run_id)
        elif args.action == "stop":
            result = stop(args.run_id)
        elif args.action == "complete":
            result = complete(args.run_id, args.reason)
        elif args.action == "retain":
            result = retain(args.run_id, args.reason, args.cleanup_condition)
        else:
            result = cleanup(args.run_id, args.dry_run, args.plan)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Refused as error:
        print(
            json.dumps({"status": "REFUSED", "reason": str(error)}, ensure_ascii=False)
        )
        return 3
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "type": type(error).__name__,
                    "reason": "Operation failed; inspect lifecycle status/evidence before further action",
                }
            )
        )
        return 2


def resource_observation(value, token):
    if value.get("resource_backend") == "docker":
        from qa_docker import inspect_resources

        return inspect_resources(value)
    found = []
    try:
        with db_connect() as connection, connection.cursor() as cursor:
            for name in value["database_names"]:
                row = db_state(cursor, name)
                found.append(
                    {
                        "name": name,
                        "exists": bool(row),
                        "registered_oid_matches": bool(
                            row and value["databases"].get(name) == row[0]
                        ),
                        "owner_comment_matches": bool(
                            row and row[1] == "y3gym-qa-owner:" + token
                        ),
                    }
                )
    except Exception:
        found = [
            {"status": "database observation unavailable; preserve reserved resources"}
        ]
    return found


def cleanup(run_id, dry_run=False, expected_plan=None):
    try:
        return _cleanup(run_id, dry_run, expected_plan)
    except BaseException as error:
        if not dry_run:
            with lock():
                entry = private_read(registry_path(run_id))
                run = RUNS / run_id
                if entry.get("cleanup_started") and entry["state"] != "DELETED":
                    entry.update(
                        state="CLEANUP_BLOCKED",
                        cleanup_failure={
                            "type": type(error).__name__,
                            "reason": str(error)
                            if isinstance(error, Refused)
                            else "resource deletion failed; inspect retained evidence",
                            "folder_exists": run.exists(),
                        },
                    )
                    token = None
                    try:
                        token = private_read(run / "owner.json")["token"]
                    except (OSError, Refused):
                        pass
                    entry["remaining_databases"] = (
                        resource_observation(entry, token)
                        if token
                        else [
                            {
                                "status": "ownership marker missing after partial cleanup; no adoption or further deletion"
                            }
                        ]
                    )
                    try:
                        save(
                            run,
                            {k: v for k, v in entry.items() if k != "manifest_sha256"},
                        )
                    except (OSError, Refused):
                        private_json(registry_path(run_id), entry)
                    directory = BACKEND / "review/qa-lifecycle/runs" / run_id
                    require(
                        not directory.is_symlink() and directory.resolve() == directory,
                        "Evidence path changed",
                    )
                    with (
                        directory / f"cleanup-failed-{uuid.uuid4().hex[:8]}.json"
                    ).open("x") as stream:
                        json.dump(
                            {
                                "run_id": run_id,
                                "status": "CLEANUP_BLOCKED",
                                "failure": entry["cleanup_failure"],
                                "remaining_databases": entry["remaining_databases"],
                            },
                            stream,
                            indent=2,
                        )
        raise


def auto(
    purpose,
    tests=None,
    command=None,
    browsers=(),
    retain_reason=None,
    cleanup_condition=None,
    resource_backend="postgres",
):
    require(bool(tests) != bool(command), "Choose explicit tests or one argv command")
    require(
        not retain_reason or bool(cleanup_condition),
        "Retained failure requires cleanup condition",
    )
    if tests:
        require(
            all(
                re.fullmatch(r"news\.tests(?:\.[A-Za-z0-9_]+)*", label)
                for label in tests
            ),
            "Explicit news.tests labels required",
        )
    require(
        not tests or resource_backend == "postgres",
        "Docker backend uses an explicit owned command; host whole tests are separate",
    )
    run_id = create("auto", purpose, resource_backend)
    code = 1
    cleanup_error = None
    evidence = None
    with lock():
        run, value, token = load(run_id)
        value.update(
            state="RUNNING", driver=identity(proc_info(os.getpid(), strict=True))
        )
        save(run, value)
    child = None
    try:
        if tests:
            with lock():
                provision(run, value, token)
        env = environment(run, value, token)
        for browser in browsers:
            env["Y3GYM_RUN_" + browser.upper() + "_BROWSER"] = "1"
        argv = (
            [
                str(PYTHON),
                "-B",
                "manage.py",
                "test",
                *tests,
                "--noinput",
                "--verbosity",
                "2",
            ]
            if tests
            else list(command)
        )
        with (run / "logs/command.log").open("xb") as stream:
            child = subprocess.Popen(
                argv,
                cwd=run / "source/backend",
                env=env,
                stdout=stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                umask=0o077,
            )
            info = capture_owned(child.pid, run, value, token)
            if info:
                with lock():
                    value["processes"] = [identity(info)]
                    save(run, value)
            code = child.wait()
        if code < 0:
            code = 128 - code
        value["outcome"] = {"exit_code": code, "kind": "tests" if tests else "command"}
    except BaseException as error:
        code = 130 if isinstance(error, KeyboardInterrupt) else 1
        value["outcome"] = {"exit_code": code, "exception_type": type(error).__name__}
        with (run / "logs/exception.log").open("x") as stream:
            stream.write(traceback.format_exc())
    finally:
        try:
            with lock():
                stop_processes(run, value, token)
                value["processes"] = []
                value["driver"] = None
                save(run, value)
                evidence = export_evidence(run, value, "auto-result")
                if code and retain_reason:
                    value.update(
                        state="RETAINED",
                        retention_reason=retain_reason,
                        cleanup_condition=cleanup_condition,
                    )
                else:
                    value.update(state="READY", retention_reason="")
                value["evidence"] = str(evidence)
                save(run, value)
            if not (code and retain_reason):
                plan = cleanup(run_id, True)
                require(
                    plan.get("eligible"),
                    "Auto cleanup blocked: " + plan.get("reason", "unknown"),
                )
                cleanup_result = cleanup(run_id, False, plan["plan_id"])
            else:
                cleanup_result = {
                    "state": "RETAINED",
                    "reason": retain_reason,
                    "cleanup_condition": cleanup_condition,
                }
        except BaseException as error:
            cleanup_error = {
                "type": type(error).__name__,
                "reason": str(error)
                if isinstance(error, Refused)
                else "cleanup failed; inspect private run and registry",
            }
            try:
                with lock():
                    run, current, token = load(run_id)
                    if token:
                        current.update(
                            state="CLEANUP_BLOCKED",
                            retention_reason="cleanup failed; inspect before completion",
                            cleanup_failure=cleanup_error,
                        )
                        current["remaining_databases"] = resource_observation(
                            current, token
                        )
                        save(run, current)
                        if evidence:
                            with (
                                Path(evidence)
                                / f"auto-cleanup-failed-{uuid.uuid4().hex[:8]}.json"
                            ).open("x") as stream:
                                json.dump(
                                    {
                                        "run_id": run_id,
                                        "error": cleanup_error,
                                        "remaining_databases": current[
                                            "remaining_databases"
                                        ],
                                    },
                                    stream,
                                    indent=2,
                                )
            except BaseException:
                pass  # Original exit remains primary; explicit cleanup_error is returned.
            cleanup_result = {"state": "CLEANUP_BLOCKED", "error": cleanup_error}
    result = {
        "run_id": run_id,
        "command_exit_code": code,
        "cleanup": cleanup_result,
        "cleanup_error": cleanup_error,
        "evidence": str(evidence) if evidence else None,
    }
    return result, code if code else (3 if cleanup_error else 0)


if __name__ == "__main__":
    sys.exit(main())
