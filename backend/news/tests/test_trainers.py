import tempfile
from pathlib import Path

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from news.models import (
    Branch,
    BrandContent,
    FacilityImage,
    Post,
    Trainer,
    TrainerBiography,
)
from news.publication import published_image_ids, published_trainers
from news.tests.test_publication import picture


class TrainerTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.admin = get_user_model().objects.create_superuser(
            "trainers-admin", password="test-password"
        )
        self.main = self.branch("main")
        self.second = self.branch("second")

    def branch(self, key, publish=True):
        branch = Branch.objects.create(
            key=key,
            name="검수 지점 " + key,
            address="공개 주소 " + key,
            opening_hours="공개 시간",
        )
        if publish:
            branch.save_revision().publish()
        return Branch.objects.get(pk=branch.pk)

    def trainer(self, **kwargs):
        values = {"name": "검수 트레이너", "branch": self.main}
        values.update(kwargs)
        return Trainer.objects.create(**values)

    def publish(self, trainer):
        trainer.save_revision(user=self.admin).publish(user=self.admin)
        return Trainer.objects.get(pk=trainer.pk)

    def edit_url(self, trainer):
        return reverse("wagtailsnippets_news_trainer:edit", args=[trainer.pk])

    def payload(self, trainer):
        soup = BeautifulSoup(
            self.client.get(self.edit_url(trainer)).content, "html.parser"
        )
        names = [
            "name",
            "branch",
            "display_order",
            "photo",
            "photo_alt",
            "intro",
            "position",
            "loaded_revision_id",
            "loaded_revision_created_at",
            "biography-TOTAL_FORMS",
            "biography-INITIAL_FORMS",
            "biography-MIN_NUM_FORMS",
            "biography-MAX_NUM_FORMS",
        ]
        data = {}
        for name in names:
            element = soup.find(attrs={"name": name})
            self.assertIsNotNone(element, name)
            if element.name == "select":
                option = element.find("option", selected=True)
                data[name] = option.get("value", "") if option else ""
            else:
                data[name] = (
                    element.text.removeprefix("\n")
                    if element.name == "textarea"
                    else element.get("value", "")
                )
        for index in range(int(data["biography-TOTAL_FORMS"])):
            for element in soup.select(f'[name^="biography-{index}-"]'):
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

    def test_blank_draft_and_requested_revision_publication_requirements(self):
        trainer = Trainer.objects.create()
        blank = trainer.save_revision()
        self.assertEqual(published_trainers(), [])
        with self.assertRaises(ValidationError):
            blank.publish()
        for name, branch in [(" \n ", self.main), ("이름", None)]:
            trainer.name, trainer.branch = name, branch
            with self.assertRaises(ValidationError):
                trainer.save_revision().publish()
        trainer.name, trainer.branch = "이름", self.main
        self.publish(trainer)
        with self.assertRaises(ValidationError):
            blank.publish()

    def test_all_fields_and_children_use_same_public_revision_even_after_mutable_changes(
        self,
    ):
        photo, draft_photo = picture("trainer-public.png"), picture("trainer-draft.png")
        trainer = self.trainer(
            photo=photo, intro="공개 소개", position="검수용 직급", display_order=2
        )
        trainer.biography = [
            TrainerBiography(text="공개 항목 둘", sort_order=1),
            TrainerBiography(text="공개 항목 하나", sort_order=0),
        ]
        trainer = self.publish(trainer)
        other = self.publish(self.trainer(name="다음 프로필", display_order=3))
        draft = trainer.get_latest_revision_as_object()
        draft.branch, draft.display_order, draft.photo = self.second, 99, draft_photo
        draft.name, draft.intro, draft.position = "초안 이름", "초안 소개", "초안 직급"
        draft.biography = [TrainerBiography(text="초안 약력", sort_order=0)]
        draft.save_revision()
        Trainer.objects.filter(pk=trainer.pk).update(
            branch=self.second, display_order=99, photo=draft_photo
        )
        TrainerBiography.objects.filter(trainer=trainer).delete()
        public = published_trainers()
        self.assertEqual([row.pk for row in public], [trainer.pk, other.pk])
        self.assertEqual(public[0].branch_id, self.main.pk)
        self.assertEqual(public[0].photo_id, photo.pk)
        self.assertEqual(
            [item.text for item in public[0].biography.all()],
            ["공개 항목 하나", "공개 항목 둘"],
        )
        self.client.force_login(self.admin)
        response = self.client.get("/branches/?branch=main")
        self.assertContains(response, "공개 소개")
        for secret in ["초안 이름", "초안 소개", "초안 직급", "초안 약력"]:
            self.assertNotContains(response, secret)
        self.assertIn(photo.pk, published_image_ids())
        self.assertNotIn(draft_photo.pk, published_image_ids())

    def test_move_order_publication_and_withdrawal_follow_both_public_states(self):
        first = self.publish(self.trainer(name="첫 프로필", display_order=20))
        second = self.publish(self.trainer(name="둘째 프로필", display_order=10))
        self.assertEqual(
            [row.pk for row in published_trainers()], [second.pk, first.pk]
        )
        draft = first.get_latest_revision_as_object()
        draft.branch, draft.display_order = self.second, 0
        revision = draft.save_revision()
        self.assertEqual(
            [row.branch_id for row in published_trainers()],
            [self.main.pk, self.main.pk],
        )
        revision.publish()
        self.assertEqual(
            [row.branch_id for row in published_trainers()],
            [self.second.pk, self.main.pk],
        )
        self.second.unpublish()
        self.assertEqual([row.pk for row in published_trainers()], [second.pk])
        first.refresh_from_db()
        self.assertTrue(first.live)
        self.second.save_revision().publish()
        self.assertEqual(len(published_trainers()), 2)
        first.unpublish()
        self.assertEqual([row.pk for row in published_trainers()], [second.pk])

    def test_public_cards_hide_empty_optional_parts_and_zero_trainers_and_escape_text(
        self,
    ):
        self.assertNotContains(
            self.client.get("/branches/"), 'data-branch-section="trainers"'
        )
        trainer = self.publish(
            self.trainer(name="<script>임시 검수</script>", intro=" ", position=" ")
        )
        response = self.client.get("/branches/")
        soup = BeautifulSoup(response.content, "html.parser")
        card = soup.select_one(f'[data-trainer-id="{trainer.pk}"]')
        self.assertIsNotNone(card)
        self.assertIsNone(
            card.select_one(
                "figure, [data-trainer-position], [data-trainer-intro], [data-trainer-biography], script"
            )
        )
        self.assertIn("trainer--text-only", card["class"])
        self.assertNotContains(self.client.get("/"), "data-trainer-id")
        self.assertEqual(
            [
                item["data-branch-section"]
                for item in soup.select("#branch-main [data-branch-section]")
            ],
            ["trainers", "contact"],
        )

    def test_preview_permissions_and_private_affiliation_never_leak_branch_drafts(self):
        private = self.branch("private", publish=False)
        private.address, private.opening_hours = "SECRET 주소", "SECRET 시간"
        private.facilities = [
            FacilityImage(image=picture("private-facility.png"), title="SECRET 시설")
        ]
        private.save_revision()
        trainer = self.trainer(branch=private, intro="프로필 수정본")
        trainer.biography = [TrainerBiography(text="프로필 약력 초안", sort_order=0)]
        user = get_user_model().objects.create_user("profile-only")
        user.user_permissions.add(Permission.objects.get(codename="change_trainer"))
        request = RequestFactory().get("/admin/preview/")
        request.user = user
        response = trainer.serve_preview(request, "")
        self.assertContains(response, "소속 지점 비공개")
        self.assertContains(response, "프로필 약력 초안")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        for secret in ["SECRET 주소", "SECRET 시간", "SECRET 시설"]:
            self.assertNotContains(response, secret)
        trainer.branch = None
        self.assertContains(trainer.serve_preview(request, ""), "소속 지점 미선택")
        trainer.branch = self.main
        self.assertContains(trainer.serve_preview(request, ""), "프로필 약력 초안")
        request.user = get_user_model().objects.create_user("no-profile-access")
        with self.assertRaises(PermissionDenied):
            trainer.serve_preview(request, "")

    def test_images_require_effective_public_profile_and_keep_shared_last_use(self):
        image = picture("shared-trainer.png")
        replacement = picture("hidden-profile-draft.png")
        rendition = image.get_rendition("fill-640x800")
        hidden_rendition = replacement.get_rendition("fill-640x800")
        trainer = self.publish(self.trainer(photo=image))
        self.assertEqual(self.client.get(rendition.url).status_code, 200)
        self.assertEqual(self.client.get(image.file.url).status_code, 404)
        draft = trainer.get_latest_revision_as_object()
        draft.photo = replacement
        draft.save_revision()
        self.assertEqual(self.client.get(hidden_rendition.url).status_code, 404)
        post = Post.objects.create(title="공유 소식", cover_image=image)
        post.save_revision().publish()
        brand = BrandContent.objects.create(
            name="공유 브랜드", intro_title="공유 소개", hero_image=image
        )
        brand.save_revision().publish()
        post.refresh_from_db()
        brand.refresh_from_db()
        self.main.facilities = [FacilityImage(image=image, sort_order=0)]
        self.main.save_revision().publish()
        self.main.unpublish()
        self.assertEqual(self.client.get(rendition.url).status_code, 200)
        post.unpublish()
        self.assertEqual(self.client.get(rendition.url).status_code, 200)
        brand.unpublish()
        self.assertEqual(self.client.get(rendition.url).status_code, 404)
        self.main.save_revision().publish()
        trainer.unpublish()
        self.assertEqual(self.client.get(rendition.url).status_code, 200)
        self.main.facilities = []
        self.main.save_revision().publish()
        self.assertEqual(self.client.get(rendition.url).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(hidden_rendition.url).status_code, 200)

    def test_editor_validation_branch_entry_initial_selection_and_draft_affiliation_list(
        self,
    ):
        self.client.force_login(self.admin)
        branch_edit = reverse("wagtailsnippets_news_branch:edit", args=[self.main.pk])
        self.assertContains(self.client.get(branch_edit), f"?branch={self.main.pk}")
        self.assertContains(
            self.client.get(reverse("wagtailsnippets_news_branch:add")),
            "먼저 지점을 초안 저장",
        )
        add = self.client.get(
            reverse("wagtailsnippets_news_trainer:add") + f"?branch={self.second.pk}"
        )
        soup = BeautifulSoup(add.content, "html.parser")
        self.assertEqual(soup.select_one("#id_branch")["value"], str(self.second.pk))
        trainer = Trainer.objects.create()
        trainer.save_revision()
        payload = self.payload(trainer)
        payload.update(
            name="  ", branch="", intro="보존할 입력", **{"action-publish": "1"}
        )
        response = self.client.post(self.edit_url(trainer), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "보존할 입력")
        trainer.refresh_from_db()
        self.assertFalse(trainer.live)
        payload.pop("action-publish")
        self.assertEqual(
            self.client.post(self.edit_url(trainer), payload).status_code, 302
        )
        trainer = self.publish(self.trainer(name="이동 대상"))
        draft = trainer.get_latest_revision_as_object()
        draft.branch = self.second
        draft.save_revision()
        index = reverse("wagtailsnippets_news_trainer:list")
        self.assertNotContains(
            self.client.get(index + f"?branch={self.main.pk}"), "이동 대상"
        )
        self.assertContains(
            self.client.get(index + f"?branch={self.second.pk}"), "이동 대상"
        )

    def test_edit_stale_form_lock_permissions_csrf_and_no_delete(self):
        trainer = self.publish(self.trainer())
        self.client.force_login(self.admin)
        stale = self.payload(trainer)
        latest = trainer.get_latest_revision_as_object()
        latest.intro = "보존할 최신 초안"
        revision = latest.save_revision()
        response = self.client.post(self.edit_url(trainer), stale)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "다른 화면에서 더 최근 내용")
        trainer.refresh_from_db()
        self.assertEqual(trainer.latest_revision_id, revision.pk)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.admin)
        self.assertEqual(
            csrf.post(self.edit_url(trainer), self.payload(trainer)).status_code, 403
        )
        editor = get_user_model().objects.create_user(
            "trainer-denied", password="test-password"
        )
        editor.user_permissions.add(
            Permission.objects.get(
                codename="access_admin", content_type__app_label="wagtailadmin"
            )
        )
        locked_payload = self.payload(trainer)
        from django.utils import timezone

        Trainer.objects.filter(pk=trainer.pk).update(
            locked=True, locked_by=editor, locked_at=timezone.now()
        )
        locked = self.client.post(self.edit_url(trainer), locked_payload)
        self.assertEqual(locked.status_code, 200)
        trainer.refresh_from_db()
        self.assertEqual(trainer.latest_revision_id, revision.pk)
        self.assertEqual(
            self.client.post(
                reverse("wagtailsnippets_news_trainer:delete", args=[trainer.pk])
            ).status_code,
            302,
        )
        self.assertTrue(Trainer.objects.filter(pk=trainer.pk).exists())
        self.client.force_login(editor)
        self.assertEqual(
            self.client.post(
                self.edit_url(trainer),
                locked_payload,
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            ).status_code,
            403,
        )

    def test_seed_is_idempotent_and_does_not_rewrite_existing_profiles_or_media(self):
        with override_settings(BASE_DIR=self.directory):
            call_command("bootstrap_trainer_review", verbosity=0)
            self.assertEqual(Trainer.objects.count(), 2)
            self.assertEqual(
                set(Trainer.objects.values_list("name", flat=True)),
                {"트레이너 A", "트레이너 B"},
            )
            before = [
                (
                    row.pk,
                    row.latest_revision_id,
                    row.live_revision_id,
                    row.photo_id,
                    row.name,
                )
                for row in Trainer.objects.all()
            ]
            file_hashes = {
                path.name: path.read_bytes() for path in self.directory.rglob("*.png")
            }
            call_command("bootstrap_trainer_review", verbosity=0)
            self.assertEqual(
                before,
                [
                    (
                        row.pk,
                        row.latest_revision_id,
                        row.live_revision_id,
                        row.photo_id,
                        row.name,
                    )
                    for row in Trainer.objects.all()
                ],
            )
            self.assertEqual(
                file_hashes,
                {
                    path.name: path.read_bytes()
                    for path in self.directory.rglob("*.png")
                },
            )
