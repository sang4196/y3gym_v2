"""Independent HTTP / PostgreSQL lock and media verification; isolated DB only."""
# ruff: noqa: E402

import hashlib
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.db import close_old_connections, connection
from django.http import HttpResponse
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext, get_runner
from django.urls import resolve, reverse
from wagtail import hooks

from news.models import Branch, BrandContent, FacilityImage, Post
from news.publication import published_image_ids
from news.tests.review_fixtures import ensure_collection_root
from news.tests.test_publication import picture

OUTPUT = Path(__file__).resolve().parent / "independent-concurrency"


def record(name, value):
    OUTPUT.mkdir(exist_ok=True)
    with (OUTPUT / f"{name}.json").open("x") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def route(obj, action):
    return reverse(
        f"wagtailsnippets_news_{obj._meta.model_name}:{action}", args=[obj.pk]
    )


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


class Setup:
    def prepare(self):
        self.assertTrue(connection.settings_dict["NAME"].startswith("test_"))
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        ensure_collection_root()
        self.admin = get_user_model().objects.create_superuser(
            "independent-r1", password="test-password"
        )

    def make(self, model):
        self.images = [
            picture(f"independent-{i}.png", color=color)
            for i, color in enumerate(["navy", "red", "green"])
        ]
        first, second, _ = self.images
        if model is Branch:
            obj = model.objects.create(
                key="main",
                name="독립 본점",
                address="이전 주소",
                opening_hours="예시 시간",
            )
            obj.facilities = [
                FacilityImage(image=first, title="이전 하나", sort_order=0),
                FacilityImage(image=second, title="이전 둘", sort_order=1),
            ]
        elif model is BrandContent:
            obj = model.objects.create(
                name="독립 브랜드",
                intro_title="소개",
                intro_text="이전 설명",
                hero_image=first,
                logo_image=second,
            )
        else:
            obj = model.objects.create(
                title="독립 소식", body="<p>이전 본문</p>", cover_image=first
            )
        obj.save_revision(user=self.admin).publish(user=self.admin)
        return model.objects.get(pk=obj.pk)

    def payload(self, client, obj):
        response = client.get(route(obj, "edit"))
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        result = {}
        for element in soup.select("input[name], textarea[name], select[name]"):
            kind = element.get("type", "")
            if kind in {"file", "submit", "button"} or (
                kind in {"checkbox", "radio"} and not element.has_attr("checked")
            ):
                continue
            if element.name == "select":
                selected = element.find("option", selected=True) or element.find(
                    "option"
                )
                result[element["name"]] = selected.get("value", "") if selected else ""
            else:
                result[element["name"]] = (
                    element.text.removeprefix("\n")
                    if element.name == "textarea"
                    else element.get("value", "")
                )
        if isinstance(obj, Branch):
            result.update(
                address="독립 새 주소",
                **{
                    "facilities-0-title": "독립 새 하나",
                    "facilities-0-image": str(self.images[2].pk),
                    "facilities-0-ORDER": "1",
                    "facilities-1-title": "독립 새 둘",
                    "facilities-1-ORDER": "0",
                },
            )
        elif isinstance(obj, BrandContent):
            result.update(intro_text="독립 새 설명", hero_image=str(self.images[2].pk))
        else:
            result.update(
                cover_image=str(self.images[2].pk),
                body=json.dumps(
                    {
                        "blocks": [
                            {
                                "key": "r1",
                                "type": "unstyled",
                                "text": "독립 새 본문",
                                "depth": 0,
                                "inlineStyleRanges": [],
                                "entityRanges": [],
                                "data": {},
                            }
                        ],
                        "entityMap": {},
                    }
                ),
            )
        return result

    def content(self, obj):
        if isinstance(obj, Branch):
            return {
                "address": obj.address,
                "facilities": [(f.title, f.image_id) for f in obj.facilities.all()],
            }
        if isinstance(obj, BrandContent):
            return {
                "text": obj.intro_text,
                "hero": obj.hero_image_id,
                "logo": obj.logo_image_id,
            }
        return {"body": str(obj.body), "cover": obj.cover_image_id}

    def expected(self, obj):
        if isinstance(obj, Branch):
            return {
                "address": "독립 새 주소",
                "facilities": [
                    ("독립 새 둘", self.images[1].pk),
                    ("독립 새 하나", self.images[2].pk),
                ],
            }
        if isinstance(obj, BrandContent):
            return {
                "text": "독립 새 설명",
                "hero": self.images[2].pk,
                "logo": self.images[1].pk,
            }
        return {"body": "<p>독립 새 본문</p>", "cover": self.images[2].pk}

    def image_hashes(self):
        return {
            image.pk: hashlib.sha256(Path(image.file.path).read_bytes()).hexdigest()
            for image in self.images
        }


class IndependentRaces(Setup, TransactionTestCase):
    def setUp(self):
        self.prepare()

    def check_race(self, model, publish, first):
        obj = self.make(model)
        old_content = self.content(obj)
        hashes = self.image_hashes()
        clients = {key: Client() for key in ["save", "withdraw"]}
        for client in clients.values():
            self.assertTrue(
                client.login(username="independent-r1", password="test-password")
            )
        payload = self.payload(clients["save"], obj)
        if publish:
            payload["action-publish"] = "1"
        second = "withdraw" if first == "save" else "save"
        first_selected, release, attempted = Event(), Event(), Event()
        pids = {}
        view_class = resolve(
            route(obj, "edit" if first == "save" else "unpublish")
        ).func.view_class
        original = view_class.get_object

        def pause(view, queryset=None):
            value = original(view, queryset)
            if view.request.method == "POST" and not first_selected.is_set():
                first_selected.set()
                if not release.wait(12):
                    raise TimeoutError("Independent synchronization timed out")
            return value

        def request(operation):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pids[operation] = cursor.fetchone()[0]

                def observe(execute, sql, params, many, context):
                    if operation == second and obj._meta.db_table in sql:
                        attempted.set()
                    return execute(sql, params, many, context)

                with (
                    connection.execute_wrapper(observe),
                    CaptureQueriesContext(connection) as queries,
                ):
                    response = clients[operation].post(
                        route(obj, "edit" if operation == "save" else "unpublish"),
                        payload if operation == "save" else {},
                    )
                return {
                    "status": response.status_code,
                    "location": response.get("Location"),
                    "row_lock": any(
                        obj._meta.db_table in q["sql"] and "FOR UPDATE" in q["sql"]
                        for q in queries
                    ),
                }
            finally:
                close_old_connections()

        blocked = False
        with (
            patch.object(view_class, "get_object", pause),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            one = pool.submit(request, first)
            try:
                self.assertTrue(first_selected.wait(12))
                two = pool.submit(request, second)
                self.assertTrue(attempted.wait(12))
                deadline = time.monotonic() + 4
                while time.monotonic() < deadline and not two.done():
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT %s = ANY(pg_blocking_pids(%s))",
                            [pids[first], pids[second]],
                        )
                        blocked = cursor.fetchone()[0]
                    if blocked:
                        break
                    time.sleep(0.015)
            finally:
                release.set()
            requests = {first: one.result(timeout=20), second: two.result(timeout=20)}
        current = model.objects.get(pk=obj.pk)
        newest = current.revisions.order_by("pk").last()
        latest = current.get_latest_revision_as_object()
        public_ids = published_image_ids()
        expected_live = publish and first == "withdraw"
        expected_ids = (
            (
                {self.images[2].pk}
                | ({self.images[1].pk} if model is not Post else set())
            )
            if expected_live
            else set()
        )
        anonymous = Client()
        media_status = {}
        for image in self.images:
            rendition = image.get_rendition("width-40")
            media_status[image.pk] = anonymous.get(rendition.url).status_code
            self.assertEqual(
                media_status[image.pk], 200 if image.pk in expected_ids else 404
            )
            self.assertEqual(anonymous.get(image.file.url).status_code, 404)
        result = {
            "model": model.__name__,
            "publish": publish,
            "first": first,
            "second": second,
            "actual_blocker_confirmed": blocked,
            "requests": requests,
            "latest_revision": current.latest_revision_id,
            "newest_revision": newest.pk,
            "revision_count": current.revisions.count(),
            "live": current.live,
            "live_revision": current.live_revision_id,
            "current": self.content(current),
            "latest": self.content(latest),
            "expected_latest": self.expected(obj),
            "published_image_ids": sorted(public_ids),
            "rendition_status": media_status,
            "original_images_unchanged": hashes == self.image_hashes(),
            "isolated_test_database": True,
        }
        record(
            f"{model._meta.model_name}-{'publish' if publish else 'draft'}-{first}-first",
            result,
        )
        self.assertTrue(blocked, result)
        self.assertTrue(all(r["row_lock"] for r in requests.values()), result)
        self.assertEqual([r["status"] for r in requests.values()], [302, 302], result)
        self.assertEqual(current.latest_revision_id, newest.pk, result)
        self.assertEqual(current.revisions.count(), 2, result)
        self.assertEqual(self.content(latest), self.expected(obj), result)
        self.assertEqual(
            self.content(current),
            self.expected(obj) if publish or first == "withdraw" else old_content,
            result,
        )
        self.assertEqual(current.live, expected_live, result)
        self.assertEqual(
            current.live_revision_id, newest.pk if expected_live else None, result
        )
        self.assertEqual(public_ids, expected_ids, result)
        self.assertEqual(hashes, self.image_hashes(), result)


for model in [Branch, BrandContent, Post]:
    for publish in [False, True]:
        for first in ["save", "withdraw"]:

            def test(self, model=model, publish=publish, first=first):
                self.check_race(model, publish, first)

            setattr(
                IndependentRaces,
                f"test_{model._meta.model_name}_{'publish' if publish else 'draft'}_{first}_first",
                test,
            )


class IndependentBoundaries(Setup, TestCase):
    def setUp(self):
        self.prepare()

    def test_authenticated_restrictions_get_404_and_cancel_for_all_models(self):
        editor = get_user_model().objects.create_user(
            "r1-restricted", password="test-password", is_staff=True
        )
        editor.user_permissions.add(
            Permission.objects.get(
                codename="access_admin", content_type__app_label="wagtailadmin"
            ),
            *Permission.objects.filter(
                content_type__app_label="news",
                codename__in=[
                    "view_post",
                    "change_post",
                    "view_brandcontent",
                    "change_brandcontent",
                    "view_branch",
                    "change_branch",
                ],
            ),
        )
        restricted = Client()
        self.assertTrue(
            restricted.login(username="r1-restricted", password="test-password")
        )
        self.assertEqual(restricted.get("/admin/").status_code, 200)
        admin, csrf = Client(), Client(enforce_csrf_checks=True)
        for client in [admin, csrf]:
            self.assertTrue(
                client.login(username="independent-r1", password="test-password")
            )
        rows = []
        for model in [Branch, BrandContent, Post]:
            obj = self.make(model)
            url = route(obj, "unpublish")

            def state():
                fresh = model.objects.get(pk=obj.pk)
                return digest(
                    {
                        "row": fresh.serializable_data(),
                        "latest": fresh.latest_revision.content,
                        "revisions": list(fresh.revisions.values_list("pk", flat=True)),
                        "images": self.image_hashes(),
                    }
                )

            before = state()
            self.assertFalse(editor.has_perm(f"news.publish_{obj._meta.model_name}"))
            response = restricted.post(url)
            messages = [str(m) for m in get_messages(response.wsgi_request)]
            ajax = restricted.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
            csrf_response = csrf.post(url)
            self.assertEqual(
                (response.status_code, response.get("Location")), (302, "/admin/")
            )
            self.assertTrue(
                any("권한" in m or "permission" in m.lower() for m in messages)
            )
            self.assertEqual((ajax.status_code, csrf_response.status_code), (403, 403))
            with CaptureQueriesContext(connection) as queries:
                self.assertEqual(admin.get(url).status_code, 200)
            self.assertFalse(
                any(
                    "FOR UPDATE" in q["sql"] and obj._meta.db_table in q["sql"]
                    for q in queries
                )
            )
            self.assertEqual(
                admin.post(url.replace(f"/{obj.pk}/", "/999999/")).status_code, 404
            )
            calls = []

            def cancel(request, instance):
                calls.append(("before", instance.live))
                return HttpResponse("Independent cancellation", status=409)

            def after(request, instance):
                calls.append(("after", instance.live))

            with (
                hooks.register_temporarily("before_unpublish", cancel),
                hooks.register_temporarily("after_unpublish", after),
            ):
                self.assertEqual(admin.post(url).status_code, 409)
            self.assertEqual(calls, [("before", True)])
            self.assertEqual(state(), before)
            calls.clear()

            def accept(request, instance):
                calls.append(("before", instance.live))

            with (
                hooks.register_temporarily("before_unpublish", accept),
                hooks.register_temporarily("after_unpublish", after),
            ):
                success = admin.post(url)
            self.assertEqual(success.status_code, 302)
            self.assertNotEqual(success.get("Location"), "/admin/")
            self.assertEqual(calls, [("before", True), ("after", False)])
            obj.refresh_from_db()
            self.assertFalse(obj.live)
            rows.append(
                {
                    "model": model.__name__,
                    "real_password_login": True,
                    "normal_denied": response.status_code,
                    "location": response.get("Location"),
                    "messages": messages,
                    "ajax": ajax.status_code,
                    "csrf": csrf_response.status_code,
                    "get_has_no_lock": True,
                    "missing": 404,
                    "cancel_preserves_all_state": True,
                    "before_after_order": calls,
                    "success_location": success.get("Location"),
                }
            )
        record("independent-boundaries", {"status": "PASS", "models": rows})


if __name__ == "__main__":
    raise SystemExit(
        bool(
            get_runner(django.conf.settings)(verbosity=2, interactive=False).run_tests(
                ["__main__"]
            )
        )
    )
