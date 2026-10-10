import json
import tempfile
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from news.home import render_home
from news.models import Branch, BrandContent, PopupSetting, Post
from news.tests.test_publication import picture


class HomeNewsTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.date = datetime(2026, 9, 1, 16, 30, tzinfo=dt_timezone.utc)

    def post(self, title, **values):
        return Post.objects.create(title=title, live=False, **values)

    def publish(self, post, date=None):
        with patch("django.utils.timezone.now", return_value=date or self.date):
            post.save_revision().publish()
        post.refresh_from_db()
        return post

    def home(self, **params):
        response = self.client.get("/", params)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["Cache-Control"])
        return BeautifulSoup(response.content, "html.parser")

    def home_ids(self, soup):
        return [
            int(urlsplit(row["href"]).path.strip("/").split("/")[-1])
            for row in soup.select("#news .news-title-link")
        ]

    def list_ids(self):
        return [post.pk for post in self.client.get("/news/").context["page"]]

    def branch(self, key):
        branch = Branch.objects.create(
            key=key, name=f"공개 {key}", address="검수 주소", opening_hours="검수 시간"
        )
        return self.publish(branch)

    def test_zero_one_five_and_more_than_five_use_real_detail_links(self):
        posts = []
        for count in range(7):
            if count:
                posts.append(
                    self.publish(
                        self.post(f"실제 글 {count}"), self.date + timedelta(days=count)
                    )
                )
            with self.subTest(count=count):
                home = self.home()
                expected = [post.pk for post in reversed(posts)]
                self.assertEqual(self.home_ids(home), expected[:5])
                self.assertEqual(self.list_ids(), expected)
                self.assertEqual(
                    bool(home.select("#news .news-empty-state")), count == 0
                )
                self.assertNotIn("날짜 예시", home.select_one("#news").get_text())
                self.assertIn(
                    "로컬 CMS 검토용",
                    home.select_one("#news .content-example").get_text(),
                )
                self.assertEqual(
                    home.select_one("#news .section-heading > a")["href"], "/news/"
                )
                for link in home.select("#news .news-title-link"):
                    detail = self.client.get(link["href"])
                    self.assertEqual(detail.status_code, 200)
                    self.assertContains(detail, link.get_text())
                if count == 0:
                    self.assertIn(
                        "등록된 소식이 없습니다.", home.select_one("#news").get_text()
                    )
                    self.assertNotIn(
                        "방문 전 확인해주세요", home.select_one("#news").get_text()
                    )

    def test_first_publication_order_ties_and_popup_registration_order_are_separate(
        self,
    ):
        first, second, third = [self.post(f"등록 {number}") for number in range(3)]
        revisions = [post.save_revision() for post in (first, second, third)]
        for revision, date in [
            (revisions[0], self.date),
            (revisions[2], self.date + timedelta(days=2)),
            (revisions[1], self.date + timedelta(days=2)),
        ]:
            with patch("django.utils.timezone.now", return_value=date):
                revision.publish()
        expected = [second.pk, third.pk, first.pk]
        self.assertEqual(self.home_ids(self.home()), expected)
        self.assertEqual(self.list_ids(), expected)
        now = timezone.now()
        for post in (first, second, third):
            PopupSetting.objects.create(
                post=post,
                enabled=True,
                starts_at=now - timedelta(hours=1),
                ends_at=now + timedelta(hours=1),
            )
        data = json.loads(self.home().select_one("#home-popup-data").string)
        self.assertEqual(
            [int(item["postId"]) for item in data], [first.pk, second.pk, third.pk]
        )
        self.assertEqual(self.home().select_one("#news time")["datetime"], "2026-09-04")

    def test_saved_draft_publish_withdraw_and_republish_keep_first_date_and_rank(self):
        old_image, new_image = (
            picture("home-old.png"),
            picture("home-draft.png", "white"),
        )
        old = self.publish(
            self.post(
                "공개 이전 제목",
                category="notices",
                summary="공개 이전 요약",
                body="<p>공개 이전 본문</p>",
                cover_image=old_image,
            )
        )
        newer = self.publish(self.post("더 최근 글"), self.date + timedelta(days=1))
        first_date = old.first_published_at
        draft = old.get_latest_revision_as_object()
        draft.title, draft.category, draft.summary, draft.body, draft.cover_image = (
            "비공개 초안 제목",
            "events",
            "비공개 초안 요약",
            "<p>비공개 초안 본문</p>",
            new_image,
        )
        revision = draft.save_revision()
        # Forge only revision JSON. Saving an object with a manually edited
        # model timestamp would itself change the source of truth.
        revision.content["first_published_at"] = (
            self.date + timedelta(days=30)
        ).isoformat()
        revision.save(update_fields=["content"])
        for authenticated in (False, True):
            if authenticated:
                self.client.force_login(
                    get_user_model().objects.create_superuser(
                        "home-admin", password="test-password"
                    )
                )
            home = self.home()
            self.assertEqual(self.home_ids(home), [newer.pk, old.pk])
            for response in (
                str(home.select_one("#news")),
                self.client.get("/news/").content.decode(),
                self.client.get(old.get_absolute_url()).content.decode(),
            ):
                self.assertIn("공개 이전 제목", response)
                self.assertNotIn("비공개 초안", response)
                self.assertNotIn("2026.10.02", response)
            self.assertEqual(
                self.client.get(old.get_absolute_url()).context["post"].cover_image_id,
                old_image.pk,
            )
        self.client.logout()
        self.assertEqual(
            self.client.get(new_image.get_rendition("width-80").url).status_code, 404
        )
        with patch(
            "django.utils.timezone.now", return_value=self.date + timedelta(days=40)
        ):
            revision.publish()
        old.refresh_from_db()
        self.assertEqual(old.first_published_at, first_date)
        self.assertEqual(self.home_ids(self.home()), [newer.pk, old.pk])
        self.assertEqual(self.list_ids(), [newer.pk, old.pk])
        row = self.home().select_one(f"#news-{old.pk}-title").find_parent("article")
        self.assertIn("비공개 초안 제목", row.get_text())
        self.assertIn("이벤트", row.get_text())
        self.assertIn("비공개 초안 요약", row.get_text())
        old.unpublish()
        self.assertEqual(self.home_ids(self.home()), [newer.pk])
        self.assertEqual(self.list_ids(), [newer.pk])
        self.assertEqual(self.client.get(old.get_absolute_url()).status_code, 404)
        self.publish(old, self.date + timedelta(days=50))
        self.assertEqual(old.first_published_at, first_date)
        self.assertEqual(self.home_ids(self.home()), [newer.pk, old.pk])
        self.assertEqual(self.list_ids(), [newer.pk, old.pk])
        self.assertContains(self.client.get(old.get_absolute_url()), "비공개 초안 본문")

    def test_live_snapshot_ignores_mutable_post_fields_and_missing_revision(self):
        post = self.publish(self.post("공개 스냅샷", summary="공개 요약"))
        Post.objects.filter(pk=post.pk).update(
            title="변경 중 모델", category="events", summary="변경 중 요약"
        )
        self.post("공개 리비전 없는 글", live_revision=None).save_revision()
        broken = self.post("불완전 공개 행")
        Post.objects.filter(pk=broken.pk).update(live=True)
        self.assertEqual(self.home_ids(self.home()), [post.pk])
        self.assertEqual(self.list_ids(), [post.pk])
        self.assertIn("공개 스냅샷", self.home().select_one("#news").get_text())
        self.assertNotIn("변경 중", self.home().select_one("#news").get_text())

    def test_new_draft_is_absent_even_for_editor_and_brand_preview(self):
        post = self.post("아직 미공개 소식", body="<p>미공개 본문</p>")
        post.save_revision()
        public = self.publish(self.post("공개된 소식"))
        self.client.force_login(
            get_user_model().objects.create_superuser(
                "preview-admin", password="test-password"
            )
        )
        self.assertEqual(self.home_ids(self.home()), [public.pk])
        self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 404)
        request = RequestFactory().get("/")
        response = render_home(
            request,
            BrandContent(name="검토 브랜드", intro_title="소개 초안"),
            is_preview=True,
        )
        self.assertContains(response, "소개 초안")
        self.assertContains(response, "공개된 소식")
        self.assertNotContains(response, "아직 미공개")
        self.assertNotContains(response, "home-popups.js")

    def test_escaping_optional_summary_category_and_date_reuse_existing_row(self):
        with_summary = self.publish(
            self.post(
                '<script>alert("제목")</script> & 소식',
                summary='<img src=x onerror="alert(1)"> & 요약',
                category="events",
            )
        )
        without_summary = self.publish(self.post("요약 없는 소식"))
        home = self.home()
        self.assertFalse(home.select("#news .news-list script, #news .news-list img"))
        row = home.select_one(f"#news-{with_summary.pk}-title").find_parent("article")
        self.assertEqual(row.select_one("h3 a").get_text(), with_summary.title)
        self.assertEqual(
            row.select_one(".news-copy p").get_text(), with_summary.summary
        )
        self.assertEqual(row.select_one(".news-category").get_text(), "이벤트")
        self.assertEqual(row.select_one("time")["datetime"], "2026-09-02")
        self.assertEqual(row.select_one("time").get_text(), "2026.09.02")
        self.assertFalse(
            home.select_one(f"#news-{without_summary.pk}-title")
            .find_parent("article")
            .select(".news-copy p")
        )

    def test_server_links_keep_valid_selected_branch_without_duplicate_query(self):
        self.branch("main")
        self.branch("second")
        post = self.publish(self.post("지점 공통 소식"))
        for requested, expected in [
            ("second", "second"),
            ("main", "main"),
            ("invalid<&", "main"),
            ("", "main"),
        ]:
            with self.subTest(requested=requested):
                home = self.home(branch=requested)
                for link in home.select(
                    "#news .news-title-link, #news .section-heading > a"
                ):
                    query = parse_qs(urlsplit(link["href"]).query)
                    self.assertEqual(query, {"branch": [expected]})
                    response = self.client.get(link["href"])
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.context["branch"], expected)
                detail = self.client.get(f"{post.get_absolute_url()}?branch={expected}")
                self.assertEqual(detail.context["category"], "all")
                self.assertEqual(detail.context["return_page"], 1)
                listing = self.client.get(f"/news/?branch={expected}")
                self.assertEqual(listing.context["category"], "all")
                self.assertEqual(listing.context["page"].number, 1)

    def test_zero_public_branches_keep_news_accessible_and_contact_hidden(self):
        post = self.publish(self.post("지점 준비 중에도 공개 소식"))
        home = self.home(branch="second")
        link = home.select_one("#news .news-title-link")
        self.assertEqual(link["href"], post.get_absolute_url())
        self.assertEqual(
            home.select_one("#news .section-heading > a")["href"], "/news/"
        )
        self.assertEqual(self.client.get(link["href"]).status_code, 200)
        self.assertTrue(
            all(control.has_attr("hidden") for control in home.select("[data-inquiry]"))
        )
