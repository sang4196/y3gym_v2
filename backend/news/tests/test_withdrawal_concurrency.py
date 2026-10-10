import hashlib
import json
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.db import close_old_connections, connection
from django.http import HttpResponse
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse
from wagtail import hooks

from news.models import Branch, BrandContent, ContentImage, FacilityImage, Post
from news.tests.review_fixtures import ensure_collection_root
from news.tests.test_publication import picture


class WithdrawalConcurrencyTests(TransactionTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        ensure_collection_root()
        self.user = get_user_model().objects.create_superuser(
            "withdrawal-race", password="test-password"
        )

    def edit_url(self, obj):
        return reverse(
            f"wagtailsnippets_news_{obj._meta.model_name}:edit", args=[obj.pk]
        )

    def run_race(self, model, publish=False, withdraw_first=True):
        if model is Branch:
            obj = model.objects.create(
                key="main",
                name="공개 본점",
                address="공개 주소",
                opening_hours="시간 예시",
            )
            obj.facilities = [
                FacilityImage(
                    image=picture("one.png"), title="기존 시설 1", sort_order=0
                ),
                FacilityImage(
                    image=picture("two.png"), title="기존 시설 2", sort_order=1
                ),
            ]
            field, text = "address", "보존할 새 주소"
        elif model is BrandContent:
            obj = model.objects.create(name="공개 브랜드", intro_title="공개 소개")
            field, text = "intro_text", "보존할 새 소개 본문"
        else:
            obj = model.objects.create(title="공개 소식", body="<p>기존 본문</p>")
            field, text = "body", "<p>보존할 새 소식 본문</p>"
        obj.save_revision(user=self.user).publish(user=self.user)
        obj.refresh_from_db()
        initial_content = str(getattr(obj, field))
        edit_url = self.edit_url(obj)
        withdraw_url = reverse(
            f"wagtailsnippets_news_{obj._meta.model_name}:unpublish", args=[obj.pk]
        )
        clients = {operation: Client() for operation in ["edit", "withdraw"]}
        for client in clients.values():
            client.force_login(self.user)
        if model is Branch:
            from news.tests.test_branches import BranchTests

            self.client = clients["edit"]
            payload = BranchTests.payload(self, obj)
            payload.update(
                {
                    "facilities-0-title": "보존할 시설 첫째",
                    "facilities-0-ORDER": "1",
                    "facilities-1-title": "보존할 시설 둘째",
                    "facilities-1-ORDER": "0",
                }
            )
        else:
            soup = BeautifulSoup(clients["edit"].get(edit_url).content, "html.parser")
            fields = (
                ["title", "category", "summary", "cover_image", "body"]
                if model is Post
                else [
                    "name",
                    "intro_title",
                    "intro_text",
                    "hero_alt",
                    "hero_image",
                    "logo_image",
                    "hero_position_x",
                    "hero_position_y",
                ]
            ) + ["loaded_revision_id", "loaded_revision_created_at"]
            payload = {}
            for name in fields:
                element = soup.find(attrs={"name": name})
                self.assertIsNotNone(element, name)
                if element.name == "select":
                    option = element.find("option", selected=True)
                    payload[name] = option["value"] if option else "notices"
                else:
                    payload[name] = (
                        element.text.removeprefix("\n")
                        if element.name == "textarea"
                        else element.get("value", "")
                    )
        payload[field] = text
        if model is Post:
            payload[field] = json.dumps(
                {
                    "blocks": [
                        {
                            "key": "draft",
                            "type": "unstyled",
                            "text": "보존할 새 소식 본문",
                            "depth": 0,
                            "inlineStyleRanges": [],
                            "entityRanges": [],
                            "data": {},
                        }
                    ],
                    "entityMap": {},
                }
            )
        if publish:
            payload["action-publish"] = "1"
        first = "withdraw" if withdraw_first else "edit"
        second = "edit" if withdraw_first else "withdraw"
        selected, release, second_query = Event(), Event(), Event()
        pids = {}
        view_class = resolve(
            withdraw_url if withdraw_first else edit_url
        ).func.view_class
        original = view_class.get_object

        def pause_after_select(view, queryset=None):
            instance = original(view, queryset)
            if view.request.method == "POST" and not selected.is_set():
                selected.set()
                if not release.wait(timeout=10):
                    raise TimeoutError("First request was not released")
            return instance

        def request(operation):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pids[operation] = cursor.fetchone()[0]

                def observe(execute, sql, params, many, context):
                    if operation == second and obj._meta.db_table in sql:
                        second_query.set()
                    return execute(sql, params, many, context)

                with (
                    connection.execute_wrapper(observe),
                    CaptureQueriesContext(connection) as queries,
                ):
                    response = clients[operation].post(
                        withdraw_url if operation == "withdraw" else edit_url,
                        {} if operation == "withdraw" else payload,
                    )
                return {
                    "status": response.status_code,
                    "rowLock": any(
                        obj._meta.db_table in query["sql"]
                        and "FOR UPDATE" in query["sql"]
                        for query in queries
                    ),
                }
            finally:
                close_old_connections()

        blocked = False
        with patch.object(view_class, "get_object", pause_after_select):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first_future = pool.submit(request, first)
                try:
                    self.assertTrue(selected.wait(timeout=10))
                    second_future = pool.submit(request, second)
                    self.assertTrue(second_query.wait(timeout=10))
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline and not second_future.done():
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "SELECT %s = ANY(pg_blocking_pids(%s))",
                                [pids[first], pids[second]],
                            )
                            blocked = cursor.fetchone()[0]
                        if blocked:
                            break
                        time.sleep(0.01)
                finally:
                    release.set()
                results = {
                    first: first_future.result(timeout=15),
                    second: second_future.result(timeout=15),
                }
        # A fresh ClusterableModel clears the fixture instance's in-memory child
        # list; refresh_from_db() alone does not clear modelcluster's cache.
        obj = model.objects.get(pk=obj.pk)
        newest = obj.revisions.order_by("pk").last()
        draft = obj.get_latest_revision_as_object()
        facility_titles = (
            [item.title for item in draft.facilities.all()] if model is Branch else None
        )
        result = {
            "model": model.__name__,
            "publish": publish,
            "first": first,
            "secondBlockedByFirst": blocked,
            "requests": results,
            "latestRevision": obj.latest_revision_id,
            "newestRevision": newest.pk,
            "live": obj.live,
            "liveRevision": obj.live_revision_id,
            "currentContent": str(getattr(obj, field)),
            "draftContent": str(getattr(draft, field)),
            "facilityTitles": facility_titles,
            "isolatedTestDatabase": True,
        }
        evidence = os.environ.get("Y3GYM_WITHDRAWAL_REVIEW_DIR")
        if evidence:
            output = Path(evidence)
            output.mkdir(parents=True, exist_ok=True)
            name = f"{model._meta.model_name}-{'publish' if publish else 'draft'}-{first}-first.json"
            with (output / name).open("x") as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
        self.assertTrue(blocked, result)
        self.assertTrue(all(item["rowLock"] for item in results.values()), result)
        self.assertEqual(
            [item["status"] for item in results.values()], [302, 302], result
        )
        self.assertEqual(obj.latest_revision_id, newest.pk, result)
        # Saving a draft while live keeps the model row's published content;
        # Wagtail stores the new content/children in latest_revision instead.
        expected_current = text if publish or withdraw_first else initial_content
        self.assertEqual(str(getattr(obj, field)), expected_current, result)
        self.assertEqual(str(getattr(draft, field)), text, result)
        self.assertEqual(obj.live, publish and withdraw_first, result)
        self.assertEqual(obj.live_revision_id, newest.pk if obj.live else None, result)
        self.assertEqual(obj.revisions.count(), 2, result)
        if model is Branch:
            self.assertEqual(
                facility_titles, ["보존할 시설 둘째", "보존할 시설 첫째"], result
            )
            expected_children = (
                facility_titles
                if publish or withdraw_first
                else ["기존 시설 1", "기존 시설 2"]
            )
            self.assertEqual(
                [item.title for item in obj.facilities.all()], expected_children, result
            )
        if obj.live:
            self.assertEqual(
                str(getattr(obj.live_revision.as_object(), field)), text, result
            )

    def test_branch_withdraw_then_draft(self):
        self.run_race(Branch)

    def test_brand_withdraw_then_draft(self):
        self.run_race(BrandContent)

    def test_post_withdraw_then_draft(self):
        self.run_race(Post)

    def test_branch_draft_then_withdraw(self):
        self.run_race(Branch, withdraw_first=False)

    def test_brand_draft_then_withdraw(self):
        self.run_race(BrandContent, withdraw_first=False)

    def test_post_draft_then_withdraw(self):
        self.run_race(Post, withdraw_first=False)

    def test_branch_withdraw_then_publish(self):
        self.run_race(Branch, publish=True)

    def test_brand_withdraw_then_publish(self):
        self.run_race(BrandContent, publish=True)

    def test_post_withdraw_then_publish(self):
        self.run_race(Post, publish=True)

    def test_branch_publish_then_withdraw(self):
        self.run_race(Branch, publish=True, withdraw_first=False)

    def test_brand_publish_then_withdraw(self):
        self.run_race(BrandContent, publish=True, withdraw_first=False)

    def test_post_publish_then_withdraw(self):
        self.run_race(Post, publish=True, withdraw_first=False)


class WithdrawalBoundaryTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        ensure_collection_root()
        self.admin = get_user_model().objects.create_superuser(
            "withdraw-boundaries", password="test-password"
        )
        self.editor = get_user_model().objects.create_user(
            "without-publish", password="test-password", is_staff=True
        )
        self.editor.user_permissions.add(
            Permission.objects.get(
                codename="access_admin", content_type__app_label="wagtailadmin"
            )
        )
        self.editor.user_permissions.add(
            *Permission.objects.filter(
                codename__in=[
                    "view_branch",
                    "change_branch",
                    "view_brandcontent",
                    "change_brandcontent",
                    "view_post",
                    "change_post",
                ]
            )
        )

    def objects(self):
        objects = [
            Branch.objects.create(
                key="main", name="본점", address="주소", opening_hours="시간"
            ),
            BrandContent.objects.create(name="브랜드", intro_title="소개"),
            Post.objects.create(title="소식", body="<p>권한 보호 본문</p>"),
        ]
        for obj in objects:
            image = picture(obj._meta.model_name + "-permission.png")
            if isinstance(obj, Branch):
                obj.facilities = [
                    FacilityImage(image=image, title="권한 보호 시설", sort_order=0)
                ]
            elif isinstance(obj, BrandContent):
                obj.hero_image = image
            else:
                obj.cover_image = image
            obj.save()
            obj.save_revision().publish()
            obj.refresh_from_db()
            yield (
                obj,
                reverse(
                    f"wagtailsnippets_news_{obj._meta.model_name}:unpublish",
                    args=[obj.pk],
                ),
            )

    def test_all_withdrawal_routes_keep_permission_csrf_and_get_boundaries(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.admin)
        evidence = []

        def snapshot(instance):
            current = type(instance).objects.get(pk=instance.pk)
            state = {
                "rowAndFacilities": current.serializable_data(),
                "latestRevisionContent": current.latest_revision.content,
                "revisionCount": current.revisions.count(),
                "images": list(
                    ContentImage.objects.order_by("pk").values("id", "file")
                ),
            }
            return hashlib.sha256(
                json.dumps(state, sort_keys=True, default=str).encode()
            ).hexdigest()

        for obj, url in self.objects():
            with self.subTest(model=type(obj).__name__):
                self.assertTrue(
                    self.client.login(
                        username="without-publish", password="test-password"
                    )
                )
                self.assertEqual(self.client.get("/admin/").status_code, 200)
                self.assertFalse(
                    self.editor.has_perm(f"news.publish_{obj._meta.model_name}")
                )
                # Wagtail's outer permission decorator redirects normal denied
                # requests home; AJAX requests receive an actual HTTP 403.
                before = snapshot(obj)
                denied = self.client.post(url)
                self.assertEqual(denied.status_code, 302)
                self.assertEqual(denied.headers["Location"], "/admin/")
                messages = [
                    str(message) for message in get_messages(denied.wsgi_request)
                ]
                self.assertTrue(
                    any(
                        "권한" in message or "permission" in message.lower()
                        for message in messages
                    ),
                    messages,
                )
                ajax = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
                self.assertEqual(
                    ajax.status_code,
                    403,
                )
                obj.refresh_from_db()
                self.assertTrue(obj.live)
                self.assertEqual(obj.latest_revision_id, obj.live_revision_id)
                csrf_response = csrf.post(url)
                self.assertEqual(csrf_response.status_code, 403)
                after = snapshot(obj)
                self.assertEqual(after, before)
                evidence.append(
                    {
                        "model": type(obj).__name__,
                        "passwordLogin": True,
                        "administratorHome": 200,
                        "publishPermission": False,
                        "normalDeniedStatus": denied.status_code,
                        "location": denied.headers["Location"],
                        "denialMessages": messages,
                        "ajaxStatus": ajax.status_code,
                        "csrfStatus": csrf_response.status_code,
                        "contentRevisionFacilitiesAndImageHashBefore": before,
                        "contentRevisionFacilitiesAndImageHashAfter": after,
                    }
                )
                self.client.force_login(self.admin)
                with CaptureQueriesContext(connection) as queries:
                    self.assertEqual(self.client.get(url).status_code, 200)
                self.assertFalse(
                    any(
                        obj._meta.db_table in item["sql"]
                        and "FOR UPDATE" in item["sql"]
                        for item in queries
                    )
                )
                obj.refresh_from_db()
                self.assertTrue(obj.live)
                self.assertEqual(self.client.post(url).status_code, 302)
                obj.refresh_from_db()
                self.assertFalse(obj.live)
                missing = reverse(
                    f"wagtailsnippets_news_{obj._meta.model_name}:unpublish",
                    args=[99999],
                )
                self.assertEqual(self.client.post(missing).status_code, 404)
        output = os.environ.get("Y3GYM_WITHDRAWAL_REVIEW_DIR")
        if output:
            Path(output).mkdir(parents=True, exist_ok=True)
            with (Path(output) / "boundary-permissions.json").open("x") as handle:
                json.dump(
                    {
                        "status": "PASS",
                        "checks": evidence,
                        "isolatedTestDatabase": True,
                    },
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )

    def test_all_withdrawal_routes_keep_before_after_and_cancel_hooks(self):
        self.client.force_login(self.admin)
        calls = []

        def before(request, instance):
            calls.append(("before", type(instance).__name__, instance.live))

        def after(request, instance):
            calls.append(("after", type(instance).__name__, instance.live))

        def cancel(request, instance):
            return HttpResponse("철회 보류", status=409)

        for obj, url in self.objects():
            with self.subTest(model=type(obj).__name__):
                calls.clear()
                with (
                    hooks.register_temporarily("before_unpublish", before),
                    hooks.register_temporarily("after_unpublish", after),
                ):
                    self.assertEqual(self.client.post(url).status_code, 302)
                self.assertEqual(
                    calls,
                    [
                        ("before", type(obj).__name__, True),
                        ("after", type(obj).__name__, False),
                    ],
                )
                obj.refresh_from_db()
                obj.get_latest_revision().publish()
                with hooks.register_temporarily("before_unpublish", cancel):
                    self.assertEqual(self.client.post(url).status_code, 409)
                obj.refresh_from_db()
                self.assertTrue(obj.live)
