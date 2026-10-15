import json
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from news.models import Trainer
from news.tests import test_branches as branch_helpers

CHAT = "https://pf.kakao.com/_TESTSecond/chat"


class ContactVisibilityTests(TestCase):
    branch = branch_helpers.BranchTests.branch
    publish = branch_helpers.BranchTests.publish

    def setUp(self):
        Path(settings.BASE_DIR).mkdir(parents=True, exist_ok=True)
        directory = tempfile.TemporaryDirectory(dir=settings.BASE_DIR)
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.admin = get_user_model().objects.create_superuser(
            "visibility-admin", password="test-password"
        )

    def soup(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return BeautifulSoup(response.content, "html.parser")

    def assert_controls(self, soup, phone=False, channel=False):
        allowed = {"phone": phone, "channel": channel, "any": phone or channel}
        controls = soup.select("[data-inquiry]")
        self.assertTrue(controls)
        for control in controls:
            self.assertEqual(
                control.has_attr("hidden"), not allowed[control["data-inquiry"]]
            )
        self.assertTrue(soup.select(".footer-navigation a"))

    def trainer(self, branch):
        Trainer.objects.create(
            name="[TEST] 문의", branch=branch
        ).save_revision().publish()

    def test_whitespace_and_note_only_hide_all_contact_entries_without_rewriting(self):
        branch = self.publish(self.branch("second"))
        self.trainer(branch)
        cases = ["", " \t \r\n", "\u00a0", "\u2003", "\u3000", "\u0085\u202f"]
        for raw in cases:
            with self.subTest(raw=repr(raw)):
                branch.phone = raw
                branch.channel = "[TEST] 안내 <문구>"
                self.publish(branch)
                revision_id = branch.live_revision_id
                for path in [
                    "/?branch=second",
                    "/branches/?branch=second",
                    "/news/?branch=second",
                ]:
                    soup = self.soup(path)
                    self.assert_controls(soup)
                    self.assertFalse(
                        soup.select('a[href^="tel:"], a[href^="https://pf.kakao.com/"]')
                    )
                    self.assertFalse(soup.select('.trainer a[href^="#contact-"]'))
                    metadata = json.loads(
                        soup.select_one("#branch-navigation-data").string
                    )
                    self.assertFalse(metadata[0]["phone"])
                    if path.startswith("/branches/"):
                        self.assertIn(
                            "[TEST] 안내 <문구>",
                            soup.select_one(".location-details").get_text(),
                        )
                        self.assertNotIn(
                            "전화",
                            [d.get_text() for d in soup.select(".location-details dt")],
                        )
                branch.refresh_from_db()
                self.assertEqual(branch.phone, raw)
                self.assertEqual(branch.live_revision.content["phone"], raw)
                self.assertEqual(branch.live_revision_id, revision_id)

    def test_numbers_and_free_guidance_keep_internal_contact_and_original_text(self):
        branch = self.publish(self.branch("second"))
        self.trainer(branch)
        for raw, native_count in [("010 0000 0000", 1), ("  방문 상담 <안내>  ", 0)]:
            with self.subTest(raw=raw):
                branch.phone = raw
                self.publish(branch)
                for path in ["/?branch=second", "/branches/?branch=second"]:
                    soup = self.soup(path)
                    self.assert_controls(soup, phone=True)
                    for control in soup.select('a[data-inquiry="phone"]'):
                        self.assertEqual(
                            control["href"], "/branches/?branch=second#contact-second"
                        )
                    if path.startswith("/branches/"):
                        self.assertEqual(
                            len(soup.select('a[href^="tel:"]')), native_count
                        )
                        self.assertTrue(
                            soup.select_one('.trainer a[href="#contact-second"]')
                        )
                        self.assertIn(
                            raw, soup.select_one(".location-details").get_text()
                        )
                branch.refresh_from_db()
                self.assertEqual(branch.phone, raw)
                self.assertEqual(branch.live_revision.content["phone"], raw)

    def test_url_only_branch_has_channel_and_any_but_no_phone_or_main_fallback(self):
        self.publish(self.branch(phone="02-0000-0000"))
        second = self.publish(
            self.branch("second", phone=" \u3000 ", kakao_chat_url=CHAT)
        )
        self.trainer(second)
        for path in [
            "/?branch=second",
            "/branches/?branch=second",
            "/news/?branch=second",
        ]:
            soup = self.soup(path)
            self.assert_controls(soup, channel=True)
            for control in soup.select("a[data-inquiry]"):
                self.assertEqual(
                    control["href"], "/branches/?branch=second#contact-second"
                )
            if path.startswith("/branches/"):
                self.assertTrue(soup.select_one('.trainer a[href="#contact-second"]'))
                self.assertFalse(soup.select('#contact-second a[href^="tel:"]'))
                self.assertEqual(
                    soup.select_one('#contact-second a[href^="https://pf.kakao.com/"]')[
                        "href"
                    ],
                    CHAT,
                )

    def test_whitespace_draft_preview_and_public_revision_availability_are_separate(
        self,
    ):
        main = self.publish(self.branch(phone="02-0000-0000"))
        original = main.live_revision_id
        draft = main.get_latest_revision_as_object()
        draft.phone = "\u00a0\t\u3000"
        revision = draft.save_revision(user=self.admin)
        self.assert_controls(self.soup("/branches/?branch=main"), phone=True)
        request = RequestFactory().get("/branches/?branch=main")
        request.user = self.admin
        response = draft.serve_preview(request, "")
        self.assert_controls(BeautifulSoup(response.content, "html.parser"))
        self.assertIn("private, no-store", response.headers["Cache-Control"])
        main.refresh_from_db()
        self.assertEqual(main.live_revision_id, original)
        revision.publish(user=self.admin)
        for path in ["/", "/branches/"]:
            self.assert_controls(self.soup(path))
        main.refresh_from_db()
        self.assertEqual(main.phone, draft.phone)

    def test_withdrawn_main_then_zero_branches_keep_navigation_without_contacts(self):
        main = self.publish(self.branch(phone="02-0000-0000"))
        second = self.publish(self.branch("second", phone=" \t "))
        main.unpublish()
        for path in ["/", "/branches/", "/news/"]:
            soup = self.soup(path)
            self.assert_controls(soup)
            self.assertFalse(soup.select_one("#branch-main"))
            self.assertTrue(soup.select_one("#branch-second") or path == "/news/")
        second.unpublish()
        for path in ["/", "/branches/", "/news/"]:
            soup = self.soup(path)
            self.assert_controls(soup)
            self.assertFalse(soup.select("[data-branch-panel]"))
