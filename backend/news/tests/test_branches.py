import tempfile
from pathlib import Path

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from news.models import Branch, BrandContent, FacilityImage, Post
from news.publication import published_branches, published_image_ids
from news.tests.test_publication import picture


class BranchTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.admin = get_user_model().objects.create_superuser(
            "branches-admin", password="test-password"
        )

    def branch(self, key="main", **kwargs):
        return Branch.objects.create(
            key=key,
            name="검토 본점" if key == "main" else "검토 " + key,
            address="임시 주소",
            opening_hours="평일 운영시간 예시",
            **kwargs,
        )

    def publish(self, branch):
        branch.save_revision(user=self.admin).publish(user=self.admin)
        branch.refresh_from_db()
        return branch

    def edit_url(self, branch):
        return reverse("wagtailsnippets_news_branch:edit", args=[branch.pk])

    def payload(self, branch):
        soup = BeautifulSoup(
            self.client.get(self.edit_url(branch)).content, "html.parser"
        )
        fields = [
            "name",
            "intro",
            "address",
            "address_detail",
            "opening_hours",
            "phone",
            "channel",
            "kakao_chat_url",
            "display_order",
            "loaded_revision_id",
            "loaded_revision_created_at",
            "facilities-TOTAL_FORMS",
            "facilities-INITIAL_FORMS",
            "facilities-MIN_NUM_FORMS",
            "facilities-MAX_NUM_FORMS",
        ]
        data = {}
        for name in fields:
            element = soup.find(attrs={"name": name})
            self.assertIsNotNone(element, name)
            data[name] = (
                element.text.removeprefix("\n")
                if element.name == "textarea"
                else element.get("value", "")
            )
        count = int(data["facilities-TOTAL_FORMS"])
        for i in range(count):
            for element in soup.select(f'[name^="facilities-{i}-"]'):
                if element.get("type") == "checkbox" and not element.has_attr(
                    "checked"
                ):
                    continue
                data[element["name"]] = (
                    element.text.removeprefix("\n")
                    if element.name == "textarea"
                    else element.get("value", "")
                )
        return data

    def test_blank_draft_is_private_and_publication_checks_requested_revision(self):
        branch = Branch.objects.create()
        revision = branch.save_revision()
        for path in ["/", "/branches/", "/news/"]:
            response = self.client.get(path)
            self.assertNotContains(response, branch.key)
            soup = BeautifulSoup(response.content, "html.parser")
            self.assertTrue(
                all(
                    control.has_attr("hidden")
                    for control in soup.select("[data-inquiry]")
                )
            )
        with self.assertRaises(ValidationError):
            revision.publish()
        for field in ["name", "address", "opening_hours"]:
            branch.name, branch.address, branch.opening_hours = "지점", "주소", "시간"
            setattr(branch, field, " \n ")
            with self.assertRaises(ValidationError):
                branch.save_revision().publish()

    def test_clustered_revision_preserves_deleted_children_order_images_and_parent(
        self,
    ):
        old, other, draft_image = (
            picture("live.png"),
            picture("other.png"),
            picture("draft.png"),
        )
        branch = self.branch()
        branch.facilities = [
            FacilityImage(image=old, title="공개 첫 사진", sort_order=0),
            FacilityImage(image=other, title="공개 둘째 사진", sort_order=1),
        ]
        self.publish(branch)
        old_revision = branch.live_revision_id
        draft = branch.get_latest_revision_as_object()
        draft.address, draft.display_order = "노출 금지 주소", 99
        draft.facilities = [
            FacilityImage(image=draft_image, title="새 초안 사진", sort_order=0)
        ]
        draft.save_revision(user=self.admin)
        # Even a mutable child-table edit must not redefine the public snapshot.
        FacilityImage.objects.filter(branch=branch).delete()
        self.assertEqual(
            [item.title for item in published_branches()[0].facilities.all()],
            ["공개 첫 사진", "공개 둘째 사진"],
        )
        for path in ["/", "/branches/"]:
            response = self.client.get(path)
            self.assertContains(response, "공개 첫 사진")
            self.assertContains(response, "공개 둘째 사진")
            self.assertNotContains(response, "새 초안 사진")
            self.assertNotContains(response, "노출 금지 주소")
        self.assertEqual(published_image_ids(), {old.pk, other.pk})
        self.assertEqual(
            self.client.get(draft_image.get_rendition("width-80").url).status_code, 404
        )
        branch.refresh_from_db()
        self.assertEqual(branch.live_revision_id, old_revision)
        branch.get_latest_revision().publish()
        self.assertContains(self.client.get("/branches/"), "새 초안 사진")
        self.assertEqual(published_image_ids(), {draft_image.pk})

    def test_preview_uses_inline_draft_and_requires_editor_and_no_store(self):
        branch = self.publish(self.branch())
        image = picture("preview.png")
        draft = branch.get_latest_revision_as_object()
        draft.name = "미공개 지점 수정"
        draft.facilities = [
            FacilityImage(image=image, title="미공개 사진", sort_order=0)
        ]
        draft.save_revision()
        request = RequestFactory().get("/branches/")
        request.user = self.admin
        response = draft.serve_preview(request, "")
        self.assertContains(response, "미공개 지점 수정")
        self.assertContains(response, "미공개 사진")
        self.assertIn("private, no-store", response.headers["Cache-Control"])
        image_url = BeautifulSoup(response.content, "html.parser").select_one(
            "[data-gallery-slide] img"
        )["src"]
        self.assertEqual(self.client.get(image_url).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(image_url).status_code, 200)
        request.user = get_user_model().objects.create_user("outsider", is_staff=True)
        with self.assertRaises(PermissionDenied):
            draft.serve_preview(request, "")

    def test_withdraw_and_republish_restore_only_the_requested_revision_and_media(self):
        image = picture("republish.png")
        branch = self.branch()
        branch.facilities = [
            FacilityImage(image=image, title="보존할 시설", sort_order=0)
        ]
        self.publish(branch)
        url = image.get_rendition("width-80").url
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(
                reverse("wagtailsnippets_news_branch:unpublish", args=[branch.pk])
            ).status_code,
            302,
        )
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertContains(self.client.get("/branches/"), "지점 안내를 준비 중입니다.")
        branch.refresh_from_db()
        draft = branch.get_latest_revision_as_object()
        draft.name = "재공개 지점"
        draft.save_revision().publish()
        self.assertContains(self.client.get("/branches/"), "재공개 지점")
        self.assertContains(self.client.get("/branches/"), "보존할 시설")
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(Branch.objects.count(), 1)

    def test_main_first_and_additional_order_use_public_snapshot_and_stable_id(self):
        first = self.publish(self.branch("third", display_order=0))
        second = self.publish(self.branch("second", display_order=0))
        main = self.publish(self.branch("main", display_order=100))
        self.assertEqual(
            [branch.key for branch in published_branches()], ["main", "third", "second"]
        )
        draft = second.get_latest_revision_as_object()
        draft.display_order = 200
        draft.save_revision()
        self.assertEqual(
            [branch.key for branch in published_branches()], ["main", "third", "second"]
        )
        main.unpublish()
        self.assertEqual(published_branches()[0].pk, first.pk)
        main.key = "another-main"
        with self.assertRaises(ValidationError):
            main.save()

    def test_dynamic_new_branch_selection_and_invalid_or_withdrawn_fallback(self):
        main = self.publish(self.branch())
        third = self.publish(self.branch("third", phone="모의 전화"))
        for path in ["/", "/branches/", "/news/"]:
            response = self.client.get(path, {"branch": "third"})
            self.assertContains(response, "?branch=third")
            self.assertNotContains(response, "http://localhost:8767")
            self.assertEqual(
                response.context["branch"] if response.context else "third", "third"
            )
        for bad in ["unknown", "third"]:
            if bad == "third":
                third.unpublish()
            soup = BeautifulSoup(
                self.client.get("/news/", {"branch": bad}).content, "html.parser"
            )
            self.assertEqual(
                soup.select_one(".site-header .wordmark")["href"], reverse("home")
            )
            self.assertIn(
                "branch=main",
                soup.select_one(".primary-navigation a[data-branch-page]")["href"],
            )
        main.unpublish()
        for path in ["/", "/branches/", "/news/"]:
            response = self.client.get(path)
            soup = BeautifulSoup(response.content, "html.parser")
            self.assertTrue(
                all(
                    control.has_attr("hidden")
                    for control in soup.select("[data-inquiry]")
                )
            )
            self.assertContains(response, "/news/")
        self.assertContains(self.client.get("/branches/"), "지점 안내를 준비 중입니다.")
        self.assertEqual(Branch.objects.count(), 2)

    def test_optional_photos_trainers_and_channels_hide_without_faking_content(self):
        branch = self.branch(phone="전화 예시")
        branch.facilities = [FacilityImage(title="이미지 없는 항목", sort_order=0)]
        self.publish(branch)
        for path in ["/", "/branches/", "/news/"]:
            soup = BeautifulSoup(self.client.get(path).content, "html.parser")
            self.assertFalse(
                soup.select("[data-facility-gallery], .trainers, [data-gallery-slide]")
            )
            self.assertTrue(
                soup.select_one('[data-inquiry="channel"]').has_attr("hidden")
            )
            self.assertFalse(
                soup.select_one('[data-inquiry="phone"]').has_attr("hidden")
            )
        branch.phone, branch.channel = "", "카카오톡 예시"
        self.publish(branch)
        soup = BeautifulSoup(self.client.get("/branches/").content, "html.parser")
        self.assertTrue(soup.select_one('[data-inquiry="phone"]').has_attr("hidden"))
        self.assertTrue(soup.select_one('[data-inquiry="channel"]').has_attr("hidden"))
        self.assertIn("카카오톡 예시", soup.select_one(".location-details").get_text())
        self.assertFalse(
            soup.select('[href^="tel:"], [href*="kakao"]:not([data-map-link])')
        )

    def test_shared_image_survives_until_last_public_post_brand_or_branch_use(self):
        image = picture()
        branch = self.branch()
        branch.facilities = [FacilityImage(image=image, sort_order=0)]
        self.publish(branch)
        post = Post.objects.create(title="공유 소식", cover_image=image, live=False)
        post.save_revision().publish()
        post.refresh_from_db()
        brand = BrandContent.objects.create(
            name="공유 브랜드", intro_title="공유 소개", hero_image=image
        )
        brand.save_revision().publish()
        brand.refresh_from_db()
        url = image.get_rendition("width-80").url
        self.assertEqual(self.client.get(image.file.url).status_code, 404)
        branch.unpublish()
        post.unpublish()
        self.assertEqual(self.client.get(url).status_code, 200)
        brand.unpublish()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_real_admin_inline_draft_reopen_preview_publish_and_reorder(self):
        image = picture()
        branch = self.publish(self.branch())
        self.client.force_login(self.admin)
        data = self.payload(branch)
        data.update(
            name="編集中の支店",
            **{
                "facilities-TOTAL_FORMS": 1,
                "facilities-0-id": "",
                "facilities-0-image": image.pk,
                "facilities-0-title": "시설 초안",
                "facilities-0-description": "사진 설명",
                "facilities-0-alt": "대체 설명",
                "facilities-0-position_x": 40,
                "facilities-0-position_y": 60,
                "facilities-0-ORDER": 0,
            },
        )
        self.assertEqual(self.client.post(self.edit_url(branch), data).status_code, 302)
        branch.refresh_from_db()
        self.assertEqual(self.payload(branch)["facilities-0-title"], "시설 초안")
        self.assertNotContains(self.client.get("/branches/"), "시설 초안")
        preview = reverse(
            "wagtailsnippets_news_branch:preview_on_edit", args=[branch.pk]
        )
        self.assertEqual(
            self.client.post(preview, self.payload(branch)).status_code, 200
        )
        self.assertContains(self.client.get(preview), "시설 초안")
        data = self.payload(branch)
        data["action-publish"] = "1"
        self.assertEqual(self.client.post(self.edit_url(branch), data).status_code, 302)
        self.assertContains(self.client.get("/branches/"), "시설 초안")

    def test_admin_incomplete_draft_and_invalid_publish_preserve_input(self):
        branch = self.publish(self.branch())
        self.client.force_login(self.admin)
        data = self.payload(branch)
        data.update(
            name=" ",
            address="",
            opening_hours="",
            intro="입력 보존",
            **{"action-publish": "1"},
        )
        response = self.client.post(self.edit_url(branch), data)
        self.assertContains(response, "공개하려면 입력해 주세요.")
        self.assertContains(response, "입력 보존")
        data.pop("action-publish")
        self.assertEqual(self.client.post(self.edit_url(branch), data).status_code, 302)
        self.assertEqual(published_branches()[0].name, "검토 본점")

    def test_permission_csrf_lock_stale_form_and_delete_boundaries(self):
        branch = self.publish(self.branch())
        self.client.force_login(self.admin)
        stale = self.payload(branch)
        newer = branch.get_latest_revision_as_object()
        newer.name = "더 최신 수정"
        newer.save_revision()
        self.assertContains(
            self.client.post(self.edit_url(branch), stale), "더 최근 내용"
        )
        guarded = Client(enforce_csrf_checks=True)
        guarded.force_login(self.admin)
        self.assertEqual(guarded.post(self.edit_url(branch), stale).status_code, 403)
        editor = get_user_model().objects.create_user("branch-editor", is_staff=True)
        editor.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["access_admin", "view_branch", "change_branch"]
            )
        )
        self.client.force_login(editor)
        data = self.payload(branch)
        data.update(name="권한 없는 공개", **{"action-publish": "1"})
        self.client.post(self.edit_url(branch), data)
        self.assertEqual(published_branches()[0].name, "검토 본점")
        branch.refresh_from_db()
        branch.locked, branch.locked_by = True, self.admin
        branch.save(update_fields=["locked", "locked_by"])
        latest = branch.latest_revision_id
        data = self.payload(branch)
        data["name"] = "잠금 무시"
        self.client.post(self.edit_url(branch), data)
        branch.refresh_from_db()
        self.assertEqual(branch.latest_revision_id, latest)
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(
                reverse("wagtailsnippets_news_branch:delete", args=[branch.pk])
            ).status_code,
            302,
        )
        self.assertTrue(Branch.objects.filter(pk=branch.pk).exists())
        outsider = get_user_model().objects.create_user(
            "branch-outsider", is_staff=True
        )
        outsider.user_permissions.add(Permission.objects.get(codename="access_admin"))
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(self.edit_url(branch)).status_code, 302)

    def test_fixture_is_idempotent_and_keeps_existing_drafts_and_other_content(self):
        post = Post.objects.create(title="기존 글", live=False)
        post.save_revision()
        with override_settings(BASE_DIR=Path(self.directory)):
            call_command("bootstrap_branch_review", verbosity=0)
            branch = Branch.objects.get(key="main")
            draft = branch.get_latest_revision_as_object()
            draft.address = "사용자 수정 보존"
            draft.save_revision()
            revision = branch.live_revision_id
            images = published_image_ids()
            call_command("bootstrap_branch_review", verbosity=0)
        branch.refresh_from_db()
        self.assertEqual(
            branch.get_latest_revision_as_object().address, "사용자 수정 보존"
        )
        self.assertEqual(branch.live_revision_id, revision)
        self.assertEqual(Branch.objects.count(), 2)
        self.assertEqual(published_image_ids(), images)
        self.assertEqual(Post.objects.get(pk=post.pk).title, "기존 글")

    def test_plain_text_escaping_and_focal_point_validation(self):
        branch = self.branch()
        branch.name = '<script>alert("branch")</script>'
        self.publish(branch)
        for path in ["/", "/branches/"]:
            self.assertNotContains(self.client.get(path), branch.name)
            self.assertContains(self.client.get(path), "&lt;script&gt;")
        item = FacilityImage(position_x=101)
        with self.assertRaises(ValidationError):
            item.full_clean(exclude=["branch"])
