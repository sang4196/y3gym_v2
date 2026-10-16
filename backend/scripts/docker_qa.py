"""Actual Docker deployment-path rehearsal, invoked only by managed auto --command."""

import hashlib
import http.client
import http.cookiejar
import importlib.util
import io
import json
import os
import secrets
import socket
import ssl
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image


def main():
    run = Path(os.environ["Y3GYM_QA_RUN_DIR"])
    run_id = os.environ["Y3GYM_QA_RUN_ID"]
    owner = json.loads((run / "owner.json").read_text())
    assert owner["token"] == os.environ["Y3GYM_QA_RUN_TOKEN"]
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["resource_backend"] == "docker"
    source = run / "source"
    canonical = Path(os.environ["Y3GYM_QA_PROJECT_ROOT"])
    spec = importlib.util.spec_from_file_location(
        "deployment", source / "backend/scripts/deploy.py"
    )
    deployment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(deployment)
    project = "y3gymqa-" + run_id.rsplit("-", 1)[1]
    domain = "qa-" + run_id.rsplit("-", 1)[1] + ".test"
    checks, details = [], {}
    result = {"status": "FAIL", "checks": checks, "details": details}
    step = "setup"
    log = (run / "logs/docker.log").open("xb")

    def execute(
        argv, *, data=None, capture=False, env=None, stdout_file=None, stdin_file=None
    ):
        return subprocess.run(
            argv,
            input=data,
            stdout=subprocess.PIPE if capture else (stdout_file or log),
            stderr=log,
            env=env,
            check=True,
            cwd=source,
            stdin=stdin_file,
        )

    def port():
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    credentials = {
        "username": "docker_editor",
        "password": secrets.token_urlsafe(30),
        "db_password": secrets.token_urlsafe(32),
        "db_admin_password": secrets.token_urlsafe(32),
    }
    (run / ".local-credentials").write_text(json.dumps(credentials))
    values = {
        "Y3GYM_ENV": "production",
        "DJANGO_SECRET_KEY": (run / "secret-key").read_text(),
        "Y3GYM_DB_NAME": "y3gymqa_" + run_id.rsplit("-", 1)[1],
        "Y3GYM_DB_USER": "app_user",
        "Y3GYM_DB_PASSWORD": credentials["db_password"],
        "Y3GYM_DB_ADMIN_USER": "bootstrap_admin",
        "Y3GYM_DB_ADMIN_PASSWORD": credentials["db_admin_password"],
        "Y3GYM_ALLOWED_HOSTS": domain,
        "Y3GYM_ADMIN_ORIGIN": "https://" + domain,
        "Y3GYM_CSRF_TRUSTED_ORIGINS": "https://" + domain,
        "Y3GYM_DOMAIN": domain,
        "Y3GYM_TLS_EMAIL": "qa@example.invalid",
        "Y3GYM_APP_IMAGE": project + ":app",
        "Y3GYM_WORKERS": "1",
        "Y3GYM_THREADS": "2",
        "Y3GYM_QA_RUN_ID": run_id,
        "Y3GYM_QA_OWNER_HASH": manifest["owner_hash"],
        "Y3GYM_QA_HTTP_PORT": str(port()),
        "Y3GYM_QA_HTTPS_PORT": str(port()),
    }
    envfile = run / "production.env"
    envfile.write_text("\n".join(k + "=" + v for k, v in values.items()) + "\n")
    envfile.chmod(0o600)
    deployment.checked_env(envfile)

    def compose(
        vals,
        target,
        *args,
        capture=False,
        input_bytes=None,
        stdout_file=None,
        stdin_file=None,
    ):
        return execute(
            [
                "docker",
                "compose",
                "-p",
                target,
                "-f",
                str(source / "compose.production.yaml"),
                "-f",
                str(source / "deploy/compose.qa.yaml"),
                *args,
            ],
            data=input_bytes,
            capture=capture,
            env={**os.environ, **vals},
            stdout_file=stdout_file,
            stdin_file=stdin_file,
        )

    deployment.compose = compose

    def c(*args, capture=False, data=None, target=project):
        return compose(values, target, *args, capture=capture, input_bytes=data)

    def shell(code, target=project):
        output = c(
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "app",
            "python",
            "manage.py",
            "shell",
            "--no-imports",
            capture=True,
            data=code.encode(),
            target=target,
        ).stdout.decode()
        return json.loads(
            [line for line in output.splitlines() if line.startswith("QAJSON:")][-1][7:]
        )

    def protected_metadata():
        files = [
            canonical / "backend/.env.local",
            canonical / "backend/.local-credentials",
        ]
        return {
            "servers": {
                str(pid): Path(f"/proc/{pid}/stat")
                .read_text()
                .split(")", 1)[1]
                .split()[19]
                for pid in [714159, 1020914, 2910010]
            },
            "private": {
                str(p): [
                    p.stat().st_ino,
                    p.stat().st_size,
                    p.stat().st_mtime_ns,
                    hashlib.sha256(p.read_bytes()).hexdigest(),
                ]
                for p in files
            },
        }

    before = protected_metadata()
    try:
        step = "build"
        fingerprint = deployment.source_fingerprint(source)
        assert (
            fingerprint["files"] == deployment.source_fingerprint(canonical)["files"]
        ), "QA image inputs must exactly match canonical image inputs"
        details["canonical_app_input_parity"] = True
        details["app_input_files"] = len(fingerprint["files"])
        details["release"] = {k: v for k, v in fingerprint.items() if k != "files"}
        # Synthetic canaries are placed only in the owned source copy.
        for relative in [
            "backend/.env.local",
            "backend/.private-media/QA_CANARY",
            ".local/qa/QA_CANARY",
            "backend/review/QA_CANARY",
            "prototype/node_modules/QA_CANARY",
        ]:
            p = source / relative
            p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            p.write_text("OWNED_BUILD_CONTEXT_CANARY")
        execute(
            [
                "docker",
                "build",
                "-t",
                values["Y3GYM_APP_IMAGE"],
                "--build-arg",
                "SOURCE_REVISION=" + fingerprint["revision"],
                "--build-arg",
                "SOURCE_FINGERPRINT=" + fingerprint["source_fingerprint"],
                "--build-arg",
                "QA_RUN_ID=" + run_id,
                "--build-arg",
                "QA_OWNER_HASH=" + manifest["owner_hash"],
                str(source),
            ]
        )
        image = json.loads(
            execute(
                ["docker", "image", "inspect", values["Y3GYM_APP_IMAGE"]], capture=True
            ).stdout
        )[0]
        details["image_id"] = image["Id"]
        probe = "import pathlib,json,sys,importlib.metadata as m; p=pathlib.Path('/app'); forbidden=[x for x in p.rglob('*') if x.name in ['.env.local','QA_CANARY','node_modules','.venv','.local','review','tests','management','__pycache__']]; assert not forbidden, forbidden; assert pathlib.Path('/app/prototype/assets/fonts/LICENSE.txt').is_file(); print(json.dumps({k:m.version(k) for k in ['Django','wagtail','gunicorn']}));"
        versions = json.loads(
            execute(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--read-only",
                    "--network",
                    "none",
                    "--label",
                    "com.docker.compose.project=" + project,
                    "--label",
                    "com.y3gym.qa.run=" + run_id,
                    "--label",
                    "com.y3gym.qa.owner=" + manifest["owner_hash"],
                    values["Y3GYM_APP_IMAGE"],
                    "python",
                    "-c",
                    probe,
                ],
                capture=True,
            ).stdout
        )
        assert versions == {
            "Django": "5.2.18",
            "wagtail": "7.4.3",
            "gunicorn": "26.2.0",
        }
        details["locked_versions"] = versions
        checks.append(
            "Immutable non-root image locked install and sensitive/QA canary exclusion"
        )
        config = json.loads(c("config", "--format", "json", capture=True).stdout)
        assert config["services"]["app"]["read_only"] and not config["services"][
            "app"
        ].get("ports")
        assert not config["services"]["database"].get("ports")
        assert all(
            v["target"] not in ["/media", "/var/lib/y3gym/media"]
            for v in config["services"]["proxy"]["volumes"]
        )
        checks.append(
            "Only loopback QA proxy ports; app/DB hidden; proxy never mounts media"
        )
        step = "new_database_prepare"
        deployment.provision(values, project)
        for command in [
            ["check", "--deploy"],
            ["makemigrations", "--check", "--dry-run"],
            ["migrate", "--noinput"],
            ["collectstatic", "--noinput"],
        ]:
            c("run", "--rm", "--no-deps", "app", "python", "manage.py", *command)
        role = shell(
            "from django.db import connection; import json\nwith connection.cursor() as c:\n c.execute('SELECT rolsuper,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=current_user'); role=c.fetchone(); c.execute('SHOW max_connections'); cap=c.fetchone()[0]\nprint('QAJSON:'+json.dumps({'role':role,'max_connections':cap}))"
        )
        assert role["role"] == [False, False, False] and role["max_connections"] == "50"
        checks.append(
            "Blank PostgreSQL17.11 migration and separate non-superuser application role"
        )
        try:
            deployment.provision(values, project)
            raise AssertionError(
                "Duplicate provision must refuse existing role/database"
            )
        except ValueError as error:
            assert "Existing application" in str(error)
        secret_error_sql = deployment.SECRET_SQL_SETTINGS + (
            'CREATE ROLE "app_user" LOGIN PASSWORD '
            + "'"
            + credentials["db_password"]
            + "';\n"
        )
        try:
            c(
                "exec",
                "-T",
                "database",
                "sh",
                "-c",
                'exec psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres',
                capture=True,
                data=secret_error_sql.encode(),
            )
            raise AssertionError("Expected duplicate-role error")
        except subprocess.CalledProcessError as error:
            assert error.returncode == 3
        database_log = c("logs", "--no-color", "database", capture=True).stdout
        assert all(
            credentials[key].encode() not in database_log
            for key in ["password", "db_password", "db_admin_password"]
        )
        checks.append(
            "Duplicate provision refuses before secret SQL; forced secret-session error does not disclose password in server log"
        )
        c("up", "-d", "--wait", "--wait-timeout", "90")
        c("cp", "proxy:/data/caddy/pki/authorities/local/root.crt", str(run / "ca.crt"))
        context = ssl.create_default_context(cafile=str(run / "ca.crt"))

        class LocalTLS(http.client.HTTPSConnection):
            def connect(self):
                sock = socket.create_connection(
                    ("127.0.0.1", int(values["Y3GYM_QA_HTTPS_PORT"])), self.timeout
                )
                self.sock = context.wrap_socket(sock, server_hostname=domain)

        class Handler(urllib.request.HTTPSHandler):
            def https_open(self, request):
                return self.do_open(LocalTLS, request, context=context)

        cookies = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            Handler(), urllib.request.HTTPCookieProcessor(cookies)
        )
        origin = "https://" + domain

        def request(path, data=None, headers=None, client=opener):
            req = urllib.request.Request(
                origin + path, data=data, headers=headers or {}
            )
            try:
                with client.open(req, timeout=30) as response:
                    return (
                        response.status,
                        response.read(),
                        dict(response.headers),
                        response.url,
                    )
            except urllib.error.HTTPError as error:
                return error.code, error.read(), dict(error.headers), error.url

        first = time.monotonic()
        assert request("/")[0] == 200
        details["empty_first_home_seconds"] = round(time.monotonic() - first, 3)
        login = request("/admin/login/")
        csrf = BeautifulSoup(login[1], "html.parser").select_one(
            '[name="csrfmiddlewaretoken"]'
        )["value"]
        shell(
            "from django.contrib.auth import get_user_model; import json\nu=get_user_model().objects.create_superuser("
            + repr(credentials["username"])
            + ", 'qa@example.invalid', "
            + repr(credentials["password"])
            + ")\nprint('QAJSON:'+json.dumps({'id':u.pk}))"
        )
        logged = request(
            "/admin/login/",
            urllib.parse.urlencode(
                {
                    "username": credentials["username"],
                    "password": credentials["password"],
                    "csrfmiddlewaretoken": csrf,
                    "next": "/admin/",
                }
            ).encode(),
            {"Origin": origin, "Referer": origin + "/admin/login/"},
        )
        assert logged[0] == 200 and logged[3].endswith("/admin/")
        production_cookies = {cookie.name: cookie for cookie in cookies}
        assert all(
            production_cookies[name].secure for name in ["y3gym_csrf", "y3gym_session"]
        )
        assert production_cookies["y3gym_session"].has_nonstandard_attr("HttpOnly")
        checks.append(
            "Production HTTPS admin login/secure cookies with owned CA and normal certificate verification"
        )
        step = "uploads_and_publication"

        def upload(payload, title):
            page = request("/admin/images/add/")
            token = BeautifulSoup(page[1], "html.parser").select_one(
                '[name="csrfmiddlewaretoken"]'
            )["value"]
            boundary = "y3gym" + secrets.token_hex(16)
            body = b""
            for key, value in {"csrfmiddlewaretoken": token, "title": title}.items():
                body += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
            body += (
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="owned.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
                + payload
                + f"\r\n--{boundary}--\r\n".encode()
            )
            response = request(
                "/admin/images/add/",
                body,
                {
                    "Content-Type": "multipart/form-data; boundary=" + boundary,
                    "Origin": origin,
                    "Referer": origin + "/admin/images/add/",
                },
            )
            assert response[0] == 200 and response[3] == origin + "/admin/images/"
            stored = shell(
                "from news.models import ContentImage;import hashlib,json\ni=ContentImage.objects.get(title="
                + repr(title)
                + ",file_hash="
                + repr(hashlib.sha1(payload).hexdigest())
                + ")\nprint('QAJSON:'+json.dumps({'id':i.pk,'size':i.file.size,'sha256':hashlib.sha256(i.file.read()).hexdigest()}))"
            )
            assert stored["size"] == len(payload)
            assert stored["sha256"] == hashlib.sha256(payload).hexdigest()
            return stored["id"]

        stream = io.BytesIO()
        Image.new("RGB", (180, 300), (60, 130, 190)).save(stream, "PNG")
        image_id = upload(stream.getvalue(), "[TEST] Docker photo")
        near = io.BytesIO()
        Image.frombytes("RGB", (1800, 1900), secrets.token_bytes(1800 * 1900 * 3)).save(
            near, "PNG"
        )
        assert 9.5 * 1024**2 < len(near.getvalue()) <= 10 * 1024**2
        large_id = upload(near.getvalue(), "[TEST] near10MiB")
        details["near_limit_upload"] = {
            "bytes": len(near.getvalue()),
            "image_id": large_id,
            "status": "PASS",
        }
        checks.append(
            "Actual admin multipart uploads through Caddy including near10MiB unchanged limit"
        )
        public = urllib.request.build_opener(Handler())
        private_large = shell(
            "from news.models import ContentImage;import json\ni=ContentImage.objects.get(pk="
            + str(large_id)
            + ");r=i.get_rendition('max-2560x2560')\nprint('QAJSON:'+json.dumps({'original':i.file.url,'rendition':r.url}))"
        )
        assert request(private_large["original"], client=public)[0] == 404
        assert request(private_large["rendition"], client=public)[0] == 404
        protected_download = request(private_large["original"])
        assert protected_download[0] == 200
        assert (
            hashlib.sha256(protected_download[1]).hexdigest()
            == hashlib.sha256(near.getvalue()).hexdigest()
        )
        checks.append(
            "Draft-only original/rendition denied anonymously; actual near10MiB FileResponse download verified for editor"
        )
        fixture = shell(
            "from news.models import ContentImage,Post,BrandContent,Branch; import json\ni=ContentImage.objects.get(pk="
            + str(image_id)
            + ")\np=Post.objects.create(title='[TEST] Docker draft',summary='Synthetic deployment fixture',body='<p>[TEST] safe fixture</p>',cover_image=i);p.save_revision()\nb=BrandContent.objects.create(name='[TEST] Docker',intro_title='[TEST] Docker home',hero_image=i);b.save_revision().publish()\nbr=Branch.objects.create(key='main',name='[TEST] Main',address='[TEST] synthetic address',opening_hours='[TEST] hours');br.save_revision().publish()\nr=i.get_rendition('max-2560x2560')\nprint('QAJSON:'+json.dumps({'post_id':p.pk,'original':i.file.url,'rendition':r.url}))"
        )
        assert (
            request("/news/" + str(fixture["post_id"]) + "/", client=public)[0] == 404
        )
        assert request(fixture["original"], client=public)[0] == 404
        # Image is shared by public brand: rendition public, original stays private.
        assert request(fixture["rendition"], client=public)[0] == 200
        assert request(fixture["original"])[0] == 200
        checks.append(
            "Anonymous originals blocked even with public shared rendition; authorized editor can read original"
        )
        times = []
        for _ in range(2):
            start = time.monotonic()
            assert request("/", client=public)[0] == 200
            times.append(round(time.monotonic() - start, 3))
        details["populated_home_first_repeat_seconds"] = times
        # Check required assets by actual page references, never by a fixed total count.
        page = request("/admin/login/", client=public)
        assets = sorted(
            {
                tag.get("src") or tag.get("href")
                for tag in BeautifulSoup(page[1], "html.parser").select(
                    'script[src^="/static/"],link[href^="/static/"]'
                )
            }
        )
        static_paths = assets + [
            "/static/prototype/assets/fonts/PretendardVariable.woff2",
            "/static/prototype/assets/fonts/LICENSE.txt",
            "/static/news/content-images.js",
            "/static/prototype/styles.css",
        ]
        static_hashes = shell(
            "import json,hashlib;from pathlib import Path;from urllib.parse import urlsplit\npaths="
            + repr(static_paths)
            + "\nprint('QAJSON:'+json.dumps({p:hashlib.sha256((Path('/var/lib/y3gym/static')/urlsplit(p).path.removeprefix('/static/')).read_bytes()).hexdigest() for p in paths}))"
        )
        for path in static_paths:
            served = request(path, client=public)
            assert served[0] == 200, path
            assert hashlib.sha256(served[1]).hexdigest() == static_hashes[path], path
        details["admin_referenced_static_assets"] = len(assets)
        for path in [
            "/static/.env.local",
            "/static/backend/.env.local",
            "/static/.local/qa/QA_CANARY",
            "/media/QA_CANARY",
        ]:
            assert request(path, client=public)[0] == 404
        assert (
            request(
                "/healthz/",
                headers={
                    "X-Forwarded-Proto": "http",
                    "Forwarded": "proto=http;host=evil.test",
                    "X-Forwarded-Host": "evil.test",
                },
                client=public,
            )[0]
            == 200
        )
        checks.append(
            "Required font/LICENSE/JS/CSS served; private canaries denied; HTTPS forwarded spoof overwritten"
        )
        plain_http = http.client.HTTPConnection(
            "127.0.0.1", int(values["Y3GYM_QA_HTTP_PORT"]), timeout=30
        )
        plain_http.request(
            "GET",
            "/healthz/",
            headers={
                "Host": domain,
                "X-Forwarded-Proto": "https",
                "Forwarded": "proto=https",
            },
        )
        redirected = plain_http.getresponse()
        assert redirected.status in [301, 308] and redirected.getheader(
            "Location"
        ).startswith(origin)
        redirected.read()
        plain_http.close()
        bad_host = request(
            "/healthz/", headers={"Host": "untrusted.example.invalid"}, client=public
        )[0]
        details["bad_host_status"] = bad_host
        assert bad_host in [400, 404, 421]
        csrf = BeautifulSoup(
            request("/admin/images/add/")[1], "html.parser"
        ).select_one('[name="csrfmiddlewaretoken"]')["value"]
        assert (
            request(
                "/admin/images/add/",
                urllib.parse.urlencode({"csrfmiddlewaretoken": csrf}).encode(),
                {"Origin": "https://untrusted.example.invalid", "Referer": origin},
            )[0]
            == 403
        )
        details["negative_security"] = {
            "HTTP_spoof_status": redirected.status,
            "bad_host_status": bad_host,
            "foreign_origin_POST": 403,
        }
        checks.append(
            "HTTP forwarded spoof cannot bypass HTTPS; invalid Host and foreign-origin admin POST denied"
        )
        container_ids = c("ps", "-q", capture=True).stdout.decode().split()
        runtime_state = json.loads(
            execute(
                ["docker", "container", "inspect", *container_ids], capture=True
            ).stdout
        )
        details["runtime_services"] = []
        for container in runtime_state:
            assert container["State"]["Health"]["Status"] == "healthy"
            logging = container["HostConfig"]["LogConfig"]
            assert (
                logging["Config"]["max-size"] == "10m"
                and logging["Config"]["max-file"] == "3"
            )
            details["runtime_services"].append(
                {
                    "service": container["Config"]["Labels"][
                        "com.docker.compose.service"
                    ],
                    "health": "healthy",
                    "log_rotation": True,
                }
            )
        checks.append(
            "Every live service healthy; actual Docker log rotation configured"
        )
        step = "browser"
        (run / "tmp/owned.png").write_bytes(stream.getvalue())
        (run / "browser-input.json").write_text(
            json.dumps(
                {
                    "username": credentials["username"],
                    "password": credentials["password"],
                    "upload_path": str(run / "tmp/owned.png"),
                    **fixture,
                }
            )
        )
        execute(
            [
                "docker",
                "build",
                "-t",
                project + ":browser",
                "-f",
                str(source / "deploy/Dockerfile.qa-browser"),
                "--build-arg",
                "QA_RUN_ID=" + run_id,
                "--build-arg",
                "QA_OWNER_HASH=" + manifest["owner_hash"],
                "--build-arg",
                "QA_UID=" + str(os.getuid()),
                "--build-arg",
                "QA_GID=" + str(os.getgid()),
                str(source / "deploy"),
            ]
        )
        browser_env = {
            key: os.environ[key]
            for key in [
                "Y3GYM_QA_RUN_ID",
                "Y3GYM_QA_RUN_TOKEN",
                "Y3GYM_QA_RUN_DIR",
                "Y3GYM_QA_PROJECT_ROOT",
            ]
        }
        browser_env.update(
            Y3GYM_QA_DOCKER="1",
            Y3GYM_QA_ORIGIN=origin,
            TMPDIR=str(run / "tmp"),
            NODE_OPTIONS="--import="
            + str(run / "source/backend/scripts/qa_browser_loader.mjs"),
            NODE_EXTRA_CA_CERTS=str(run / "ca.crt"),
            PLAYWRIGHT_BROWSERS_PATH="/ms-playwright",
        )
        argv = [
            "docker",
            "run",
            "--rm",
            "--name",
            project + "-browser",
            "--network",
            project + "_application",
            "--label",
            "com.docker.compose.project=" + project,
            "--label",
            "com.y3gym.qa.run=" + run_id,
            "--label",
            "com.y3gym.qa.owner=" + manifest["owner_hash"],
            "--shm-size",
            "256m",
            "--mount",
            f"type=bind,src={run},dst={run}",
            "--mount",
            f"type=bind,src={canonical / 'prototype/node_modules'},dst={canonical / 'prototype/node_modules'},readonly",
            "--mount",
            f"type=bind,src={canonical / 'backend/scripts/qa_browser_guard.mjs'},dst={canonical / 'backend/scripts/qa_browser_guard.mjs'},readonly",
        ]
        for key, value in browser_env.items():
            argv += ["-e", key]
        argv += [
            project + ":browser",
            "sh",
            "-c",
            'certutil -N --empty-password -d "sql:$HOME/.pki/nssdb" && certutil -A -d "sql:$HOME/.pki/nssdb" -n y3gym-owned-qa -t "C,," -i "$Y3GYM_QA_RUN_DIR/ca.crt" && node "$Y3GYM_QA_RUN_DIR/source/backend/scripts/docker-browser.mjs"',
        ]
        execute(argv, env={**os.environ, **browser_env})
        browser_result = json.loads(
            (run / "output/docker-browser-result.json").read_text()
        )
        assert browser_result["status"] == "PASS"
        checks.extend(browser_result["checks"])
        step = "withdrawal_and_persistence"
        assert (
            request("/news/" + str(fixture["post_id"]) + "/", client=public)[0] == 200
        )
        shell(
            "from news.models import Post,BrandContent; import json\np=Post.objects.get(pk="
            + str(fixture["post_id"])
            + ");p.unpublish();BrandContent.objects.get(pk=1).unpublish()\nprint('QAJSON:'+json.dumps({'withdrawn':True}))"
        )
        assert (
            request("/news/" + str(fixture["post_id"]) + "/", client=public)[0] == 404
        )
        assert request(fixture["rendition"], client=public)[0] == 404
        checks.append(
            "Withdrawal immediately revokes public HTML and last public image usage"
        )
        execute(
            [
                "docker",
                "build",
                "-t",
                project + ":app-next",
                "--label",
                "org.opencontainers.image.ref.name=owned-replacement",
                "--build-arg",
                "SOURCE_REVISION=" + fingerprint["revision"],
                "--build-arg",
                "SOURCE_FINGERPRINT=" + fingerprint["source_fingerprint"],
                "--build-arg",
                "QA_RUN_ID=" + run_id,
                "--build-arg",
                "QA_OWNER_HASH=" + manifest["owner_hash"],
                str(source),
            ]
        )
        values["Y3GYM_APP_IMAGE"] = project + ":app-next"
        details["replacement_image_id"] = json.loads(
            execute(
                ["docker", "image", "inspect", values["Y3GYM_APP_IMAGE"]], capture=True
            ).stdout
        )[0]["Id"]
        assert details["replacement_image_id"] != details["image_id"]
        try:
            deployment.running_release(values, project)
            raise AssertionError(
                "Backup accepted an environment image different from the running app"
            )
        except ValueError as error:
            assert "different" in str(error)
        checks.append(
            "Backup refuses a configured image different from the actually running release"
        )
        c("up", "-d", "--wait", "--force-recreate", "--no-deps", "app")
        state_code = (
            "from news.models import Post,ContentImage;from pathlib import Path;import hashlib,json\ni=ContentImage.objects.get(pk="
            + str(image_id)
            + ")\nroot=Path('/var/lib/y3gym/media')\nprint('QAJSON:'+json.dumps({'posts':Post.objects.count(),'images':ContentImage.objects.count(),'file_sha256':hashlib.sha256(i.file.read()).hexdigest(),'media':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}}))"
        )
        persisted = shell(state_code)
        assert (
            persisted["posts"] == 1
            and persisted["file_sha256"]
            == hashlib.sha256(stream.getvalue()).hexdigest()
        )
        c("stop")
        c("up", "-d", "--wait", "--wait-timeout", "90")
        assert shell(state_code) == persisted
        checks.append(
            "Application image replacement and normal stop/restart preserve own DB and private media"
        )
        step = "backup_restore"
        # Run the actual deployment backup/restore implementation with the explicit QA runner.
        envfile.write_text("\n".join(k + "=" + v for k, v in values.items()) + "\n")
        old_argv = sys.argv
        sys.argv = [
            "deploy.py",
            "--env",
            str(envfile),
            "--project",
            project,
            "backup",
            "--directory",
            str(run / "backup"),
        ]
        deployment.main()
        backup_manifest = json.loads((run / "backup/manifest.json").read_text())
        assert backup_manifest["image_id"] == details["replacement_image_id"]
        assert (
            backup_manifest["release"]["source_fingerprint"]
            == fingerprint["source_fingerprint"]
        )
        details["backup_release"] = {
            k: backup_manifest[k] for k in ["image_id", "release"]
        }
        sys.argv = [
            "deploy.py",
            "--env",
            str(envfile),
            "--project",
            project + "-restore",
            "restore",
            "--directory",
            str(run / "backup"),
            "--confirm-empty-restore",
        ]
        foreign = project + "-restore_database"
        assert (
            subprocess.run(
                ["docker", "volume", "inspect", foreign], capture_output=True
            ).returncode
            != 0
        )
        execute(
            [
                "docker",
                "volume",
                "create",
                "--label",
                "com.y3gym.qa.run=" + run_id,
                "--label",
                "com.y3gym.qa.owner=" + manifest["owner_hash"],
                "--label",
                "com.y3gym.qa.fixture=restore-collision",
                foreign,
            ],
            capture=True,
        )
        try:
            deployment.main()
            raise AssertionError("Restore adopted foreign exact-name volume")
        except ValueError as error:
            assert "volume" in str(error)
        collision = json.loads(
            execute(["docker", "volume", "inspect", foreign], capture=True).stdout
        )[0]
        assert collision["Labels"]["com.y3gym.qa.owner"] == manifest["owner_hash"]
        assert "com.docker.compose.project" not in collision["Labels"]
        execute(["docker", "volume", "rm", foreign], capture=True)
        checks.append(
            "Restore refuses an exact-name existing volume lacking Compose ownership; only owned synthetic collision fixture removed"
        )
        deployment.main()
        sys.argv = old_argv
        restored = shell(state_code, target=project + "-restore")
        assert restored == persisted
        details["restored_state"] = {
            "posts": restored["posts"],
            "images": restored["images"],
            "media_files": len(restored["media"]),
            "all_media_hashes_match": True,
        }
        checks.append(
            "Writes paused DB+original/rendition export restored into a separate empty owned deployment"
        )
        assert protected_metadata() == before
        checks.append(
            "Protected original server identities and private file metadata/bytes unchanged; no original DB-row scan"
        )
        details["scope"] = (
            "Docker production path plus browser; whole news.tests executes separately on host managed QA"
        )
        details["external_backup"] = (
            "NOT_CONFIGURED: local export/isolated restore only"
        )
        result["status"] = "PASS"
    except BaseException as error:
        result["failure"] = {"step": step, "type": type(error).__name__}
        traceback.print_exc(file=sys.stderr)
        raise
    finally:
        try:
            runtime = c("logs", "--no-color", capture=True)
            (run / "logs/runtime.log").write_bytes(runtime.stdout)
        except subprocess.CalledProcessError:
            pass
        (run / "output/docker-result.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        # The lifecycle CLI exports evidence and verifies exact labels/IDs before removing resources.
        log.close()


if __name__ == "__main__":
    os.umask(0o077)
    main()
