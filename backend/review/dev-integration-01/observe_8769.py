"""Future basic connection check, without browser JS, edits, or server restart."""

import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
INSTANCE = Path("/tmp/y3gym-kakao-map-iq9yoy7v")


def observe(work):
    os.umask(0o077)
    work = work.resolve()
    assert work.parent == Path("/tmp") and work.name.startswith(
        "y3gym-dev-integration-"
    )
    assert work.stat().st_mode & 0o777 == 0o700
    private = work / "current-8769"
    private.mkdir()  # No overwrite of a previous observation.
    spec = json.loads((INSTANCE / "instance.json").read_text())
    assert spec["scratch"] == str(INSTANCE)
    assert spec["database"] == "test_y3gym_kakao_map_6a8c1ada2d3b"
    assert spec["origin"] == "http://localhost:8769" and spec["port"] == 8769
    assert spec["media"] == str(INSTANCE / "media")
    os.environ.update(
        DJANGO_SETTINGS_MODULE="map_review_settings",
        Y3GYM_KAKAO_MAP_JS_KEY="",
        PGOPTIONS="-c default_transaction_read_only=on",
    )
    sys.path[:0] = [str(INSTANCE), str(BACKEND)]
    import django

    django.setup()
    from bs4 import BeautifulSoup
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.db import connection, transaction
    from wagtail.images.formats import get_image_format
    from wagtail.images.models import Filter
    from wagtail.users.models import UserProfile

    from news.models import ContentImage
    from news.popups import eligible_popups
    from news.publication import (
        published_branches,
        published_brand,
        published_posts,
        published_trainers,
    )

    assert settings.DATABASES["default"]["NAME"] == spec["database"]
    assert settings.DATABASES["default"]["TEST"]["NAME"] == spec["test_database"]
    assert spec["test_database"] == spec["database"] + "_runner"
    assert settings.DATABASES["default"]["HOST"] == "127.0.0.1"
    assert str(settings.DATABASES["default"]["PORT"]) == "55438"
    assert Path(settings.MEDIA_ROOT).resolve() == INSTANCE / "media"
    assert Path(settings.BASE_DIR).resolve() == INSTANCE
    assert (
        settings.WAGTAILADMIN_BASE_URL == spec["origin"]
        and not settings.KAKAO_MAP_JS_KEY
    )
    # These copied functions have no module-level apply/restart actions.
    namespace = dict(
        globals(),
        PRIVATE=private,
        SPEC=spec,
        connection=connection,
        transaction=transaction,
        hashlib=hashlib,
        re=re,
        subprocess=subprocess,
    )
    exec(
        compile(
            (work / "snapshot_functions.py").read_text(),
            "copied-read-only-snapshot-functions",
            "exec",
        ),
        namespace,
    )
    guard, snapshot, save = [namespace[name] for name in ("guard", "snapshot", "save")]
    before_guard = guard()
    metadata = namespace["metadata"]()
    before = snapshot()
    save("before.json", before)
    save("metadata-before.json", metadata)
    results = []
    report = {
        "status": "BLOCKED",
        "requests": results,
        "browser_js_external_calls": 0,
        "restart": False,
        "restoration": False,
    }
    cookies = SimpleCookie()
    session_key = None
    user_id = None
    try:
        # Read current public revisions, including every gallery/profile rendered
        # by these routes. find_existing_rendition never generates missing files.
        required = set()

        def need(image, filter_spec):
            if image:
                required.add((image.pk, filter_spec))

        brand = published_brand()
        if brand:
            need(brand.logo_image, "max-360x64")
            need(brand.hero_image, "max-1536x1536")
        branches = published_branches()
        for branch in branches:
            for photo in branch.facilities.all():
                need(photo.image, "max-1536x1536")
        for trainer in published_trainers():
            need(trainer.photo, "fill-640x800")
        posts = published_posts()
        popups = list(eligible_popups())
        for popup in popups:
            need(popup.post.live_revision.as_object().cover_image, "width-800")
        selected = next(
            (post for post in posts if any(p.post_id == post.pk for p in popups)),
            posts[0] if posts else None,
        )
        if selected:
            need(selected.cover_image, "width-1200")
            for embed in BeautifulSoup(str(selected.body), "html.parser").select(
                'embed[embedtype="image"]'
            ):
                image = ContentImage.objects.get(pk=int(embed["id"]))
                need(image, get_image_format(embed["format"]).filter_spec)
        for image_id, filter_spec in sorted(required):
            rendition = ContentImage.objects.get(pk=image_id).find_existing_rendition(
                Filter(filter_spec)
            )
            assert rendition.file.storage.exists(rendition.file.name), (
                "Existing rendition file missing; BLOCK GET"
            )
        report["renditions_preflighted"] = len(required)

        def request(method, path, data=None, auth=False):
            assert path.startswith("/") and not path.startswith("//")
            headers = {"Connection": "close"}
            if auth:
                headers["Cookie"] = "; ".join(
                    f"{key}={value.value}" for key, value in cookies.items()
                )
            if data is not None:
                headers.update(
                    {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Referer": spec["origin"] + "/admin/login/",
                    }
                )
                data = urlencode(data)
            client = http.client.HTTPConnection("localhost", 8769, timeout=15)
            try:
                client.request(method, path, body=data, headers=headers)
                response = client.getresponse()
                body = response.read()
                if auth:
                    for key, value in response.getheaders():
                        if key.lower() == "set-cookie":
                            cookies.load(value)
                location = response.getheader("Location")
                if location:
                    target = urlsplit(location)
                    assert not target.netloc or target.netloc == "localhost:8769", (
                        "External redirect blocked"
                    )
                results.append(
                    {"method": method, "path": path, "status": response.status}
                )
                return response.status, body, location
            finally:
                client.close()

        paths = ["/", "/branches/", "/news/"]
        if selected:
            paths.append(selected.get_absolute_url())
        else:
            report["linked_article"] = "NOT_PRESENT"
        for path in paths:
            assert request("GET", path)[0] == 200
        status, body, _ = request("GET", "/admin/login/", auth=True)
        assert status == 200
        csrf = BeautifulSoup(body, "html.parser").select_one(
            'input[name="csrfmiddlewaretoken"]'
        )["value"]
        credentials = json.loads((INSTANCE / ".local-credentials").read_text())
        username = "cms-review-editor"
        user_id = get_user_model().objects.get(username=username).pk
        status, _, location = request(
            "POST",
            "/admin/login/",
            {
                "username": username,
                "password": credentials[username],
                "csrfmiddlewaretoken": csrf,
                "next": "/admin/",
            },
            auth=True,
        )
        del credentials
        assert status == 302 and location == "/admin/"
        session_key = cookies[settings.SESSION_COOKIE_NAME].value
        for path in [
            "/admin/",
            "/admin/snippets/news/post/",
            "/admin/snippets/news/branch/",
            "/admin/snippets/news/trainer/",
        ]:
            assert request("GET", path, auth=True)[0] == 200
        report["status"] = "OBSERVED_AWAITING_PRESERVATION"
    except Exception as error:
        # No body, token, credentials, SQL rows, or traceback in the public summary.
        report["failure_type"] = type(error).__name__
    finally:
        after = snapshot()
        save("after.json", after)
        report["metadata_unchanged"] = namespace["metadata"]() == metadata
        report["same_server_pid"] = guard()["pid"] == before_guard["pid"]
        report["media_unchanged"] = before["media"] == after["media"]
        changes = []
        allowed_profile = False
        for table in sorted(set(before["tables"]) | set(after["tables"])):
            old, new = before["tables"].get(table, []), after["tables"].get(table, [])
            if old == new:
                continue
            rows_old, rows_new = (
                [json.loads(row) for row in old],
                [json.loads(row) for row in new],
            )
            permitted = False
            if table == "auth_user" and user_id:

                def strip_login(rows):
                    return [
                        {
                            k: v
                            for k, v in row.items()
                            if not (row["id"] == user_id and k == "last_login")
                        }
                        for row in rows
                    ]

                permitted = strip_login(rows_old) == strip_login(rows_new)
            elif table == "django_session" and session_key:
                permitted = rows_old == [
                    row for row in rows_new if row["session_key"] != session_key
                ] and not any(row["session_key"] == session_key for row in rows_old)
            elif table == "wagtailusers_userprofile" and user_id:
                additions = [row for row in rows_new if row not in rows_old]
                if (
                    len(additions) == 1
                    and all(row in rows_new for row in rows_old)
                    and not any(row["user_id"] == user_id for row in rows_old)
                ):
                    row = additions[0]
                    defaults = {
                        field.column: field.get_default()
                        for field in UserProfile._meta.concrete_fields
                        if field.column not in {"id", "user_id"}
                    }
                    permitted = (
                        row["user_id"] == user_id
                        and {k: v for k, v in row.items() if k not in {"id", "user_id"}}
                        == defaults
                    )
                    allowed_profile = permitted
            changes.append({"table": table, "permitted_login_metadata": permitted})
        schema_old, schema_new = before["schema"], after["schema"]
        sequence_ok = schema_old["sequences"] == schema_new["sequences"]
        if allowed_profile and not sequence_ok:
            old = {row[0]: row for row in schema_old["sequences"]}
            new = {row[0]: row for row in schema_new["sequences"]}
            name = "wagtailusers_userprofile_id_seq"
            sequence_ok = (
                old.keys() == new.keys()
                and all(old[key] == new[key] for key in old if key != name)
                and old[name][:-1] == new[name][:-1]
                and new[name][-1] == (old[name][-1] or 0) + 1
            )
        schema_ok = (
            all(
                schema_old[key] == schema_new[key]
                for key in schema_old
                if key != "sequences"
            )
            and sequence_ok
        )
        report.update(
            table_changes=changes,
            schema_sequences_preserved_or_precise_profile_increment=schema_ok,
        )
        preservation_ok = (
            all(row["permitted_login_metadata"] for row in changes)
            and schema_ok
            and report["metadata_unchanged"]
            and report["same_server_pid"]
            and report["media_unchanged"]
        )
        if report["status"] == "OBSERVED_AWAITING_PRESERVATION" and preservation_ok:
            report["status"] = "PASS_BASIC_CONNECTION_ONLY"
        elif not preservation_ok:
            report["status"] = "FAIL_PRESERVATION_NO_RESTORE"
        save("summary.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        connection.close()


if __name__ == "__main__":
    assert len(sys.argv) == 3 and sys.argv[2] == "--execute", (
        "Test-role execution authorization required"
    )
    observe(Path(sys.argv[1]))
