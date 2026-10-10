"""Independent manifests and actual CMS HTTP lifecycle, isolated test DB only."""
# ruff: noqa: E402

import copy
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from datetime import timezone as utc
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import get_runner
from django.urls import reverse
from django.utils import timezone

from news.home import render_home
from news.models import Branch, BrandContent, PopupSetting, Post
from news.tests import test_publication as fixture
from news.tests.review_fixtures import ensure_collection_root

OUTPUT = Path(__file__).resolve().parent


class HomeSemantics(TestCase):
    def setUp(self):
        self.assertTrue(connection.settings_dict["NAME"].startswith("test_"))
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        ensure_collection_root()
        self.user = get_user_model().objects.create_superuser(
            "independent-home", password="test-password"
        )
        self.assertTrue(
            self.client.login(username="independent-home", password="test-password")
        )
        session = self.client.session
        session.set_expiry(400 * 86400)
        session.save()
        self.visitor = Client()
        self.base = datetime(2026, 9, 1, 16, 30, tzinfo=utc.utc)
        self.branches = []
        for key in ["main", "second"]:
            branch = Branch.objects.create(
                key=key,
                name="검수 " + key,
                address="임시 주소",
                opening_hours="임시 시간",
            )
            branch.save_revision().publish()
            self.branches.append(branch)
        self.manifest = {}
        self.observations = []

    def make(self, index, day, **values):
        values = {
            "title": f"PUBLIC {index}",
            "category": "notices",
            "summary": f"SUMMARY {index}",
            "body": f"<p>BODY {index}</p>",
            **values,
        }
        post = Post.objects.create(live=False, **values)
        with patch(
            "django.utils.timezone.now",
            return_value=self.base - timedelta(days=30) + timedelta(minutes=index),
        ):
            revision = post.save_revision()
        date = self.base + timedelta(days=day)
        with patch("django.utils.timezone.now", return_value=date):
            revision.publish()
        post.refresh_from_db()
        self.assertEqual(post.first_published_at, date)
        self.manifest[post.pk] = {
            "id": post.pk,
            "title": values["title"],
            "category": values["category"],
            "summary": values["summary"],
            "body": values["body"],
            "cover_image": values.get("cover_image").pk
            if values.get("cover_image")
            else None,
            "first": date,
            "live": True,
        }
        return post

    def expected(self):
        return sorted(
            [p for p in self.manifest.values() if p["live"]],
            key=lambda p: (-p["first"].timestamp(), p["id"]),
        )

    def rows(self, response, home):
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        items = []
        for row in soup.select(
            "#news .news-item" if home else ".news-index .news-item"
        ):
            link = row.select_one(".news-title-link")
            summary = row.select_one(".news-copy p")
            items.append(
                {
                    "id": int(urlsplit(link["href"]).path.strip("/").split("/")[-1]),
                    "title": link.get_text(),
                    "summary": summary.get_text() if summary else "",
                    "category": row.select_one(".news-category").get_text(),
                    "date": row.select_one("time")["datetime"],
                }
            )
        return soup, items

    def check_public(self, label, client=None):
        client = client or self.visitor
        expected = [
            {
                "id": p["id"],
                "title": p["title"],
                "summary": p["summary"],
                "category": {"notices": "공지", "events": "이벤트"}[p["category"]],
                "date": p["first"]
                .astimezone(ZoneInfo("Asia/Seoul"))
                .strftime("%Y-%m-%d"),
            }
            for p in self.expected()
        ]
        home, actual = self.rows(client.get("/?branch=second"), True)
        _, listing = self.rows(client.get("/news/?branch=second"), False)
        self.assertEqual(actual, expected[:5])
        self.assertEqual(listing, expected)
        self.observations.append(
            {
                "phase": label,
                "expected_ids_from_manifest": [p["id"] for p in expected],
                "home_ids": [p["id"] for p in actual],
                "list_ids": [p["id"] for p in listing],
            }
        )
        return home

    def record(self, name, **data):
        folder = OUTPUT / os.environ.get("Y3GYM_HOME_AUDIT_RESULTS", "semantics")
        folder.mkdir(exist_ok=True)
        with (folder / f"{name}.json").open("x") as handle:
            json.dump(
                {
                    "status": "PASS",
                    "isolated_test_database": True,
                    "observations": self.observations,
                    **data,
                },
                handle,
                ensure_ascii=False,
                default=str,
                indent=2,
            )

    def test_independent_order_manifest_and_all_popup_targets_beyond_home_five(self):
        posts = [
            self.make(index, day) for index, day in enumerate([2, 7, 3, 7, 5, 1, 6, 4])
        ]
        now = timezone.now()
        for post in posts:
            PopupSetting.objects.create(
                post=post,
                enabled=True,
                starts_at=now - timedelta(hours=1),
                ends_at=now + timedelta(hours=1),
            )
        draft = Post.objects.create(title="NEVER PUBLIC", live=False)
        draft.save_revision()
        broken = Post.objects.create(title="NO LIVE REVISION", live=True)
        for post in [draft, broken]:
            PopupSetting.objects.create(
                post=post,
                enabled=True,
                starts_at=now - timedelta(hours=1),
                ends_at=now + timedelta(hours=1),
            )
        home = self.check_public("eight_deliberately_shuffled_first_publications")
        popup = json.loads(home.select_one("#home-popup-data").string)
        self.assertEqual([int(p["postId"]) for p in popup], [p.pk for p in posts])
        excluded = set(self.manifest) - {p["id"] for p in self.expected()[:5]}
        self.assertEqual(len(excluded), 3)
        for pk in excluded:
            response = self.visitor.get(f"/popups/{pk}/data/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["post"]["id"], str(pk))
        self.record(
            "order-and-popup",
            manifest=copy.deepcopy(self.manifest),
            home_limit=5,
            popup_count=8,
            popup_ids_registration_order=[p.pk for p in posts],
            excluded_home_ids_still_popup_targets=sorted(excluded),
        )

    def test_actual_cms_draft_publish_withdraw_republish_preserves_first_rank_and_all_fields(
        self,
    ):
        old, new = (
            fixture.picture("independent-home-old.png"),
            fixture.picture("independent-home-draft.png", "green"),
        )
        files = {
            p.pk: hashlib.sha256(Path(p.file.path).read_bytes()).hexdigest()
            for p in [old, new]
        }
        posts = [
            self.make(index, day, **({"cover_image": old} if index == 4 else {}))
            for index, day in enumerate([2, 7, 3, 7, 5, 1, 6, 4])
        ]
        target = posts[4]
        url = reverse("wagtailsnippets_news_post:edit", args=[target.pk])
        baseline = copy.deepcopy(Post.objects.get(pk=target.pk).live_revision.content)
        body = json.dumps(
            {
                "entityMap": {},
                "blocks": [
                    {
                        "key": "audit",
                        "text": "DRAFT BODY INDEPENDENT",
                        "type": "unstyled",
                        "depth": 0,
                        "inlineStyleRanges": [],
                        "entityRanges": [],
                    }
                ],
            }
        )

        def submit(publish=False):
            data = fixture.PublicationTests.editor_payload(self, target)
            data.update(
                title="DRAFT TITLE INDEPENDENT",
                category="events",
                summary="DRAFT SUMMARY INDEPENDENT",
                body=body,
                cover_image=str(new.pk),
            )
            if publish:
                data["action-publish"] = "1"
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 302)

        self.check_public("before_editor_save")
        submit()
        current = Post.objects.get(pk=target.pk)
        self.assertEqual(current.live_revision.content, baseline)
        self.assertEqual(current.get_latest_revision_as_object().cover_image_id, new.pk)
        for client in [self.client, self.visitor]:
            self.check_public(
                "draft_editor" if client == self.client else "draft_anonymous", client
            )
            for route in [
                "/?branch=second",
                "/news/?branch=second",
                f"/news/{target.pk}/?branch=second",
            ]:
                response = client.get(route)
                self.assertNotContains(response, "DRAFT TITLE INDEPENDENT")
                self.assertNotContains(response, "DRAFT SUMMARY INDEPENDENT")
                self.assertNotContains(response, "DRAFT BODY INDEPENDENT")
            detail = client.get(f"/news/{target.pk}/")
            self.assertEqual(detail.context["post"].cover_image_id, old.pk)
            self.assertEqual(detail.context["post"].category, "notices")
        self.assertEqual(
            self.visitor.get(new.get_rendition("width-80").url).status_code, 404
        )
        with patch(
            "django.utils.timezone.now", return_value=self.base + timedelta(days=100)
        ):
            submit(publish=True)
        self.manifest[target.pk].update(
            title="DRAFT TITLE INDEPENDENT",
            category="events",
            summary="DRAFT SUMMARY INDEPENDENT",
            body="<p>DRAFT BODY INDEPENDENT</p>",
            cover_image=new.pk,
        )
        self.check_public("explicit_publish_keeps_first_date")
        detail = self.visitor.get(f"/news/{target.pk}/")
        self.assertContains(detail, "DRAFT BODY INDEPENDENT")
        self.assertEqual(detail.context["post"].cover_image_id, new.pk)
        self.assertEqual(
            Post.objects.get(pk=target.pk).first_published_at,
            self.manifest[target.pk]["first"],
        )
        response = self.client.post(
            reverse("wagtailsnippets_news_post:unpublish", args=[target.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.manifest[target.pk]["live"] = False
        self.check_public("actual_CMS_withdraw")
        self.assertEqual(self.visitor.get(f"/news/{target.pk}/").status_code, 404)
        with patch(
            "django.utils.timezone.now", return_value=self.base + timedelta(days=200)
        ):
            submit(publish=True)
        self.manifest[target.pk]["live"] = True
        self.check_public("actual_CMS_republish_returns_original_rank")
        self.assertEqual(
            Post.objects.get(pk=target.pk).first_published_at,
            self.manifest[target.pk]["first"],
        )
        self.assertEqual(
            files,
            {
                p.pk: hashlib.sha256(Path(p.file.path).read_bytes()).hexdigest()
                for p in [old, new]
            },
        )
        self.record(
            "CMS-lifecycle",
            actual_password_login=True,
            actual_edit_save_publish_unpublish_republish=True,
            first_publication_preserved=True,
            image_files_unchanged=True,
        )

    def test_empty_one_five_escaping_preview_and_branch_fallbacks(self):
        home = self.check_public("zero")
        self.assertIsNotNone(home.select_one("#news .news-empty-state"))
        self.assertEqual(
            home.select_one("#news .section-heading > a")["href"],
            "/news/?branch=second",
        )
        post = Post.objects.create(
            title="<script>HOME_XSS</script>",
            summary='<img src=x onerror="SUMMARY_XSS">',
            body='<p>SAFE<strong>BODY</strong></p><script>BODY_XSS</script><a href="javascript:alert(1)">LINK</a>',
            live=False,
        )
        post.full_clean()
        with patch("django.utils.timezone.now", return_value=self.base):
            post.save_revision().publish()
        post.refresh_from_db()
        self.manifest[post.pk] = {
            "id": post.pk,
            "title": post.title,
            "summary": post.summary,
            "category": "notices",
            "body": str(post.body),
            "first": self.base,
            "live": True,
        }
        home = self.check_public("one_and_XSS")
        self.assertFalse(home.select("#news .news-list script, #news .news-list img"))
        detail = BeautifulSoup(
            self.visitor.get(f"/news/{post.pk}/").content, "html.parser"
        )
        self.assertFalse(
            detail.select(
                "#post-title script, .post-body script, .post-body a[href^='javascript:']"
            )
        )
        for index in range(1, 5):
            self.make(index, index, summary="" if index == 1 else f"SUMMARY {index}")
        home = self.check_public("exactly_five")
        empty_id = next(pk for pk, p in self.manifest.items() if p["summary"] == "")
        self.assertFalse(
            home.select_one(f"#news-{empty_id}-title")
            .find_parent("article")
            .select(".news-copy p")
        )
        for params, expected_branch in [
            ({}, "main"),
            ({"branch": "invalid<&"}, "main"),
            ({"branch": "second"}, "second"),
        ]:
            soup = BeautifulSoup(self.visitor.get("/", params).content, "html.parser")
            for anchor in soup.select(
                "#news .news-title-link, #news .section-heading > a"
            ):
                self.assertEqual(
                    parse_qs(urlsplit(anchor["href"]).query),
                    {"branch": [expected_branch]},
                )
                self.assertEqual(self.visitor.get(anchor["href"]).status_code, 200)
        draft = Post.objects.create(title="SECRET NEW DRAFT", live=False)
        draft.save_revision()
        request = RequestFactory().get("/?branch=second")
        request.user = self.user
        preview = render_home(
            request,
            BrandContent(name="BRAND PREVIEW", intro_title="PREVIEW"),
            is_preview=True,
        )
        self.assertNotContains(preview, "SECRET NEW DRAFT")
        soup = BeautifulSoup(preview.content, "html.parser")
        self.assertEqual(len(soup.select("#news .news-item")), 5)
        self.assertEqual(json.loads(soup.select_one("#home-popup-data").string), [])
        for branch in self.branches:
            branch.refresh_from_db()
            branch.unpublish()
        soup = BeautifulSoup(self.visitor.get("/?branch=second").content, "html.parser")
        for anchor in soup.select("#news .news-title-link, #news .section-heading > a"):
            self.assertEqual(urlsplit(anchor["href"]).query, "")
            self.assertEqual(self.visitor.get(anchor["href"]).status_code, 200)
        self.assertTrue(
            all(c.has_attr("hidden") for c in soup.select("[data-inquiry]"))
        )
        self.record(
            "boundaries",
            counts=[0, 1, 5],
            title_summary_body_XSS_safe=True,
            preview_never_exposes_post_drafts=True,
            no_branch_invalid_and_zero_branch_links_valid=True,
        )


if __name__ == "__main__":
    raise SystemExit(
        bool(
            get_runner(django.conf.settings)(verbosity=2, interactive=False).run_tests(
                ["__main__.HomeSemantics"]
            )
        )
    )
