"""Read-only protection and minimal delivery checks for the approved 8769."""

import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import django

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
INSTANCE = Path("/tmp/y3gym-kakao-map-iq9yoy7v")
PRIVATE = Path(sys.argv[1]).resolve()
assert PRIVATE.parent == Path("/tmp")
assert PRIVATE.name.startswith("y3gym-image-focus-apply-")
assert PRIVATE.stat().st_mode & 0o777 == 0o700
SPEC = json.loads((INSTANCE / "instance.json").read_text())
assert SPEC["scratch"] == str(INSTANCE)
assert SPEC["database"] == "test_y3gym_kakao_map_6a8c1ada2d3b"
assert SPEC["origin"] == "http://localhost:8769" and SPEC["port"] == 8769
assert SPEC["media"] == str(INSTANCE / "media")
os.environ["DJANGO_SETTINGS_MODULE"] = "map_review_settings"
os.environ["Y3GYM_KAKAO_MAP_JS_KEY"] = ""  # Only this observer has a blank key.
sys.path[:0] = [str(INSTANCE), str(BACKEND)]
django.setup()
from django.conf import settings  # noqa: E402
from django.db import connection, transaction  # noqa: E402

assert settings.DATABASES["default"]["NAME"] == SPEC["database"]
assert settings.DATABASES["default"]["TEST"]["NAME"] == SPEC["test_database"]
assert SPEC["test_database"].startswith("test_y3gym_kakao_map_")
assert SPEC["test_database"] != SPEC["database"]
assert settings.DATABASES["default"]["HOST"] == "127.0.0.1"
assert str(settings.DATABASES["default"]["PORT"]) == "55438"
assert Path(settings.MEDIA_ROOT).resolve() == INSTANCE / "media"
assert Path(settings.BASE_DIR).resolve() == INSTANCE
assert settings.WAGTAILADMIN_BASE_URL == SPEC["origin"]
assert not settings.KAKAO_MAP_JS_KEY


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with os.fdopen(
        os.open(PRIVATE / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
    ) as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True)


def stat(path):
    s = path.lstat()
    return {
        "size": s.st_size,
        "mode": s.st_mode,
        "mtime_ns": s.st_mtime_ns,
        "inode": s.st_ino,
    }


def metadata():
    assert not INSTANCE.is_symlink() and not (INSTANCE / "media").is_symlink()
    result = {}
    for name in [
        "instance.json",
        "map_review_settings.py",
        ".local-credentials",
        "kakao-map-js-key",
    ]:
        p = INSTANCE / name
        assert p.is_file() and not p.is_symlink()
        result[name] = stat(p)
        if name in [".local-credentials", "kakao-map-js-key"]:
            assert p.stat().st_mode & 0o777 == 0o600
        else:
            result[name]["sha256"] = digest(p)
    return result


def guard():
    pid = int((INSTANCE / "server.pid").read_text())
    proc = Path(f"/proc/{pid}")
    assert (proc / "cwd").resolve() == BACKEND
    argv = (proc / "cmdline").read_bytes().split(b"\0")
    assert b"manage.py" in argv and b"127.0.0.1:8769" in argv
    assert b"runserver" in argv and b"--noreload" in argv
    environment = dict(
        v.split(b"=", 1)
        for v in (proc / "environ").read_bytes().split(b"\0")
        if b"=" in v
    )
    assert environment[b"DJANGO_SETTINGS_MODULE"] == b"map_review_settings"
    assert str(INSTANCE).encode() in environment[b"PYTHONPATH"].split(b":")
    assert str(BACKEND).encode() in environment[b"PYTHONPATH"].split(b":")
    # Values stay in memory; key/credential files are observed by stat only.
    key = environment[b"Y3GYM_KAKAO_MAP_JS_KEY"]
    assert re.fullmatch(rb"[0-9a-fA-F]{32}", key)
    assert not any(key in arg for arg in argv)
    listeners = subprocess.check_output(["ss", "-ltnp", "sport = :8769"], text=True)
    assert f"pid={pid}," in listeners
    return {
        "pid": pid,
        "origin": SPEC["origin"],
        "database": SPEC["database"],
        "test_database": SPEC["test_database"],
        "media": SPEC["media"],
        "cwd_argv_settings_pythonpath_match": True,
        "actual_server_key_present": True,
        "key_values_logged": False,
        "key_credentials_stat_only": True,
        "observer_key_blank": True,
    }


def media_inventory():
    result = {}
    for p in sorted((INSTANCE / "media").rglob("*")):
        assert not p.is_symlink()
        if p.is_file():
            result[str(p.relative_to(INSTANCE / "media"))] = {
                **stat(p),
                "sha256": digest(p),
            }
    return result


def snapshot():
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            cursor.execute("SELECT current_database()")
            assert cursor.fetchone()[0] == SPEC["database"]
            tables = {}
            for table in connection.introspection.table_names(cursor):
                cursor.execute(
                    f"SELECT to_jsonb(t)::text FROM {connection.ops.quote_name(table)} t"
                )
                tables[table] = sorted(row[0] for row in cursor.fetchall())
            queries = {
                "columns": "SELECT table_name,column_name,data_type,udt_name,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position",
                "indexes": "SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname",
                "sequences": "SELECT sequencename,data_type,start_value,min_value,max_value,increment_by,cycle,cache_size,last_value FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename",
                "constraints": "SELECT c.relname,k.conname,k.contype,pg_get_constraintdef(k.oid,true) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY c.relname,k.conname",
                "views": "SELECT viewname,definition FROM pg_views WHERE schemaname='public' ORDER BY viewname",
            }
            schema = {}
            for name, query in queries.items():
                cursor.execute(query)
                schema[name] = cursor.fetchall()
    return json.loads(
        json.dumps(
            {
                "database": SPEC["database"],
                "tables": tables,
                "schema": schema,
                "media": media_inventory(),
            }
        )
    )


def summary(value):
    tables = value["tables"]
    return {
        "tables": len(tables),
        "logical_rows": sum(len(r) for r in tables.values()),
        "revisions": len(tables["wagtailcore_revision"]),
        "branches": len(tables["news_branch"]),
        "images": len(tables["news_contentimage"]),
        "media_files": len(value["media"]),
    }


def unchanged():
    current = snapshot()
    assert current == json.loads((PRIVATE / "before.json").read_text()), (
        "Current user data changed; never restore"
    )
    assert metadata() == json.loads((PRIVATE / "metadata-before.json").read_text())
    return current


def loader():
    from wagtail import hooks
    from news import wagtail_hooks

    script = BACKEND / "news/static/news/admin-image-chooser-focus.js"
    approved = json.loads(
        (
            ROOT / "backend/review/image-chooser-focus-independent/served-script.json"
        ).read_text()
    )
    assert digest(script) == approved["served_sha256"]
    registered = hooks.get_hooks("insert_global_admin_js")
    hook = wagtail_hooks.preserve_image_chooser_focus
    assert sum(f is hook for f in registered) == 1
    assert Path(wagtail_hooks.__file__).resolve() == BACKEND / "news/wagtail_hooks.py"
    output = str(hook())
    assert output == '<script src="/static/news/admin-image-chooser-focus.js"></script>'
    return {
        "fresh_observer_registration_count": 1,
        "hook_origin_matches_project": True,
        "hook_module_sha256": digest(Path(wagtail_hooks.__file__)),
        "project_script_sha256": digest(script),
        "matches_independent_approved_script": True,
        "observer_key_blank": True,
        "server_internal_cache_inspected": False,
    }


def http_read():
    results = []
    for path in ["/admin/login/", "/static/news/admin-image-chooser-focus.js"]:
        client = http.client.HTTPConnection("localhost", 8769, timeout=10)
        client.request("GET", path, headers={"Connection": "close"})
        response = client.getresponse()
        body = response.read()
        assert response.status == 200
        row = {"path": path, "status": response.status}
        if path.endswith(".js"):
            sha = hashlib.sha256(body).hexdigest()
            assert sha == digest(
                BACKEND / "news/static/news/admin-image-chooser-focus.js"
            )
            row.update(bytes=len(body), sha256=sha, project_bytes_match=True)
        else:
            assert b'name="username"' in body and b'name="password"' in body
            row["login_form_present"] = True
        results.append(row)
        client.close()
    return {
        "requests": results,
        "anonymous_GET_only": True,
        "cookies_sent_or_saved": False,
        "redirects_or_login_POST": False,
        "browser_JS_or_external_calls": 0,
        "response_bodies_logged": False,
        "authenticated_admin_UI_checked": False,
    }


action = sys.argv[2]
if action == "before":
    evidence = {"guard": guard(), "metadata": metadata()}
    value = snapshot()
    save("before.json", value)
    save("metadata-before.json", evidence["metadata"])
    evidence["summary"] = summary(value)
    evidence["loader"] = loader()
    save("before-evidence.json", evidence)
elif action == "stopped":
    pid = json.loads((PRIVATE / "before-evidence.json").read_text())["guard"]["pid"]
    assert not Path(f"/proc/{pid}").exists()
    assert (
        len(
            subprocess.check_output(
                ["ss", "-ltnp", "sport = :8769"], text=True
            ).splitlines()
        )
        == 1
    )
    evidence = {
        "old_pid": pid,
        "stopped": True,
        "unchanged": True,
        "summary": summary(unchanged()),
    }
    save("stopped-evidence.json", evidence)
elif action == "delivery":
    state = guard()
    unchanged()
    evidence = {"guard": state, "loader": loader(), "HTTP": http_read()}
    save("delivery-evidence.json", evidence)
elif action == "after":
    state = guard()
    value = unchanged()
    save("after.json", value)
    evidence = {
        "guard": state,
        "summary": summary(value),
        "all_logical_rows_schema_sequences_unchanged": True,
        "revision_accounts_sessions_contacts_raw_JSON_unchanged": True,
        "media_hashes_and_metadata_unchanged": True,
        "settings_key_credentials_metadata_unchanged": True,
        "migrate_collectstatic_restore_reseed_admin_POST": False,
    }
    save("after-evidence.json", evidence)
else:
    raise ValueError("before, stopped, delivery or after")
print(
    json.dumps(
        {
            "stage": action,
            "status": "PASS",
            "summary": evidence.get("summary"),
            "pid": evidence.get("guard", {}).get("pid"),
        },
        ensure_ascii=False,
    )
)
