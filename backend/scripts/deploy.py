"""Explicit local Compose operations; never contacts AWS or changes DNS/firewalls."""

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECRET_SQL_SETTINGS = (
    "\\set VERBOSITY terse\n"
    "SET log_statement='none'; SET log_min_error_statement='panic'; "
    "SET log_parameter_max_length_on_error=0; SET log_duration=off; "
    "SET log_min_duration_statement=-1; SET log_min_duration_sample=-1;\n"
)


def checked_env(path):
    path = Path(path).absolute()
    for item, mode in [(path.parent, 0o700), (path, 0o600)]:
        if item.is_symlink() or stat.S_IMODE(item.stat().st_mode) != mode:
            raise ValueError(
                "Environment requires a mode0700 directory and mode0600 file"
            )
        if item.stat().st_uid != os.getuid():
            raise ValueError("Environment must belong to the invoking operator")
    values = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError("Use literal KEY=VALUE environment lines")
        values[key] = value
    required = [
        "DJANGO_SECRET_KEY",
        "Y3GYM_DB_NAME",
        "Y3GYM_DB_USER",
        "Y3GYM_DB_PASSWORD",
        "Y3GYM_ALLOWED_HOSTS",
        "Y3GYM_ADMIN_ORIGIN",
        "Y3GYM_CSRF_TRUSTED_ORIGINS",
        "Y3GYM_DOMAIN",
        "Y3GYM_TLS_EMAIL",
        "Y3GYM_APP_IMAGE",
        "Y3GYM_DB_ADMIN_USER",
        "Y3GYM_DB_ADMIN_PASSWORD",
    ]
    if any(not values.get(key) for key in required):
        raise ValueError("Required deployment environment field is empty")
    if values["Y3GYM_DB_ADMIN_USER"] == values["Y3GYM_DB_USER"]:
        raise ValueError("Bootstrap administrator and application DB roles must differ")
    if any(
        not re.fullmatch(r"[a-z][a-z0-9_]{2,40}", values[key])
        for key in ["Y3GYM_DB_NAME", "Y3GYM_DB_USER", "Y3GYM_DB_ADMIN_USER"]
    ):
        raise ValueError("Use explicit conservative database and role identifiers")
    domain = values["Y3GYM_DOMAIN"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]+[A-Za-z0-9]", domain):
        raise ValueError("Domain must be one bare hostname")
    if values["Y3GYM_ADMIN_ORIGIN"] != "https://" + domain:
        raise ValueError("Administrator origin must be the explicit HTTPS domain")
    if domain not in values["Y3GYM_ALLOWED_HOSTS"].split(","):
        raise ValueError("Domain must be explicitly allowed")
    if "latest" in values["Y3GYM_APP_IMAGE"].split(":")[-1]:
        raise ValueError("Use a versioned application tag or digest")
    capacity = {}
    for name, default, maximum in [
        ("Y3GYM_WORKERS", 1, 16),
        ("Y3GYM_THREADS", 2, 16),
        ("Y3GYM_PG_MAX_CONNECTIONS", 50, 1000),
    ]:
        value = values.get(name, str(default))
        if not value.isdecimal() or not 1 <= int(value) <= maximum:
            raise ValueError("Worker/thread/connection capacity must be positive")
        capacity[name] = int(value)
    if (
        capacity["Y3GYM_WORKERS"] * capacity["Y3GYM_THREADS"] + 10
        > capacity["Y3GYM_PG_MAX_CONNECTIONS"]
    ):
        raise ValueError(
            "Database connection budget needs room for every worker thread and maintenance"
        )
    return values


def source_fingerprint(root=ROOT):
    roots = [root / "backend/config", root / "backend/news", root / "prototype/assets"]
    paths = [
        p
        for base in roots
        for p in base.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and "tests" not in p.parts
        and "management" not in p.parts
        and p.suffix != ".pyc"
    ]
    paths += list((root / "prototype").glob("*.js"))
    paths += [
        root / p
        for p in [
            "Dockerfile",
            ".dockerignore",
            "backend/manage.py",
            "backend/pyproject.toml",
            "backend/uv.lock",
            "deploy/gunicorn.conf.py",
            "prototype/index.html",
            "prototype/styles.css",
        ]
    ]
    manifest = {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(set(paths))
    }
    fingerprint = hashlib.sha256(
        json.dumps(manifest, sort_keys=True).encode()
    ).hexdigest()
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root))
    return {
        "revision": revision,
        "dirty": dirty,
        "source_fingerprint": fingerprint,
        "files": manifest,
    }


def compose(
    values,
    project,
    *args,
    capture=False,
    input_bytes=None,
    stdout_file=None,
    stdin_file=None,
):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,62}", project):
        raise ValueError("Explicit Compose project name required")
    return subprocess.run(
        [
            "docker",
            "compose",
            "--project-name",
            project,
            "-f",
            str(ROOT / "compose.production.yaml"),
            *args,
        ],
        env={**os.environ, **values},
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE if capture else stdout_file,
        stderr=subprocess.PIPE if capture else None,
        input=input_bytes,
        stdin=stdin_file,
    )


def file_sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def running_release(values, project):
    """Backup must identify the running release before pausing any writer."""
    configured = json.loads(
        subprocess.check_output(
            ["docker", "image", "inspect", values["Y3GYM_APP_IMAGE"]]
        )
    )[0]
    app = None
    for service in ["app", "proxy"]:
        ids = compose(values, project, "ps", "-q", service, capture=True).stdout.split()
        if len(ids) != 1:
            raise ValueError("Backup requires one running app and proxy")
        container = json.loads(
            subprocess.check_output(["docker", "inspect", ids[0].decode()])
        )[0]
        if not container["State"]["Running"]:
            raise ValueError(
                "Backup requires running writers before the controlled pause"
            )
        if service == "app":
            app = container
    if app["Image"] != configured["Id"]:
        raise ValueError(
            "Backup refuses an environment image different from the running app"
        )
    labels = configured["Config"]["Labels"]
    release = {
        "revision": labels["org.opencontainers.image.revision"],
        "source_fingerprint": labels["org.opencontainers.image.source-fingerprint"],
    }
    return {"release": release, "image_id": app["Image"]}


def provision(values, project):
    """One explicit new-database operation. Existing roles are never reset."""
    compose(values, project, "up", "-d", "--wait", "database")
    user, name = values["Y3GYM_DB_USER"], values["Y3GYM_DB_NAME"]
    preflight = (
        f"SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='{user}'), "
        f"EXISTS(SELECT 1 FROM pg_database WHERE datname='{name}');\n"
    )
    state = compose(
        values,
        project,
        "exec",
        "-T",
        "database",
        "sh",
        "-c",
        'exec psql -X -At -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres',
        capture=True,
        input_bytes=preflight.encode(),
    ).stdout.strip()
    if state != b"f|f":
        raise ValueError(
            "Existing application role/database refused; credentials are unchanged"
        )
    password = values["Y3GYM_DB_PASSWORD"].replace("'", "''")
    # stdin, not argv/environment output: psql does not echo this input.
    sql = (
        SECRET_SQL_SETTINGS
        + f"CREATE ROLE \"{user}\" LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION;\n"
        f'CREATE DATABASE "{name}" OWNER "{user}";\n'
        f'REVOKE CONNECT ON DATABASE "{name}" FROM PUBLIC;\n'
        f'GRANT CONNECT ON DATABASE "{name}" TO "{user}";\n'
    )
    result = compose(
        values,
        project,
        "exec",
        "-T",
        "database",
        "sh",
        "-c",
        'exec psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres',
        capture=True,
        input_bytes=sql.encode(),
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument(
        "action",
        choices=[
            "validate",
            "build",
            "provision",
            "prepare",
            "up",
            "stop",
            "status",
            "admin",
            "backup",
            "restore",
        ],
    )
    parser.add_argument("--directory")
    parser.add_argument("--confirm-empty-restore", action="store_true")
    args = parser.parse_args()
    values = checked_env(args.env)
    compose(values, args.project, "config", "--quiet")
    if args.action == "validate":
        print("Deployment environment/Compose syntax valid; no AWS action performed")
    elif args.action == "build":
        version = source_fingerprint()
        subprocess.run(
            [
                "docker",
                "build",
                "--build-arg",
                "SOURCE_REVISION=" + version["revision"],
                "--build-arg",
                "SOURCE_FINGERPRINT=" + version["source_fingerprint"],
                "--tag",
                values["Y3GYM_APP_IMAGE"],
                str(ROOT),
            ],
            check=True,
        )
        version["image"] = json.loads(
            subprocess.check_output(
                ["docker", "image", "inspect", values["Y3GYM_APP_IMAGE"]]
            )
        )[0]["Id"]
        print(json.dumps(version, sort_keys=True))
    elif args.action == "provision":
        provision(values, args.project)
    elif args.action == "prepare":
        compose(values, args.project, "up", "-d", "--wait", "database")
        for command in [
            ["check", "--deploy"],
            ["migrate", "--plan"],
            ["migrate", "--noinput"],
            ["collectstatic", "--noinput"],
        ]:
            compose(
                values,
                args.project,
                "run",
                "--rm",
                "--no-deps",
                "app",
                "python",
                "manage.py",
                *command,
            )
    elif args.action == "up":
        # Does not migrate, seed, initialize a user, or delete a volume.
        compose(values, args.project, "up", "-d", "--wait", "--wait-timeout", "90")
    elif args.action == "stop":
        compose(values, args.project, "stop")
    elif args.action == "status":
        compose(values, args.project, "ps")
    elif args.action == "admin":
        compose(
            values,
            args.project,
            "run",
            "--rm",
            "app",
            "python",
            "manage.py",
            "createsuperuser",
        )
    else:
        directory = Path(args.directory or "").absolute()
        if not args.directory or directory.is_symlink():
            raise ValueError("Explicit private backup/restore directory required")
        if args.action == "backup":
            metadata = running_release(values, args.project)
            directory.mkdir(mode=0o700, parents=False, exist_ok=False)
            os.chmod(directory, 0o700)
            # Stop every application writer, including lazy rendition generation.
            compose(values, args.project, "stop", "proxy", "app")
            try:
                with (directory / "database.dump").open("xb") as out:
                    compose(
                        values,
                        args.project,
                        "exec",
                        "-T",
                        "database",
                        "sh",
                        "-c",
                        'exec pg_dump -Fc -U "$POSTGRES_USER" "$Y3GYM_DB_NAME"',
                        stdout_file=out,
                    )
                with (directory / "media.tar").open("xb") as out:
                    compose(
                        values,
                        args.project,
                        "run",
                        "--rm",
                        "--no-deps",
                        "-T",
                        "app",
                        "tar",
                        "-C",
                        "/var/lib/y3gym/media",
                        "-cf",
                        "-",
                        ".",
                        stdout_file=out,
                    )
                metadata["sha256"] = {
                    p.name: file_sha256(p) for p in directory.iterdir()
                }
                (directory / "manifest.json").write_text(
                    json.dumps(metadata, indent=2) + "\n"
                )
                for path in directory.iterdir():
                    path.chmod(0o600)
            finally:
                compose(values, args.project, "up", "-d", "--wait", "app", "proxy")
            print(
                "Consistent local export complete; off-server backup is NOT configured"
            )
        else:
            if not args.confirm_empty_restore:
                raise ValueError(
                    "Restore requires a new isolated empty deployment and explicit confirmation"
                )
            manifest = json.loads((directory / "manifest.json").read_text())
            actual_image = json.loads(
                subprocess.check_output(
                    ["docker", "image", "inspect", values["Y3GYM_APP_IMAGE"]]
                )
            )[0]["Id"]
            if actual_image != manifest["image_id"]:
                raise ValueError(
                    "Restore requires the matching immutable application image"
                )
            if set(manifest["sha256"]) != {"database.dump", "media.tar"}:
                raise ValueError(
                    "Backup must contain exactly the database and media digests"
                )
            if any(
                file_sha256(directory / name) != h
                for name, h in manifest["sha256"].items()
            ):
                raise ValueError("Backup digest mismatch")
            # Only a brand new deployment is eligible. Existing contents are never cleaned.
            ps = compose(values, args.project, "ps", "-aq", capture=True)
            if ps.stdout.strip():
                raise ValueError("Restore refuses an existing Compose deployment")
            config = json.loads(
                compose(
                    values, args.project, "config", "--format", "json", capture=True
                ).stdout
            )
            for volume in config["volumes"].values():
                existing = subprocess.run(
                    ["docker", "volume", "inspect", volume["name"]], capture_output=True
                )
                if existing.returncode == 0:
                    raise ValueError(
                        "Restore refuses an existing exact-name volume, including unlabelled or foreign volumes"
                    )
            if subprocess.check_output(
                [
                    "docker",
                    "volume",
                    "ls",
                    "-q",
                    "--filter",
                    "label=com.docker.compose.project=" + args.project,
                ]
            ).strip():
                raise ValueError("Restore refuses pre-existing deployment volumes")
            provision(values, args.project)
            result = compose(
                values,
                args.project,
                "exec",
                "-T",
                "database",
                "sh",
                "-c",
                'psql -At -U "$POSTGRES_USER" -d "$Y3GYM_DB_NAME" -c "SELECT count(*) FROM pg_tables WHERE schemaname=\'public\'"',
                capture=True,
            )
            if result.stdout.strip() != b"0":
                raise ValueError("Restore database is not empty")
            with (directory / "database.dump").open("rb") as source:
                compose(
                    values,
                    args.project,
                    "exec",
                    "-T",
                    "database",
                    "sh",
                    "-c",
                    'exec pg_restore --exit-on-error -U "$POSTGRES_USER" -d "$Y3GYM_DB_NAME"',
                    stdin_file=source,
                )
            with (directory / "media.tar").open("rb") as source:
                compose(
                    values,
                    args.project,
                    "run",
                    "--rm",
                    "--no-deps",
                    "-T",
                    "app",
                    "tar",
                    "-C",
                    "/var/lib/y3gym/media",
                    "-xf",
                    "-",
                    stdin_file=source,
                )
            print(
                "Isolated restore complete; verify release/schema/permissions before serving traffic"
            )


if __name__ == "__main__":
    os.umask(0o077)
    main()
