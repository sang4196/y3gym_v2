import json
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import (
    Client,
    RequestFactory,
    SimpleTestCase,
    TestCase,
    override_settings,
)

from news.contacts import kakao_chat_href, validate_kakao_chat_url
from news.models import Branch, Trainer
from news.publication import published_branches
from news.tests import test_branches as branch_helpers

MAIN = "https://pf.kakao.com/_TESTMain/chat"
SECOND = "https://pf.kakao.com/_TESTSecond/chat"
DRAFT = "https://pf.kakao.com/_TESTDraft/chat"


class KakaoURLTests(SimpleTestCase):
    def test_exact_chat_urls_and_optional_empty_value(self):
        for value in [MAIN, SECOND, "https://pf.kakao.com/_aB09/chat"]:
            self.assertEqual(kakao_chat_href(value), value)
            validate_kakao_chat_url(value)
        self.assertEqual(kakao_chat_href(""), "")
        validate_kakao_chat_url("")

    def test_unsafe_or_non_chat_urls_are_rejected_without_repair(self):
        for value in [
            None,
            123,
            " ",
            " " + MAIN,
            MAIN + " ",
            MAIN + "\n",
            MAIN + "\r",
            MAIN + "\t",
            MAIN + "\x00",
            MAIN + "?x=1",
            MAIN + "#chat",
            MAIN + "/",
            MAIN + "/extra",
            "https://pf.kakao.com/_TESTMain",
            "http://pf.kakao.com/_TESTMain/chat",
            "//pf.kakao.com/_TESTMain/chat",
            "javascript:alert(1)",
            "https://pf.kakao.com.evil.test/_TESTMain/chat",
            "https://evil.test/pf.kakao.com/_TESTMain/chat",
            "https://user@pf.kakao.com/_TESTMain/chat",
            "https://pf.kakao.com@evil.test/_TESTMain/chat",
            "https://pf.kakao.com:443/_TESTMain/chat",
            "https://PF.KAKAO.COM/_TESTMain/chat",
            "HTTPS://pf.kakao.com/_TESTMain/chat",
            "https://pf.kakao.com//_TESTMain/chat",
            "https://pf.kakao.com/_/chat",
            "https://pf.kakao.com/TESTMain/chat",
            "https://pf.kakao.com/_한글/chat",
            "https://pf.kakao.com/_%54EST/chat",
            "https://pf.kakao.com/_TEST/../chat",
            "https://pf.kakao.com\\evil.test/_TESTMain/chat",
            "https://pf.kakao.com/_" + "a" * 129 + "/chat",
            "x" * 501,
        ]:
            with self.subTest(value=value):
                self.assertEqual(kakao_chat_href(value), "")
                with self.assertRaises(ValidationError):
                    validate_kakao_chat_url(value)


class KakaoContactTests(TestCase):
    branch = branch_helpers.BranchTests.branch
    publish = branch_helpers.BranchTests.publish
    payload = branch_helpers.BranchTests.payload
    edit_url = branch_helpers.BranchTests.edit_url

    def setUp(self):
        Path(settings.BASE_DIR).mkdir(parents=True, exist_ok=True)
        directory = tempfile.TemporaryDirectory(dir=settings.BASE_DIR)
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.admin = get_user_model().objects.create_superuser(
            "kakao-test-admin", password="test-password"
        )

    def soup(self, path="/branches/?branch=main"):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return BeautifulSoup(response.content, "html.parser")

    def chat(self, soup, key):
        return soup.select_one(f'#contact-{key} a[href^="https://pf.kakao.com/"]')

    def test_public_targets_are_fixed_to_each_revision_with_safe_native_attributes(
        self,
    ):
        main = self.publish(
            self.branch(
                kakao_chat_url=MAIN,
                phone="02-0000-0000",
                channel="안내 <script>x</script>",
            )
        )
        self.publish(self.branch("second", kakao_chat_url=SECOND))
        before = main.live_revision.content.copy()
        for selected in ["main", "second", "unknown"]:
            soup = self.soup("/branches/?branch=" + selected)
            for key, value in [("main", MAIN), ("second", SECOND)]:
                link = self.chat(soup, key)
                self.assertEqual(link["href"], value)
                self.assertEqual(link["target"], "_blank")
                self.assertEqual(set(link["rel"]), {"noopener", "noreferrer"})
                self.assertEqual(link.get_text(), "카카오톡 문의")
                self.assertNotIn("data-preview-contact", link.attrs)
                self.assertNotIn("data-branch-page", link.attrs)
            self.assertFalse(
                soup.select(
                    "[data-preview-contact], [data-contact-feedback], .location-information script"
                )
            )
            self.assertEqual(
                soup.select_one('#contact-main a[href^="tel:"]')["href"],
                "tel:+82200000000",
            )
            self.assertIn(
                "안내 <script>x</script>",
                soup.select_one("#contact-main .location-details").get_text(),
            )
        main.refresh_from_db()
        self.assertEqual(main.live_revision.content, before)

    def test_missing_old_revision_field_never_borrows_base_or_latest_url(self):
        main = self.publish(
            self.branch(channel="기존 안내", address_detail="기존 상세")
        )
        revision = main.live_revision
        old = revision.content.copy()
        old.pop("kakao_chat_url")
        type(revision).objects.filter(pk=revision.pk).update(content=old)
        Branch.objects.filter(pk=main.pk).update(kakao_chat_url=MAIN)
        main.refresh_from_db()
        revision.refresh_from_db()
        draft = revision.as_object()
        self.assertEqual(draft.kakao_chat_url, "")
        draft.kakao_chat_url = DRAFT
        draft.save_revision()
        public = published_branches()[0]
        self.assertEqual(public.kakao_chat_url, "")
        self.assertEqual(public.address_detail, "기존 상세")
        self.assertEqual(public.key, "main")
        self.assertIsNone(self.chat(self.soup(), "main"))
        revision.refresh_from_db()
        self.assertEqual(revision.content, old)
        revision.publish()
        self.assertIsNone(self.chat(self.soup(), "main"))

    def test_actual_admin_draft_reentry_preview_permissions_publish_and_withdraw(self):
        main = self.publish(self.branch(kakao_chat_url=MAIN))
        self.publish(self.branch("second", kakao_chat_url=SECOND))
        old = main.live_revision_id
        self.client.force_login(self.admin)
        data = self.payload(main)
        data["kakao_chat_url"] = DRAFT
        self.assertEqual(self.client.post(self.edit_url(main), data).status_code, 302)
        self.assertEqual(self.payload(main)["kakao_chat_url"], DRAFT)
        self.assertEqual(self.chat(self.soup(), "main")["href"], MAIN)
        draft = Branch.objects.get(pk=main.pk).get_latest_revision_as_object()
        request = RequestFactory().get("/branches/")
        request.user = self.admin
        response = draft.serve_preview(request, "")
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertEqual(self.chat(soup, "main")["href"], DRAFT)
        self.assertEqual(self.chat(soup, "second")["href"], SECOND)
        self.assertIn("private, no-store", response.headers["Cache-Control"])
        request.user = get_user_model().objects.create_user("outsider", is_staff=True)
        with self.assertRaises(PermissionDenied):
            draft.serve_preview(request, "")
        main.refresh_from_db()
        self.assertEqual(main.live_revision_id, old)
        data = self.payload(main)
        data["action-publish"] = "1"
        self.assertEqual(self.client.post(self.edit_url(main), data).status_code, 302)
        self.assertEqual(self.chat(self.soup(), "main")["href"], DRAFT)
        self.assertEqual(self.chat(self.soup(), "second")["href"], SECOND)
        main.refresh_from_db()
        main.unpublish()
        self.assertIsNone(self.chat(self.soup(), "main"))
        self.assertEqual(self.chat(self.soup(), "second")["href"], SECOND)

    def test_invalid_form_and_publication_fail_without_normalization_or_new_revision(
        self,
    ):
        branch = self.publish(self.branch(kakao_chat_url=MAIN))
        self.client.force_login(self.admin)
        for value in [
            " " + MAIN,
            MAIN + "\n",
            "https://pf.kakao.com/_TESTMain",
            "javascript:alert(1)",
        ]:
            with self.subTest(value=value):
                branch.refresh_from_db()
                latest = branch.latest_revision_id
                data = self.payload(branch)
                data["kakao_chat_url"] = value
                response = self.client.post(self.edit_url(branch), data)
                self.assertEqual(response.status_code, 200)
                self.assertIn("kakao_chat_url", response.context["form"].errors)
                self.assertEqual(response.context["form"].data["kakao_chat_url"], value)
                branch.refresh_from_db()
                self.assertEqual(branch.latest_revision_id, latest)
                branch.kakao_chat_url = value
                with self.assertRaises(ValidationError):
                    branch.save_revision().publish()

    def test_url_only_common_home_mobile_news_trainer_use_public_branch_without_fallback(
        self,
    ):
        main = self.publish(self.branch(kakao_chat_url=MAIN))
        self.publish(self.branch("second", channel="안내만 <script>x</script>"))
        Trainer.objects.create(
            name="TEST 트레이너", branch=main
        ).save_revision().publish()
        draft = main.get_latest_revision_as_object()
        draft.kakao_chat_url = DRAFT
        draft.save_revision()
        for path in ["/", "/branches/", "/news/"]:
            soup = self.soup(path + "?branch=main")
            nav = json.loads(soup.select_one("#branch-navigation-data").string)
            self.assertTrue(nav[0]["channel"])
            self.assertFalse(nav[1]["channel"])
            for link in soup.select('a[data-inquiry="channel"]'):
                self.assertFalse(link.has_attr("hidden"))
                self.assertTrue(link["href"].endswith("?branch=main#contact-main"))
            self.assertNotIn(DRAFT, str(soup))
        soup = self.soup()
        self.assertEqual(
            soup.select_one('.trainer a[href^="#contact-"]')["href"], "#contact-main"
        )
        self.assertIsNone(self.chat(soup, "second"))
        self.assertIn(
            "안내만 <script>x</script>", soup.select_one("#contact-second").get_text()
        )
        for path in [
            "/?branch=second",
            "/branches/?branch=second",
            "/news/?branch=second",
        ]:
            self.assertTrue(
                self.soup(path)
                .select_one('[data-inquiry="channel"]')
                .has_attr("hidden")
            )

    def test_corrupt_public_url_is_suppressed_and_empty_contact_zero_branches_are_optional(
        self,
    ):
        branch = self.publish(self.branch(kakao_chat_url=MAIN))
        revision = branch.live_revision
        for value in [
            "javascript:alert(1)",
            MAIN + "?x=1",
            "",
            "https://pf.kakao.com/_TESTMain",
        ]:
            with self.subTest(value=value):
                content = revision.content.copy()
                content["kakao_chat_url"] = value
                type(revision).objects.filter(pk=revision.pk).update(content=content)
                soup = self.soup()
                self.assertIsNone(self.chat(soup, "main"))
                self.assertTrue(
                    soup.select_one('[data-inquiry="channel"]').has_attr("hidden")
                )
        draft = branch.get_latest_revision_as_object()
        draft.kakao_chat_url = ""
        draft.channel = ""
        draft.save_revision().publish()
        branch.refresh_from_db()
        self.assertFalse(self.soup().select(".location-contact-buttons"))
        branch.unpublish()
        for path in ["/", "/branches/", "/news/"]:
            soup = self.soup(path)
            self.assertFalse(
                soup.select('a[href^="https://pf.kakao.com/"],a[href^="tel:"]')
            )
            self.assertTrue(
                all(n.has_attr("hidden") for n in soup.select("[data-inquiry]"))
            )

    def test_whitespace_note_is_absent_without_rewriting_stored_text(self):
        branch = self.publish(self.branch(kakao_chat_url=MAIN, channel=" \t "))
        soup = self.soup()
        self.assertEqual(self.chat(soup, "main")["href"], MAIN)
        self.assertNotIn(
            "카카오톡", [n.get_text() for n in soup.select(".location-details dt")]
        )
        branch.refresh_from_db()
        self.assertEqual(branch.channel, " \t ")
        branch.kakao_chat_url = ""
        self.publish(branch)
        soup = self.soup()
        self.assertFalse(soup.select(".location-contact-buttons"))
        self.assertTrue(soup.select_one('[data-inquiry="channel"]').has_attr("hidden"))

    def test_new_url_obeys_existing_stale_form_csrf_publish_permission_and_lock(self):
        branch = self.publish(self.branch(kakao_chat_url=MAIN))
        self.client.force_login(self.admin)
        stale = self.payload(branch)
        draft = branch.get_latest_revision_as_object()
        draft.kakao_chat_url = DRAFT
        draft.save_revision()
        stale["kakao_chat_url"] = SECOND
        self.assertContains(
            self.client.post(self.edit_url(branch), stale), "더 최근 내용"
        )
        self.assertEqual(self.payload(branch)["kakao_chat_url"], DRAFT)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.admin)
        self.assertEqual(csrf.post(self.edit_url(branch), stale).status_code, 403)
        editor = get_user_model().objects.create_user("kakao-editor", is_staff=True)
        editor.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["access_admin", "view_branch", "change_branch"]
            )
        )
        self.client.force_login(editor)
        data = self.payload(branch)
        data.update(kakao_chat_url=SECOND, **{"action-publish": "1"})
        self.client.post(self.edit_url(branch), data)
        self.assertEqual(self.chat(self.soup(), "main")["href"], MAIN)
        branch.refresh_from_db()
        branch.locked, branch.locked_by = True, self.admin
        branch.save(update_fields=["locked", "locked_by"])
        latest = branch.latest_revision_id
        data = self.payload(branch)
        data["kakao_chat_url"] = SECOND
        self.client.post(self.edit_url(branch), data)
        branch.refresh_from_db()
        self.assertEqual(branch.latest_revision_id, latest)
