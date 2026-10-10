import io
import json
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image as PILImage

from news.models import Branch, ContentImage, Post
from news.publication import published_image_ids


def picture(name="test.png", color="navy"):
    buffer = io.BytesIO()
    PILImage.new("RGB", (80, 60), color).save(buffer, format="PNG")
    return ContentImage.objects.create(
        title="검수 사진",
        file=SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png"),
    )


class PublicationTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.media = override_settings(MEDIA_ROOT=self.directory.name)
        self.media.enable()
        self.addCleanup(self.media.disable)
        self.admin = get_user_model().objects.create_superuser(
            "test-admin", password="test-password"
        )
        self.client = Client()

    def post(self, **values):
        return Post.objects.create(
            title="공개 제목",
            summary="공개 설명",
            body="<p>공개 본문</p>",
            live=False,
            **values,
        )

    def publish(self, post):
        revision = post.save_revision(user=self.admin)
        revision.publish(user=self.admin)
        post.refresh_from_db()
        return post

    def editor_payload(self, post):
        response = self.client.get(
            reverse("wagtailsnippets_news_post:edit", args=[post.pk])
        )
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        payload = {
            "title": "수정 제목",
            "category": "notices",
            "summary": "수정 설명",
            "cover_image": "",
        }
        for name in ["body", "loaded_revision_id", "loaded_revision_created_at"]:
            field = soup.find("input", {"name": name})
            self.assertIsNotNone(field, name)
            payload[name] = field.get("value", "")
        return payload

    def test_new_draft_is_absent_from_public_urls_even_for_admin(self):
        post = self.post()
        post.save_revision()
        for authenticated in [False, True]:
            if authenticated:
                self.client.force_login(self.admin)
            self.assertNotContains(self.client.get(reverse("news:list")), post.title)
            self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 404)

    def test_line_breaks_and_images_reopen_in_the_actual_rich_text_editor(self):
        image = picture()
        post = self.post()
        post.body = (
            "<p>한글 첫 줄<br/>같은 문단 다음 줄</p><p><b>강조</b></p>"
            f'<embed embedtype="image" id="{image.pk}" format="fullwidth" alt="시설"/>'
        )
        post.full_clean()
        post.save_revision()
        self.client.force_login(self.admin)
        payload = self.editor_payload(post)
        self.assertIn("한글 첫 줄", json.loads(payload["body"])["blocks"][0]["text"])
        self.assertIn("IMAGE", payload["body"])
        self.assertEqual(
            self.client.post(
                reverse("wagtailsnippets_news_post:edit", args=[post.pk]), payload
            ).status_code,
            302,
        )
        self.editor_payload(post)

    def test_published_content_survives_changed_draft_including_images_and_date(self):
        old, new = picture("old.png"), picture("new.png", "white")
        post = self.publish(self.post(cover_image=old))
        date = post.first_published_at
        draft = post.get_latest_revision_as_object()
        draft.title, draft.category, draft.cover_image, draft.body = (
            "새 초안 제목",
            "events",
            new,
            "<p>새 초안 본문</p>",
        )
        draft.save_revision()
        for authenticated in [False, True]:
            if authenticated:
                self.client.force_login(self.admin)
            response = self.client.get(post.get_absolute_url())
            self.assertContains(response, "공개 제목")
            self.assertContains(response, "공개 본문")
            self.assertNotContains(response, "새 초안")
            self.assertEqual(response.context["post"].cover_image_id, old.pk)
            self.assertEqual(response.context["post"].first_published_at, date)
        self.assertEqual(published_image_ids(), {old.pk})

    def test_republish_atomically_replaces_visible_content_and_media_usage(self):
        old, new = picture("old.png"), picture("new.png", "white")
        post = self.publish(self.post(cover_image=old))
        old_url = old.get_rendition("width-80").url
        draft = post.get_latest_revision_as_object()
        draft.title, draft.body, draft.cover_image = (
            "재공개 제목",
            "<p>재공개 본문</p>",
            new,
        )
        revision = draft.save_revision()
        revision.publish(user=self.admin)
        response = self.client.get(post.get_absolute_url())
        self.assertContains(response, "재공개 제목")
        self.assertContains(response, "재공개 본문")
        self.assertNotContains(response, "<p>공개 본문</p>")
        self.assertEqual(self.client.get(old_url).status_code, 404)
        self.assertEqual(
            self.client.get(new.get_rendition("width-80").url).status_code, 200
        )

    def test_unpublish_revokes_public_html_and_all_renditions(self):
        image = picture()
        post = self.publish(self.post(cover_image=image))
        url = image.get_rendition("width-80").url
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("wagtailsnippets_news_post:unpublish", args=[post.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 404)
        self.assertNotContains(self.client.get(reverse("news:list")), post.title)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_original_draft_and_thumbnail_require_real_editor_permission(self):
        image = picture()
        urls = [image.file.url, image.get_rendition("max-165x165").url]
        outsider = get_user_model().objects.create_user(
            "staff-without-permission", is_staff=True
        )
        for user in [None, outsider, self.admin]:
            self.client.logout()
            if user:
                self.client.force_login(user)
            for url in urls:
                self.assertEqual(
                    self.client.get(url).status_code, 200 if user == self.admin else 404
                )
        self.publish(self.post(cover_image=image))
        self.client.logout()
        self.assertEqual(self.client.get(image.file.url).status_code, 404)
        self.assertEqual(self.client.get(urls[1]).status_code, 200)
        self.assertEqual(
            self.client.get(f"/images/invalid/{image.pk}/width-80/").status_code, 404
        )

    def test_shared_image_remains_available_until_last_public_use_is_withdrawn(self):
        image = picture()
        first, second = (
            self.publish(self.post(cover_image=image)),
            self.publish(self.post(cover_image=image)),
        )
        url = image.get_rendition("width-80").url
        first.unpublish()
        self.assertEqual(self.client.get(url).status_code, 200)
        second.unpublish()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_body_image_reference_controls_public_rendition_access(self):
        image = picture()
        post = self.post()
        post.body = f'<p>본문 사진</p><embed embedtype="image" id="{image.pk}" format="fullwidth" alt="검수 사진"/>'
        post.full_clean()
        self.publish(post)
        response = self.client.get(post.get_absolute_url())
        soup = BeautifulSoup(response.content, "html.parser")
        url = soup.select_one(".post-body img")["src"]
        self.assertEqual(self.client.get(url).status_code, 200)
        post.unpublish()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_replacing_original_file_is_rejected_and_old_bytes_remain(self):
        image = picture()
        old_path = Path(image.file.path)
        old_bytes = old_path.read_bytes()
        buffer = io.BytesIO()
        PILImage.new("RGB", (80, 60), "white").save(buffer, format="PNG")
        image.file = SimpleUploadedFile(
            image.file.name, buffer.getvalue(), content_type="image/png"
        )
        with self.assertRaises(ValidationError):
            image.save()
        self.assertEqual(old_path.read_bytes(), old_bytes)

    def test_preview_permission_and_draft_rendering_do_not_change_publication(self):
        post = self.publish(self.post())
        draft = post.get_latest_revision_as_object()
        draft.title = "초안 미리보기 제목"
        draft.save_revision()
        request = RequestFactory().get("/admin/preview/")
        request.user = self.admin
        response = draft.serve_preview(request, "")
        response.render()
        self.assertContains(response, "초안 미리보기 제목")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertContains(self.client.get(post.get_absolute_url()), "공개 제목")
        request.user = get_user_model().objects.create_user("no-preview-permission")
        with self.assertRaises(PermissionDenied):
            draft.serve_preview(request, "")
        url = reverse("wagtailsnippets_news_post:preview_on_edit", args=[post.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(request.user)
        self.assertIn(self.client.get(url).status_code, [302, 403])

    def test_body_strips_scripts_and_unsafe_links_without_removing_allowed_formatting(
        self,
    ):
        post = self.post()
        post.body = '<p><strong>한글 강조</strong><script>alert(1)</script><a href="javascript:alert(1)" onclick="alert(1)">링크</a></p>'
        post.full_clean()
        self.publish(post)
        response = self.client.get(post.get_absolute_url())
        self.assertContains(response, "<strong>한글 강조</strong>", html=True)
        body = BeautifulSoup(response.content, "html.parser").select_one(".post-body")
        self.assertIsNone(body.find("script"))
        self.assertNotContains(response, "javascript:")
        self.assertNotContains(response, "onclick")

    def test_stale_editor_form_is_rejected_instead_of_overwriting_new_revision(self):
        post = self.publish(self.post())
        self.client.force_login(self.admin)
        payload = self.editor_payload(post)
        newer = post.get_latest_revision_as_object()
        newer.title = "먼저 저장한 내용"
        revision = newer.save_revision(user=self.admin)
        response = self.client.post(
            reverse("wagtailsnippets_news_post:edit", args=[post.pk]), payload
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "더 최근 내용")
        post.refresh_from_db()
        self.assertEqual(post.latest_revision_id, revision.pk)
        self.assertEqual(post.get_latest_revision_as_object().title, "먼저 저장한 내용")

    def test_current_editor_form_can_save_and_publish(self):
        post = self.publish(self.post())
        self.client.force_login(self.admin)
        payload = self.editor_payload(post)
        payload["action-publish"] = "1"
        response = self.client.post(
            reverse("wagtailsnippets_news_post:edit", args=[post.pk]), payload
        )
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(post.get_absolute_url()), "수정 제목")

    def test_unauthorized_mutation_and_csrf_fail_without_creating_content(self):
        add_url = reverse("wagtailsnippets_news_post:add")
        response = self.client.post(
            add_url, {"title": "무권한 글", "category": "notices"}
        )
        self.assertEqual(response.status_code, 302)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        self.assertEqual(
            csrf_client.post(add_url, {"title": "CSRF 글"}).status_code, 403
        )
        self.assertEqual(Post.objects.count(), 0)

    def test_categories_branch_context_and_empty_state_remain_usable(self):
        branch = Branch.objects.create(
            key="second",
            name="선택 지점 예시",
            address="주소 예시",
            opening_hours="시간 예시",
            phone="전화 예시",
        )
        branch.save_revision().publish()
        post = self.publish(self.post(category="events"))
        response = self.client.get(
            reverse("news:list"), {"category": "notices", "branch": "second"}
        )
        self.assertContains(response, "등록된 소식이 없습니다")
        self.assertContains(response, "contact-second")
        self.assertNotContains(response, post.title)
        response = self.client.get(
            reverse("news:list"), {"category": "unknown", "branch": "invalid"}
        )
        self.assertContains(response, post.title)
        self.assertContains(response, "#contact-second")

    def test_bootstrap_is_idempotent_and_does_not_reset_user_edits_or_credentials(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            override_settings(BASE_DIR=Path(directory)),
        ):
            output = io.StringIO()
            call_command("bootstrap_review", stdout=output)
            credentials = (Path(directory) / ".local-credentials").read_bytes()
            post = Post.objects.first()
            post.title = "사용자가 편집한 제목"
            post.save_revision()
            call_command("bootstrap_review", stdout=output)
            self.assertEqual(Post.objects.count(), 2)
            self.assertEqual(
                post.get_latest_revision_as_object().title, "사용자가 편집한 제목"
            )
            self.assertEqual(
                (Path(directory) / ".local-credentials").read_bytes(), credentials
            )
            self.assertNotIn("password", output.getvalue())
