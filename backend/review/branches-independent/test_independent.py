"""Additional checks in Django's isolated test database and temporary media."""
# ruff: noqa: E402

import json
import os
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.test.utils import get_runner
from django.urls import reverse
from django.utils import timezone

from news.models import Branch, FacilityImage, PopupSetting, Post
from news.publication import published_branches
from news.tests import test_branches


class IndependentBoundaries(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            "independent-admin", password="test-password"
        )
        self.branch = Branch.objects.create(
            key="main", name="공개 본점", address="공개 주소", opening_hours="공개 시간"
        )
        self.branch.save_revision().publish()
        self.branch.refresh_from_db()
        self.client.force_login(self.admin)

    def edit_url(self, branch):
        return reverse("wagtailsnippets_news_branch:edit", args=[branch.pk])

    def test_each_whitespace_required_field_blocks_admin_publish(self):
        for field in ["name", "address", "opening_hours"]:
            with self.subTest(field=field):
                payload = test_branches.BranchTests.payload(self, self.branch)
                payload.update({field: " \t\n ", "action-publish": "1"})
                old_live = self.branch.live_revision_id
                response = self.client.post(self.edit_url(self.branch), payload)
                self.assertContains(response, "공개하려면 입력해 주세요.")
                self.branch.refresh_from_db()
                self.assertEqual(self.branch.live_revision_id, old_live)
                self.assertEqual(published_branches()[0].address, "공개 주소")

    def test_unpublish_requires_publish_permission_and_csrf(self):
        url = reverse("wagtailsnippets_news_branch:unpublish", args=[self.branch.pk])
        editor = get_user_model().objects.create_user("change-only")
        editor.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["access_admin", "view_branch", "change_branch"]
            )
        )
        restricted = Client()
        restricted.force_login(editor)
        self.assertIn(restricted.post(url).status_code, [302, 403])
        self.branch.refresh_from_db()
        self.assertTrue(self.branch.live)
        guarded = Client(enforce_csrf_checks=True)
        guarded.force_login(self.admin)
        self.assertEqual(guarded.post(url).status_code, 403)
        self.branch.refresh_from_db()
        self.assertTrue(self.branch.live)

    def test_no_public_branch_keeps_popup_and_news_without_inquiry(self):
        post = Post.objects.create(title="공통 소식", live=False)
        post.save_revision().publish()
        PopupSetting.objects.create(
            post=post,
            enabled=True,
            starts_at=timezone.now() - timedelta(hours=1),
            ends_at=timezone.now() + timedelta(hours=1),
        )
        self.branch.unpublish()
        for route in [
            "/",
            "/branches/",
            "/news/",
            f"/news/{post.pk}/",
            f"/popups/{post.pk}/",
        ]:
            with self.subTest(route=route):
                response = self.client.get(route, {"branch": "main"})
                self.assertEqual(response.status_code, 200)
                self.assertIn("no-store", response["Cache-Control"])
                soup = BeautifulSoup(response.content, "html.parser")
                self.assertTrue(
                    all(
                        control.has_attr("hidden")
                        for control in soup.select("[data-inquiry]")
                    )
                )
                metadata = json.loads(soup.select_one("#branch-navigation-data").text)
                self.assertEqual(metadata, [])


class IndependentMobileAndContext(StaticLiveServerTestCase):
    def test_mobile_admin_and_third_branch_popup_context(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with override_settings(BASE_DIR=base, MEDIA_ROOT=base / "media"):
                call_command("bootstrap_review", verbosity=0)
                call_command("bootstrap_brand_review", verbosity=0)
                call_command("bootstrap_branch_review", verbosity=0)
                branch = Branch.objects.create(
                    key="third-independent",
                    name="독립 검수 세번째 지점",
                    address="세번째 임시 주소",
                    opening_hours="세번째 임시 시간",
                    phone="세번째 모의 전화",
                )
                branch.facilities = [
                    FacilityImage(
                        image=Branch.objects.get(key="main").facilities.first().image,
                        title="세번째 사진",
                    )
                ]
                branch.save_revision().publish()
                post = Post.objects.create(title="독립 검수 공통 팝업", live=False)
                post.save_revision().publish()
                PopupSetting.objects.create(
                    post=post,
                    enabled=True,
                    starts_at=timezone.now() - timedelta(hours=1),
                    ends_at=timezone.now() + timedelta(hours=1),
                )
                environment = os.environ.copy()
                environment.update(
                    Y3GYM_INDEPENDENT_ORIGIN=self.live_server_url,
                    Y3GYM_INDEPENDENT_PASSWORD=json.loads(
                        (base / ".local-credentials").read_text()
                    )["cms-review-editor"],
                    Y3GYM_INDEPENDENT_MAIN_PK=str(Branch.objects.get(key="main").pk),
                    Y3GYM_INDEPENDENT_POST_PK=str(post.pk),
                )
                result = subprocess.run(
                    ["node", "review/branches-independent/probe-mobile.mjs"],
                    cwd=settings.PROTOTYPE_DIR.parent / "backend",
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=240,
                )
                print(result.stdout)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    failures = get_runner(settings)(verbosity=2, interactive=False).run_tests(
        ["__main__"]
    )
    raise SystemExit(bool(failures))
