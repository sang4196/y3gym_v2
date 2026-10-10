import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from threading import Barrier
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import close_old_connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from news.models import PopupSetting, Post
from news.popups import eligible_popups
from news.tests.test_publication import picture


class PopupTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.admin = get_user_model().objects.create_superuser(
            "popup-admin", password="test-password"
        )
        self.client.force_login(self.admin)
        self.visitor = Client()
        self.now = datetime(2026, 10, 10, tzinfo=dt_timezone.utc)
        self.post = Post.objects.create(
            title="공개된 안내",
            summary="공개 설명",
            body="<p>공개 본문</p>",
            live=False,
        )
        self.post.save_revision(user=self.admin).publish(user=self.admin)
        self.post.refresh_from_db()
        self.url = reverse("news_popup_settings", args=[self.post.pk])

    def payload(self, **values):
        return {
            "enabled": True,
            "starts_at": "2026-10-10T09:00",
            "ends_at": "2026-10-10T10:00",
            "version": 0,
            **values,
        }

    def apply(self, **values):
        return self.client.post(
            self.url, self.payload(**values), content_type="application/json"
        )

    def setting(self, **values):
        return PopupSetting.objects.create(
            post=self.post,
            enabled=True,
            starts_at=self.now,
            ends_at=self.now + timedelta(hours=1),
            **values,
        )

    def home_data(self, now=None, branch="main"):
        with patch("news.popups.timezone.now", return_value=now or self.now):
            response = self.visitor.get("/", {"branch": branch})
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["Cache-Control"])
        soup = BeautifulSoup(response.content, "html.parser")
        return json.loads(soup.select_one("#home-popup-data").string)

    def test_admin_panel_explains_draft_first_and_current_post_without_url_input(self):
        response = self.client.get(reverse("wagtailsnippets_news_post:add"))
        self.assertContains(response, "먼저 게시글을 초안 저장")
        response = self.client.get(
            reverse("wagtailsnippets_news_post:edit", args=[self.post.pk])
        )
        self.assertContains(response, "팝업 설정 적용")
        self.assertContains(response, "한국 시간")
        soup = BeautifulSoup(response.content, "html.parser")
        fields = soup.select("[data-popup-field]")
        self.assertEqual(len(fields), 3)
        self.assertTrue(all(not field.has_attr("name") for field in fields))
        self.assertEqual(soup.select_one("[data-apply-popup]")["type"], "button")

    def test_applied_dates_persist_as_korean_time_and_reopen(self):
        response = self.apply()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["applied"])
        setting = self.post.popup_setting
        self.assertEqual(setting.starts_at, self.now)
        self.assertEqual(setting.ends_at, self.now + timedelta(hours=1))
        response = self.client.get(
            reverse("wagtailsnippets_news_post:edit", args=[self.post.pk])
        )
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertEqual(
            soup.select_one("#popup-starts-at")["value"], "2026-10-10T09:00"
        )
        self.assertEqual(soup.select_one("#popup-ends-at")["value"], "2026-10-10T10:00")
        self.assertEqual(
            soup.select_one("[data-popup-settings]")["data-popup-version"], "1"
        )

    def test_enabled_requires_both_dates_and_strict_increasing_period(self):
        for values in [
            {"starts_at": ""},
            {"ends_at": ""},
            {"ends_at": "2026-10-10T09:00"},
            {"ends_at": "2026-10-10T08:59"},
            {"starts_at": "invalid"},
        ]:
            with self.subTest(values=values):
                response = self.apply(**values)
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.json()["errors"])
                self.assertFalse(PopupSetting.objects.exists())

    def test_disabled_setting_can_have_no_period(self):
        response = self.apply(enabled=False, starts_at="", ends_at="")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"], "사용 안 함")

    def test_invalid_and_stale_changes_do_not_alter_saved_state(self):
        self.assertEqual(self.apply().status_code, 200)
        stale = self.apply(enabled=False)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["version"], 1)
        self.assertNotEqual(stale.json()["state"], "사용 안 함")
        invalid = self.apply(version=1, ends_at="")
        self.assertEqual(invalid.status_code, 400)
        saved = PopupSetting.objects.get(post=self.post)
        self.assertTrue(saved.enabled)
        self.assertEqual(saved.ends_at, self.now + timedelta(hours=1))
        self.assertEqual(saved.version, 1)

    def test_settings_do_not_publish_new_draft_or_create_body_revision(self):
        draft = Post.objects.create(title="비공개 초안", live=False)
        draft.save_revision()
        self.url = reverse("news_popup_settings", args=[draft.pk])
        response = self.apply(title="무시할 제목", body="무시할 본문")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"], "게시글 비공개")
        draft.refresh_from_db()
        self.assertFalse(draft.live)
        self.assertEqual(draft.revisions.count(), 1)
        self.assertEqual(draft.title, "비공개 초안")
        self.assertEqual(self.visitor.get(draft.get_absolute_url()).status_code, 404)

    def test_popup_uses_live_title_summary_and_image_with_unpublished_edits(self):
        image = picture("public-popup.png")
        self.post.cover_image = image
        self.post.save_revision().publish()
        self.post.refresh_from_db()
        draft_image = picture("private-popup.png", "white")
        draft = self.post.get_latest_revision_as_object()
        draft.title, draft.summary, draft.cover_image = (
            "비밀 초안",
            "초안 설명",
            draft_image,
        )
        draft.save_revision()
        self.apply()
        payload = self.home_data()[0]
        self.assertEqual(payload["title"], "공개된 안내")
        self.assertEqual(payload["description"], "공개 설명")
        self.assertEqual(payload["image"], image.get_rendition("width-800").url)
        self.assertEqual(self.visitor.get(payload["image"]).status_code, 200)
        self.assertEqual(
            self.visitor.get(draft_image.get_rendition("width-800").url).status_code,
            404,
        )
        with patch("news.popups.timezone.now", return_value=self.now):
            popup = self.visitor.get(payload["url"])
        self.assertContains(popup, "공개된 안내")
        self.assertNotContains(popup, "비밀 초안")
        self.assertNotContains(popup, "초안 설명")

    def test_body_saved_from_pre_apply_form_then_published_keeps_popup_setting(self):
        edit_url = reverse("wagtailsnippets_news_post:edit", args=[self.post.pk])
        page = BeautifulSoup(self.client.get(edit_url).content, "html.parser")
        payload = {
            "title": "새 본문 제목",
            "category": "events",
            "summary": "새 설명",
            "cover_image": "",
        }
        for name in ["body", "loaded_revision_id", "loaded_revision_created_at"]:
            payload[name] = page.find("input", {"name": name}).get("value", "")
        self.assertEqual(self.apply().status_code, 200)
        self.assertEqual(self.client.post(edit_url, payload).status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.live_revision.as_object().title, "공개된 안내")
        self.post.get_latest_revision().publish(user=self.admin)
        setting = PopupSetting.objects.get(post=self.post)
        self.assertTrue(setting.enabled)
        self.assertEqual(setting.version, 1)
        self.assertEqual(setting.starts_at, self.now)
        self.assertEqual(self.home_data()[0]["title"], "새 본문 제목")

    def test_server_period_boundaries_and_expiration_leave_post_public(self):
        self.setting()
        for moment, count in [
            (self.now - timedelta(microseconds=1), 0),
            (self.now, 1),
            (self.now + timedelta(minutes=30), 1),
            (self.now + timedelta(hours=1), 0),
            (self.now + timedelta(hours=2), 0),
        ]:
            with self.subTest(now=moment):
                self.assertEqual(len(self.home_data(moment)), count)
                with patch("news.popups.timezone.now", return_value=moment):
                    for suffix in ["", "data/"]:
                        response = self.visitor.get(f"/popups/{self.post.pk}/{suffix}")
                        self.assertEqual(response.status_code, 200 if count else 404)
                        self.assertIn("no-store", response.headers["Cache-Control"])
                self.assertEqual(
                    self.visitor.get(self.post.get_absolute_url()).status_code, 200
                )

    def test_disable_and_unpublish_remove_both_popup_endpoints_and_home_data(self):
        self.setting()
        for action in ["disable", "unpublish"]:
            with self.subTest(action=action):
                if action == "disable":
                    response = self.apply(enabled=False)
                    self.assertEqual(response.status_code, 200)
                else:
                    PopupSetting.objects.filter(post=self.post).update(enabled=True)
                    self.assertEqual(
                        self.client.post(
                            reverse(
                                "wagtailsnippets_news_post:unpublish",
                                args=[self.post.pk],
                            )
                        ).status_code,
                        302,
                    )
                self.assertEqual(self.home_data(), [])
                with patch("news.popups.timezone.now", return_value=self.now):
                    self.assertEqual(
                        self.visitor.get(f"/popups/{self.post.pk}/").status_code, 404
                    )
                    self.assertEqual(
                        self.visitor.get(f"/popups/{self.post.pk}/data/").status_code,
                        404,
                    )
                self.assertEqual(
                    self.visitor.get(self.post.get_absolute_url()).status_code,
                    200 if action == "disable" else 404,
                )

    def test_all_overlaps_use_registration_not_publication_order_and_common_branches(
        self,
    ):
        first_revision = self.post.revisions.first()
        first_revision.created_at = self.now - timedelta(days=2)
        first_revision.save(update_fields=["created_at"])
        # A newer publication of the older post must not reorder its popup.
        other = Post.objects.create(title="나중에 등록", live=False)
        other.save_revision().publish()
        self.post.save_revision().publish()
        self.setting()
        PopupSetting.objects.create(
            post=other,
            enabled=True,
            starts_at=self.now,
            ends_at=self.now + timedelta(hours=1),
        )
        expected = [str(self.post.pk), str(other.pk)]
        for branch in ["main", "second"]:
            self.assertEqual(
                [item["postId"] for item in self.home_data(branch=branch)], expected
            )
        self.assertEqual(
            list(eligible_popups(self.now).values_list("post_id", flat=True)),
            [self.post.pk, other.pk],
        )

    def test_saved_status_distinguishes_all_required_conditions(self):
        setting = self.setting()
        for now, title in [
            (self.now - timedelta(seconds=1), "시작 전"),
            (self.now, "노출 대상"),
            (self.now + timedelta(hours=1), "기간 종료"),
        ]:
            self.assertEqual(setting.display_state(now)[0], title)
        setting.enabled = False
        self.assertEqual(setting.display_state(self.now)[0], "사용 안 함")
        setting.enabled, setting.post.live = True, False
        self.assertEqual(setting.display_state(self.now)[0], "게시글 비공개")

    def test_permission_csrf_and_existing_edit_lock_are_not_bypassed(self):
        anonymous = Client()
        self.assertEqual(anonymous.post(self.url, self.payload()).status_code, 302)
        editor = get_user_model().objects.create_user("no-publish", is_staff=True)
        editor.user_permissions.add(
            *Permission.objects.filter(codename__in=["access_admin", "change_post"])
        )
        restricted = Client()
        restricted.force_login(editor)
        self.assertEqual(
            restricted.get(
                self.url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
            ).status_code,
            403,
        )
        self.assertEqual(
            restricted.post(
                self.url, self.payload(), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
            ).status_code,
            403,
        )
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.admin)
        self.assertEqual(csrf.post(self.url, self.payload()).status_code, 403)
        self.post.locked, self.post.locked_by = True, self.admin
        self.post.save(update_fields=["locked", "locked_by"])
        self.assertEqual(self.apply().status_code, 409)
        self.assertFalse(PopupSetting.objects.exists())

    def test_fallback_form_saves_without_javascript_and_json_rejects_malformed_data(
        self,
    ):
        page = self.client.get(self.url)
        self.assertContains(page, "팝업 설정 적용")
        self.assertContains(page, "한국 시간")
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 200)
        for body in ["[1]", "{"]:
            self.assertEqual(
                self.client.post(
                    self.url, body, content_type="application/json"
                ).status_code,
                400,
            )
        self.assertEqual(PopupSetting.objects.get(post=self.post).version, 1)

    def test_home_keeps_approved_assets_and_no_routine_alert_button(self):
        self.setting()
        with patch("news.popups.timezone.now", return_value=self.now):
            response = self.visitor.get("/")
        self.assertContains(response, "/static/prototype/styles.css")
        self.assertContains(response, "/static/news/home-popups.js")
        self.assertContains(response, "/news/")
        self.assertNotContains(response, "알림 보기")
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertIsNotNone(soup.select_one("[data-popup-recovery][hidden]"))
        self.assertIsNotNone(
            soup.select_one("noscript a[href='" + self.post.get_absolute_url() + "']")
        )


class PopupConcurrencyTests(TransactionTestCase):
    def test_two_initial_applies_commit_only_one_setting_and_no_post_revision(self):
        user = get_user_model().objects.create_superuser(
            "popup-race", password="test-password"
        )
        post = Post.objects.create(title="동시 설정", live=False)
        post.save_revision()
        url = reverse("news_popup_settings", args=[post.pk])
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(user)
        barrier = Barrier(2)

        def apply(number):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                response = clients[number].post(
                    url,
                    {
                        "enabled": True,
                        "version": 0,
                        "starts_at": f"2026-10-10T0{number + 1}:00",
                        "ends_at": "2026-10-11T00:00",
                    },
                    content_type="application/json",
                )
                return response.status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(apply, [0, 1]))
        self.assertEqual(sorted(results), [200, 409])
        self.assertEqual(PopupSetting.objects.filter(post=post).count(), 1)
        self.assertEqual(PopupSetting.objects.get(post=post).version, 1)
        self.assertEqual(post.revisions.count(), 1)
