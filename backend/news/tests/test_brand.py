import tempfile
from datetime import timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from news.models import BrandContent, PopupSetting, Post
from news.publication import published_brand, published_image_ids
from news.tests.test_publication import picture


class BrandTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.media = override_settings(MEDIA_ROOT=self.directory.name)
        self.media.enable()
        self.addCleanup(self.media.disable)
        self.admin = get_user_model().objects.create_superuser(
            "brand-admin", password="test-password"
        )
        self.url = reverse("wagtailsnippets_news_brandcontent:edit", args=[1])

    def brand(self, **values):
        return BrandContent.objects.create(
            name="공개 브랜드",
            intro_title="공개 소개\n둘째 줄",
            intro_text="공개 설명",
            **values,
        )

    def publish(self, brand):
        brand.save_revision(user=self.admin).publish(user=self.admin)
        brand.refresh_from_db()
        return brand

    def payload(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        result = {}
        for name in [
            "name",
            "intro_title",
            "intro_text",
            "hero_alt",
            "logo_image",
            "hero_image",
            "hero_position_x",
            "hero_position_y",
            "loaded_revision_id",
            "loaded_revision_created_at",
        ]:
            field = soup.find(attrs={"name": name})
            self.assertIsNotNone(field, name)
            result[name] = (
                field.text.removeprefix("\n")
                if field.name == "textarea"
                else field.get("value", "")
            )
        return result

    def test_blank_draft_does_not_leak_and_empty_home_keeps_navigation(self):
        brand = BrandContent.objects.create()
        brand.save_revision()
        self.assertIsNone(published_brand())
        for user in [None, self.admin]:
            if user:
                self.client.force_login(user)
            response = self.client.get("/")
            self.assertContains(response, "브랜드 소개를 준비 중입니다.")
            self.assertContains(response, "/branches/")
            self.assertContains(response, "/news/")
            self.assertNotContains(response, 'class="hero-figure"')
        self.assertContains(
            self.client.get(reverse("wagtailsnippets_news_brandcontent:list")),
            "브랜드·홈 (준비 초안)",
        )

    def test_live_revision_used_on_home_news_and_popup_despite_new_draft(self):
        old, new, logo = (
            picture("old.png"),
            picture("new.png", "white"),
            picture("logo.png"),
        )
        brand = self.publish(self.brand(hero_image=old, logo_image=logo))
        draft = brand.get_latest_revision_as_object()
        draft.name, draft.intro_title, draft.hero_image, draft.logo_image = (
            "秘密の新ブランド",
            "비공개 소개",
            new,
            new,
        )
        draft.save_revision()
        self.assertEqual(published_image_ids(), {old.pk, logo.pk})
        for user in [None, self.admin]:
            if user:
                self.client.force_login(user)
            for url in ["/", "/news/"]:
                response = self.client.get(url)
                self.assertContains(response, 'alt="공개 브랜드"')
                self.assertNotContains(response, "비공개 소개")
                self.assertNotContains(response, "秘密の新ブランド")
            self.assertContains(
                self.client.get("/"), "공개 소개<br/>둘째 줄", html=True
            )

    def test_preview_uses_draft_and_private_images_without_automatic_popup(self):
        image = picture("draft.png")
        brand = self.brand(hero_image=image)
        brand.save_revision()
        request = RequestFactory().get("/")
        request.user = self.admin
        response = brand.serve_preview(request, "")
        self.assertContains(response, "공개 소개")
        self.assertContains(response, "미리보기")
        self.assertNotContains(response, "home-popups.js")
        self.assertIn("private", response.headers["Cache-Control"])
        self.assertIsNone(published_brand())
        url = BeautifulSoup(response.content, "html.parser").select_one(
            ".hero-figure img"
        )["src"]
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)
        request.user = get_user_model().objects.create_user("outsider", is_staff=True)
        with self.assertRaises(PermissionDenied):
            brand.serve_preview(request, "")

    def test_republish_replaces_brand_media_but_shared_post_image_remains(self):
        old, new = picture("old.png"), picture("new.png")
        brand = self.publish(self.brand(hero_image=old))
        old_url = old.get_rendition("width-80").url
        post = Post.objects.create(title="공통 소식", cover_image=old, live=False)
        post.save_revision().publish(user=self.admin)
        post.refresh_from_db()
        draft = brand.get_latest_revision_as_object()
        draft.intro_title, draft.hero_image = "재공개 소개", new
        draft.save_revision().publish(user=self.admin)
        self.assertContains(self.client.get("/"), "재공개 소개")
        self.assertEqual(published_image_ids(), {old.pk, new.pk})
        self.assertEqual(self.client.get(old_url).status_code, 200)
        post.unpublish()
        self.assertEqual(self.client.get(old_url).status_code, 404)
        self.assertEqual(
            self.client.get(new.get_rendition("width-80").url).status_code, 200
        )

    def test_unpublish_removes_brand_and_image_but_preserves_news_and_branch_navigation(
        self,
    ):
        image = picture()
        self.publish(self.brand(hero_image=image, logo_image=image))
        url = image.get_rendition("width-80").url
        post = Post.objects.create(title="남아 있는 소식", live=False)
        post.save_revision().publish(user=self.admin)
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(
                reverse("wagtailsnippets_news_brandcontent:unpublish", args=[1])
            ).status_code,
            302,
        )
        self.client.logout()
        response = self.client.get("/")
        self.assertNotContains(response, "공개 브랜드")
        self.assertNotContains(response, "공개 소개")
        self.assertContains(response, "브랜드 소개를 준비 중입니다.")
        self.assertContains(response, "/branches/")
        self.assertContains(self.client.get("/news/"), "남아 있는 소식")
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertTrue(BrandContent.objects.exists())

    def test_admin_draft_save_reopen_preview_and_publish_are_separate(self):
        brand = self.publish(self.brand())
        self.client.force_login(self.admin)
        payload = self.payload()
        payload["intro_title"] = "편집 초안"
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.assertEqual(self.payload()["intro_title"], "편집 초안")
        self.assertNotContains(self.client.get("/"), "편집 초안")
        preview_url = reverse(
            "wagtailsnippets_news_brandcontent:preview_on_edit", args=[1]
        )
        self.assertEqual(self.client.post(preview_url, self.payload()).status_code, 200)
        self.assertContains(self.client.get(preview_url), "편집 초안")
        payload = self.payload()
        payload["action-publish"] = "1"
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.assertContains(self.client.get("/"), "편집 초안")
        brand.refresh_from_db()
        self.assertEqual(brand.revisions.count(), 3)

    def test_publish_requires_name_and_title_but_incomplete_draft_keeps_input(self):
        brand = self.publish(self.brand())
        self.client.force_login(self.admin)
        payload = self.payload()
        payload.update(
            name=" ",
            intro_title="",
            intro_text="편집한 설명 보존",
            **{"action-publish": "1"},
        )
        response = self.client.post(self.url, payload)
        self.assertContains(response, "공개하려면 입력해 주세요.")
        self.assertContains(response, "편집한 설명 보존")
        self.assertEqual(published_brand().name, "공개 브랜드")
        payload.pop("action-publish")
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        brand.refresh_from_db()
        revision = brand.get_latest_revision()
        with self.assertRaises(ValidationError):
            revision.publish(user=self.admin)
        self.assertEqual(published_brand().name, "공개 브랜드")
        self.assertEqual(self.payload()["intro_text"], "편집한 설명 보존")

    def test_first_publish_is_validated_while_blank_new_draft_can_be_saved(self):
        self.client.force_login(self.admin)
        add = reverse("wagtailsnippets_news_brandcontent:add")
        payload = {
            "name": "",
            "intro_title": "",
            "hero_position_x": 50,
            "hero_position_y": 50,
            "action-publish": "1",
        }
        self.assertContains(self.client.post(add, payload), "공개하려면 입력해 주세요.")
        self.assertFalse(BrandContent.objects.exists())
        payload.pop("action-publish")
        self.assertEqual(self.client.post(add, payload).status_code, 302)
        self.assertFalse(BrandContent.objects.get().live)

    def test_editor_cannot_save_locked_brand_or_publish_without_permission(self):
        brand = self.publish(self.brand())
        editor = get_user_model().objects.create_user("brand-editor", is_staff=True)
        editor.user_permissions.add(
            *Permission.objects.filter(
                codename__in=[
                    "access_admin",
                    "view_brandcontent",
                    "change_brandcontent",
                ]
            )
        )
        self.client.force_login(editor)
        payload = self.payload()
        payload.update(name="권한 없는 공개", **{"action-publish": "1"})
        response = self.client.post(self.url, payload)
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(published_brand().name, "공개 브랜드")
        brand.refresh_from_db()
        brand.locked, brand.locked_by = True, self.admin
        brand.save(update_fields=["locked", "locked_by"])
        revision = brand.latest_revision_id
        payload = self.payload()
        payload["name"] = "잠금 무시"
        self.client.post(self.url, payload)
        brand.refresh_from_db()
        self.assertEqual(brand.latest_revision_id, revision)

    def test_publishing_previous_blank_revision_is_rejected_in_history_editor(self):
        brand = BrandContent.objects.create()
        incomplete = brand.save_revision(user=self.admin)
        brand.name, brand.intro_title = "공개 브랜드", "공개 소개"
        self.publish(brand)
        self.client.force_login(self.admin)
        payload = self.payload()
        payload.update(name="", intro_title="", **{"action-publish": "1"})
        url = reverse(
            "wagtailsnippets_news_brandcontent:revisions_revert",
            args=[1, incomplete.pk],
        )
        self.assertContains(self.client.post(url, payload), "공개하려면 입력해 주세요.")
        self.assertEqual(published_brand().intro_title, "공개 소개")

    def test_popup_keeps_post_publication_and_uses_only_live_brand(self):
        brand = self.publish(self.brand())
        post = Post.objects.create(title="연결 소식", live=False)
        post.save_revision().publish(user=self.admin)
        now = timezone.now()
        PopupSetting.objects.create(
            post=post,
            enabled=True,
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=1),
        )
        draft = brand.get_latest_revision_as_object()
        draft.name = "노출 금지 브랜드 초안"
        draft.save_revision()
        response = self.client.get(f"/popups/{post.pk}/")
        self.assertContains(response, "공개 브랜드")
        self.assertNotContains(response, "노출 금지")
        brand.unpublish()
        self.assertContains(self.client.get(f"/popups/{post.pk}/"), "연결 소식")
        self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 200)

    def test_stale_editor_cannot_overwrite_newer_brand_draft(self):
        brand = self.publish(self.brand())
        self.client.force_login(self.admin)
        stale = self.payload()
        newer = brand.get_latest_revision_as_object()
        newer.name = "새 초안 브랜드"
        newer.save_revision(user=self.admin)
        stale["name"] = "오래된 화면"
        response = self.client.post(self.url, stale)
        self.assertContains(response, "더 최근 내용")
        self.assertContains(response, 'value="오래된 화면"')
        brand.refresh_from_db()
        self.assertEqual(brand.get_latest_revision_as_object().name, "새 초안 브랜드")
        self.assertEqual(published_brand().name, "공개 브랜드")

    def test_image_optional_layout_and_plain_text_escaping_and_focal_validation(self):
        brand = self.brand()
        brand.intro_title = '<script>alert("unsafe")</script>'
        self.publish(brand)
        response = self.client.get("/")
        self.assertContains(response, "hero-layout--text-only")
        self.assertNotContains(response, '<script>alert("unsafe")</script>')
        self.assertContains(response, "&lt;script&gt;")
        brand.hero_position_x = 101
        with self.assertRaises(ValidationError):
            brand.full_clean()

    def test_singleton_creation_and_delete_are_denied(self):
        self.publish(self.brand())
        self.client.force_login(self.admin)
        for response in [
            self.client.get(reverse("wagtailsnippets_news_brandcontent:add")),
            self.client.post(
                reverse("wagtailsnippets_news_brandcontent:add"), {"name": "중복"}
            ),
            self.client.post(
                reverse("wagtailsnippets_news_brandcontent:delete", args=[1])
            ),
        ]:
            self.assertRedirects(
                response, reverse("wagtailadmin_home"), fetch_redirect_response=False
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            BrandContent.objects.create(id=2, name="두 번째 브랜드")
        self.assertEqual(BrandContent.objects.count(), 1)

    def test_model_permission_and_csrf_are_required(self):
        self.publish(self.brand())
        outsider = get_user_model().objects.create_user("brand-outsider", is_staff=True)
        outsider.user_permissions.add(Permission.objects.get(codename="access_admin"))
        self.client.force_login(outsider)
        self.assertRedirects(
            self.client.get(self.url),
            reverse("wagtailadmin_home"),
            fetch_redirect_response=False,
        )
        guarded = Client(enforce_csrf_checks=True)
        guarded.force_login(self.admin)
        self.assertEqual(
            guarded.post(self.url, {"name": "CSRF 없는 변경"}).status_code, 403
        )

    def test_bootstrap_is_idempotent_and_keeps_drafts_permissions_and_credentials(self):
        credentials = Path(self.directory.name) / ".local-credentials"
        credentials.write_text("private-test-value")
        with override_settings(BASE_DIR=Path(self.directory.name)):
            call_command("bootstrap_brand_review", verbosity=0)
            brand = BrandContent.objects.get()
            old_revision = brand.live_revision_id
            draft = brand.get_latest_revision_as_object()
            draft.name = "사용자 변경 보존"
            draft.save_revision()
            group = Group.objects.get(name="로컬 소식 검토 운영자")
            post_perm = Permission.objects.get(codename="change_post")
            group.permissions.add(post_perm)
            call_command("bootstrap_brand_review", verbosity=0)
        brand.refresh_from_db()
        self.assertEqual(brand.get_latest_revision_as_object().name, "사용자 변경 보존")
        self.assertEqual(brand.live_revision_id, old_revision)
        self.assertEqual(brand.revisions.count(), 2)
        self.assertEqual(credentials.read_text(), "private-test-value")
        self.assertIn(post_perm, group.permissions.all())
        self.assertIn(
            Permission.objects.get(codename="publish_brandcontent"),
            group.permissions.all(),
        )
