"""Independent trainer boundaries and real concurrent HTTP requests, test DB only."""
# ruff: noqa: E402

import hashlib
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.db import close_old_connections, connection
from django.test import (
    Client,
    RequestFactory,
    TestCase,
    TransactionTestCase,
    override_settings,
)
from django.test.utils import CaptureQueriesContext, get_runner
from django.urls import resolve, reverse
from django.utils import timezone

from news.models import (
    Branch,
    BrandContent,
    FacilityImage,
    Post,
    Trainer,
    TrainerBiography,
)
from news.publication import published_image_ids, published_trainers
from news.tests.review_fixtures import ensure_collection_root
from news.tests.test_publication import picture
from news.tests.test_trainers import TrainerTests

OUTPUT = Path(__file__).resolve().parent / "additional"


def record(name, data):
    OUTPUT.mkdir(exist_ok=True)
    with (OUTPUT / f"{name}.json").open("x") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


class Setup:
    def setUp(self):
        self.assertTrue(connection.settings_dict["NAME"].startswith("test_"))
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        ensure_collection_root()
        self.admin = get_user_model().objects.create_superuser(
            "independent-trainer", password="test-password"
        )
        self.branches = []
        for key in ["main", "second"]:
            branch = Branch.objects.create(
                key=key,
                name="独立 " + key,
                address="PUBLIC " + key,
                opening_hours="PUBLIC HOURS",
                phone="예시 문의",
            )
            branch.save_revision().publish()
            self.branches.append(Branch.objects.get(pk=branch.pk))
        self.images = [
            picture(f"trainer-independent-{i}.png", color=color)
            for i, color in enumerate(["red", "green"])
        ]
        self.trainer = Trainer.objects.create(
            name="공개 이름",
            branch=self.branches[0],
            display_order=4,
            photo=self.images[0],
            intro="공개 소개",
            position="공개 직급",
        )
        self.trainer.biography = [
            TrainerBiography(text="공개 약력 하나", sort_order=0),
            TrainerBiography(text="공개 약력 둘", sort_order=1),
        ]
        self.trainer.save_revision().publish()
        self.trainer = Trainer.objects.get(pk=self.trainer.pk)
        self.assertTrue(
            self.client.login(username="independent-trainer", password="test-password")
        )

    def edit_url(self, trainer):
        return reverse("wagtailsnippets_news_trainer:edit", args=[trainer.pk])

    def url(self, action="unpublish"):
        return reverse(f"wagtailsnippets_news_trainer:{action}", args=[self.trainer.pk])

    def payload(self):
        data = TrainerTests.payload(self, self.trainer)
        data.update(
            name="독립 새 이름",
            branch=str(self.branches[1].pk),
            display_order="1",
            photo=str(self.images[1].pk),
            intro="독립 새 소개",
            position="독립 새 직급",
        )
        data.update(
            {
                "biography-0-text": "독립 새 약력",
                "biography-0-ORDER": "0",
                "biography-1-DELETE": "on",
            }
        )
        return data

    def state(self, trainer):
        return {
            "name": trainer.name,
            "branch": trainer.branch_id,
            "order": trainer.display_order,
            "photo": trainer.photo_id,
            "intro": trainer.intro,
            "position": trainer.position,
            "biography": [b.text for b in trainer.biography.all()],
        }

    def expected(self):
        return {
            "name": "독립 새 이름",
            "branch": self.branches[1].pk,
            "order": 1,
            "photo": self.images[1].pk,
            "intro": "독립 새 소개",
            "position": "독립 새 직급",
            "biography": ["독립 새 약력"],
        }

    def hashes(self):
        return {
            image.pk: hashlib.sha256(Path(image.file.path).read_bytes()).hexdigest()
            for image in self.images
        }

    def snapshot(self):
        t = Trainer.objects.get(pk=self.trainer.pk)
        return {
            "content": t.serializable_data(),
            "latest": t.latest_revision_id,
            "live": t.live_revision_id,
            "revisions": list(t.revisions.values_list("pk", "content")),
            "images": self.hashes(),
        }


class Boundaries(Setup, TestCase):
    def test_same_live_snapshot_and_move_publish_for_authenticated_and_anonymous(self):
        old = self.state(self.trainer)
        response = self.client.post(self.edit_url(self.trainer), self.payload())
        self.assertEqual(response.status_code, 302)
        # Corrupt mutable rows only in the test DB to distinguish snapshot reads.
        Trainer.objects.filter(pk=self.trainer.pk).update(
            name="MUTABLE SECRET",
            branch=self.branches[1],
            display_order=88,
            photo=self.images[1],
            intro="MUTABLE INTRO",
            position="MUTABLE POSITION",
        )
        TrainerBiography.objects.filter(trainer=self.trainer).delete()
        for client in [Client(), self.client]:
            soup = BeautifulSoup(
                client.get("/branches/?branch=main").content, "html.parser"
            )
            card = soup.select_one(
                f'#branch-main [data-trainer-id="{self.trainer.pk}"]'
            )
            self.assertIsNotNone(card)
            self.assertEqual(card.select_one("h4").text, old["name"])
            self.assertEqual([li.text for li in card.select("li")], old["biography"])
            self.assertIn(old["intro"], card.text)
            self.assertIn(old["position"], card.text)
            self.assertIsNone(
                soup.select_one(f'#branch-second [data-trainer-id="{self.trainer.pk}"]')
            )
            self.assertNotIn("MUTABLE", str(soup))
            self.assertNotIn("독립 새", str(soup))
        current = Trainer.objects.get(pk=self.trainer.pk)
        self.assertEqual(self.state(published_trainers()[0]), old)
        current.get_latest_revision().publish()
        self.assertEqual(Trainer.objects.count(), 1)
        self.assertEqual(self.state(published_trainers()[0]), self.expected())
        soup = BeautifulSoup(Client().get("/branches/").content, "html.parser")
        self.assertIsNone(
            soup.select_one(f'#branch-main [data-trainer-id="{current.pk}"]')
        )
        self.assertIsNotNone(
            soup.select_one(f'#branch-second [data-trainer-id="{current.pk}"]')
        )
        record(
            "snapshot-and-move",
            {
                "status": "PASS",
                "same_profile_id": current.pk,
                "public_snapshot": old,
                "published_move": self.expected(),
                "authenticated_customer_url_matches": True,
            },
        )

    def test_preview_excludes_private_and_public_branch_drafts(self):
        request = RequestFactory().get("/admin/preview/")
        request.user = self.admin
        draft = self.trainer.get_latest_revision_as_object()
        draft.name = "PREVIEW PROFILE"
        for private in [False, True]:
            branch = self.branches[0].get_latest_revision_as_object()
            branch.address, branch.opening_hours = "SECRET ADDRESS", "SECRET HOURS"
            branch.facilities = [
                FacilityImage(title="SECRET FACILITY", image=self.images[1])
            ]
            branch.save_revision()
            if private:
                self.branches[0].unpublish()
            response = draft.serve_preview(request, "")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Cache-Control"], "private, no-store")
            self.assertContains(response, "PREVIEW PROFILE")
            for secret in ["SECRET ADDRESS", "SECRET HOURS", "SECRET FACILITY"]:
                self.assertNotContains(response, secret)
            if not private:
                self.assertContains(response, "PUBLIC main")
        draft.branch = None
        self.assertContains(draft.serve_preview(request, ""), "소속 지점 미선택")
        self.assertTrue(Trainer.objects.get(pk=draft.pk).live)
        record(
            "preview-branch-isolation",
            {
                "status": "PASS",
                "public_branch_uses_live_only": True,
                "private_and_unspecified_affiliation_only_profile": True,
                "cache_control": "private, no-store",
            },
        )

    def test_media_dual_publication_move_and_shared_last_use(self):
        anonymous = Client()
        old, new = self.images
        renditions = [image.get_rendition("fill-640x800") for image in self.images]
        hidden_thumb = new.get_rendition("max-165x165")
        self.assertEqual(anonymous.get(renditions[0].url).status_code, 200)
        self.assertEqual(anonymous.get(old.file.url).status_code, 404)
        self.assertEqual(
            self.client.post(self.edit_url(self.trainer), self.payload()).status_code,
            302,
        )
        self.assertEqual(anonymous.get(renditions[1].url).status_code, 404)
        self.assertEqual(anonymous.get(hidden_thumb.url).status_code, 404)
        self.branches[1].unpublish()
        trainer = Trainer.objects.get(pk=self.trainer.pk)
        trainer.get_latest_revision().publish()
        self.assertTrue(Trainer.objects.get(pk=trainer.pk).live)
        self.assertEqual(published_trainers(), [])
        self.assertEqual(anonymous.get(renditions[0].url).status_code, 404)
        self.assertEqual(anonymous.get(renditions[1].url).status_code, 404)
        self.branches[1].get_latest_revision().publish()
        self.assertEqual(anonymous.get(renditions[1].url).status_code, 200)
        post = Post.objects.create(title="공유", cover_image=new)
        post.save_revision().publish()
        brand = BrandContent.objects.create(
            name="공유", intro_title="공유", hero_image=new
        )
        brand.save_revision().publish()
        branch = self.branches[0].get_latest_revision_as_object()
        branch.facilities = [FacilityImage(image=new, title="공유")]
        branch.save_revision().publish()
        trainer = Trainer.objects.get(pk=trainer.pk)
        trainer.unpublish()
        post = Post.objects.get(pk=post.pk)
        post.unpublish()
        brand = BrandContent.objects.get(pk=brand.pk)
        brand.unpublish()
        self.assertEqual(anonymous.get(renditions[1].url).status_code, 200)
        branch = Branch.objects.get(pk=branch.pk)
        branch.unpublish()
        self.assertEqual(anonymous.get(renditions[1].url).status_code, 404)
        self.assertEqual(anonymous.get(new.file.url).status_code, 404)
        self.assertEqual(self.client.get(hidden_thumb.url).status_code, 200)
        record(
            "media-boundaries",
            {
                "status": "PASS",
                "dual_publication": True,
                "draft_and_original_and_private_thumbnail_denied": True,
                "move_to_private_revokes_old_and_new": True,
                "shared_brand_post_facility_last_use": True,
            },
        )

    def test_individual_required_fields_draft_save_and_entry(self):
        for update in [{"name": " \t\n "}, {"branch": ""}]:
            before = self.snapshot()
            payload = self.payload()
            payload.update(update)
            payload["action-publish"] = "1"
            response = self.client.post(self.edit_url(self.trainer), payload)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "독립 새 소개")
            self.assertEqual(self.snapshot(), before)
        add = reverse("wagtailsnippets_news_trainer:add")
        for branch in self.branches:
            soup = BeautifulSoup(
                self.client.get(add + f"?branch={branch.pk}").content, "html.parser"
            )
            self.assertEqual(soup.select_one("#id_branch")["value"], str(branch.pk))
        entry = reverse("wagtailsnippets_news_branch:add")
        self.assertContains(self.client.get(entry), "먼저 지점을 초안 저장")
        payload = self.payload()
        payload.update(name="", branch="", intro="보존할 미완성")
        self.assertEqual(
            self.client.post(self.edit_url(self.trainer), payload).status_code, 302
        )
        t = Trainer.objects.get(pk=self.trainer.pk)
        self.assertEqual(t.get_latest_revision_as_object().intro, "보존할 미완성")
        self.assertEqual(published_trainers()[0].name, "공개 이름")
        record(
            "required-and-entry",
            {
                "status": "PASS",
                "each_required_field_individually_rejected": True,
                "incomplete_draft_allowed": True,
                "both_branch_initial_values": True,
            },
        )

    def test_real_restricted_login_get_csrf_delete_stale_and_lock(self):
        editor = get_user_model().objects.create_user(
            "trainer-change-only", password="test-password", is_staff=True
        )
        editor.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["access_admin", "view_trainer", "change_trainer"]
            )
        )
        restricted = Client()
        self.assertTrue(
            restricted.login(username="trainer-change-only", password="test-password")
        )
        self.assertEqual(restricted.get("/admin/").status_code, 200)
        before = self.snapshot()
        denied = restricted.post(self.url())
        messages = [str(m) for m in get_messages(denied.wsgi_request)]
        self.assertEqual((denied.status_code, denied.get("Location")), (302, "/admin/"))
        self.assertTrue(any("권한" in m or "permission" in m.lower() for m in messages))
        self.assertEqual(
            restricted.post(
                self.url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
            ).status_code,
            403,
        )
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.admin)
        self.assertEqual(csrf.post(self.url()).status_code, 403)
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.assertFalse(
            any(
                "news_trainer" in q["sql"] and "FOR UPDATE" in q["sql"] for q in queries
            )
        )
        delete = self.client.post(self.url("delete"))
        self.assertEqual((delete.status_code, delete.get("Location")), (302, "/admin/"))
        self.assertEqual(self.snapshot(), before)
        stale = self.payload()
        self.assertEqual(
            self.client.post(self.edit_url(self.trainer), stale).status_code, 302
        )
        latest_state = self.snapshot()
        rejected = self.client.post(self.edit_url(self.trainer), stale)
        self.assertContains(rejected, "다른 화면에서 더 최근 내용")
        self.assertEqual(self.snapshot(), latest_state)
        Trainer.objects.filter(pk=self.trainer.pk).update(
            locked=True, locked_by=editor, locked_at=timezone.now()
        )
        locked_before = self.snapshot()
        rejected = self.client.post(self.edit_url(self.trainer), self.payload())
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(self.snapshot(), locked_before)
        record(
            "permissions-and-stale",
            {
                "status": "PASS",
                "real_password_login": True,
                "denied_location": denied.get("Location"),
                "denial_messages": messages,
                "ajax": 403,
                "csrf": 403,
                "get_unlocked_unchanged": True,
                "delete_denied_even_for_admin": True,
                "stale_and_locked_preserve_all_fields_children_images": True,
            },
        )


class Races(Setup, TransactionTestCase):
    def withdrawal_race(self, publish, first):
        second = "withdraw" if first == "save" else "save"
        payload, hashes = self.payload(), self.hashes()
        if publish:
            payload["action-publish"] = "1"
        clients = {operation: Client() for operation in ["save", "withdraw"]}
        for client in clients.values():
            self.assertTrue(
                client.login(username="independent-trainer", password="test-password")
            )
        selected, release, attempted = Event(), Event(), Event()
        pids = {}
        klass = resolve(
            self.edit_url(self.trainer) if first == "save" else self.url()
        ).func.view_class
        original = klass.get_object

        def pause(view, queryset=None):
            instance = original(view, queryset)
            if view.request.method == "POST" and not selected.is_set():
                selected.set()
                if not release.wait(12):
                    raise TimeoutError("Independent request synchronization")
            return instance

        def request(operation):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pids[operation] = cursor.fetchone()[0]

                def observe(execute, sql, params, many, context):
                    if operation == second and '"news_trainer"' in sql:
                        attempted.set()
                    return execute(sql, params, many, context)

                with (
                    connection.execute_wrapper(observe),
                    CaptureQueriesContext(connection) as queries,
                ):
                    response = clients[operation].post(
                        self.edit_url(self.trainer)
                        if operation == "save"
                        else self.url(),
                        payload if operation == "save" else {},
                    )
                return {
                    "status": response.status_code,
                    "lock": any(
                        '"news_trainer"' in q["sql"] and "FOR UPDATE" in q["sql"]
                        for q in queries
                    ),
                }
            finally:
                close_old_connections()

        blocked = False
        with (
            patch.object(klass, "get_object", pause),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            one = pool.submit(request, first)
            try:
                self.assertTrue(selected.wait(12))
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
                    time.sleep(0.01)
            finally:
                release.set()
            results = {first: one.result(timeout=20), second: two.result(timeout=20)}
        t = Trainer.objects.get(pk=self.trainer.pk)
        latest, newest = (
            t.get_latest_revision_as_object(),
            t.revisions.order_by("pk").last(),
        )
        expected_live = publish and first == "withdraw"
        row = {
            "publish": publish,
            "first": first,
            "actual_blocking": blocked,
            "requests": results,
            "latest": t.latest_revision_id,
            "newest": newest.pk,
            "state": self.state(latest),
            "live": t.live,
            "live_revision": t.live_revision_id,
            "images_unchanged": hashes == self.hashes(),
        }
        record(f"race-{'publish' if publish else 'draft'}-{first}-first", row)
        self.assertTrue(blocked, row)
        self.assertTrue(all(r["lock"] for r in results.values()), row)
        self.assertEqual([r["status"] for r in results.values()], [302, 302], row)
        self.assertEqual(t.latest_revision_id, newest.pk, row)
        self.assertEqual(t.revisions.count(), 2, row)
        self.assertEqual(self.state(latest), self.expected(), row)
        self.assertEqual(t.live, expected_live, row)
        self.assertEqual(t.live_revision_id, newest.pk if expected_live else None, row)
        self.assertEqual(
            published_image_ids(), {self.images[1].pk} if expected_live else set(), row
        )
        self.assertEqual(hashes, self.hashes(), row)

    def save_race(self, publish):
        clients, payloads = [Client(), Client()], []
        for number, client in enumerate(clients):
            self.assertTrue(
                client.login(username="independent-trainer", password="test-password")
            )
            payload = self.payload()
            payload.update(
                name=f"동시 독립 {number}",
                branch=str(self.branches[number].pk),
                display_order=str(number),
                photo=str(self.images[number].pk),
                intro=f"짝 소개 {number}",
                position=f"짝 직급 {number}",
            )
            payload["biography-0-text"] = f"짝 약력 {number}"
            if publish:
                payload["action-publish"] = "1"
            payloads.append(payload)
        barrier = Barrier(2)

        def request(number):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                r = clients[number].post(self.edit_url(self.trainer), payloads[number])
                return {
                    "status": r.status_code,
                    "conflict": "더 최근 내용" in r.content.decode(),
                }
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(request, [0, 1]))
        t = Trainer.objects.get(pk=self.trainer.pk)
        latest = t.get_latest_revision_as_object()
        number = int(latest.name[-1])
        expected = {
            "name": f"동시 독립 {number}",
            "branch": self.branches[number].pk,
            "order": number,
            "photo": self.images[number].pk,
            "intro": f"짝 소개 {number}",
            "position": f"짝 직급 {number}",
            "biography": [f"짝 약력 {number}"],
        }
        row = {
            "publish": publish,
            "requests": results,
            "winner": number,
            "latest_state": self.state(latest),
            "expected": expected,
            "revisions": t.revisions.count(),
        }
        record(f"simultaneous-{'publish' if publish else 'draft'}", row)
        self.assertEqual(sorted(r["status"] for r in results), [200, 302], row)
        self.assertEqual(sum(r["conflict"] for r in results), 1, row)
        self.assertEqual(t.revisions.count(), 2, row)
        self.assertEqual(self.state(latest), expected, row)
        self.assertEqual(
            t.latest_revision_id, t.revisions.order_by("pk").last().pk, row
        )
        self.assertEqual(
            published_trainers()[0].name,
            expected["name"] if publish else "공개 이름",
            row,
        )

    def test_simultaneous_drafts(self):
        self.save_race(False)

    def test_simultaneous_publications(self):
        self.save_race(True)


for publish in [False, True]:
    for first in ["save", "withdraw"]:

        def test(self, publish=publish, first=first):
            self.withdrawal_race(publish, first)

        setattr(Races, f"test_{'publish' if publish else 'draft'}_{first}_first", test)


if __name__ == "__main__":
    raise SystemExit(
        bool(
            get_runner(settings)(verbosity=2, interactive=False).run_tests(["__main__"])
        )
    )
