import json
import tempfile

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from news.contacts import telephone_href
from news.models import Branch, Trainer


class TelephoneHrefTests(SimpleTestCase):
    def test_supported_notation_derives_global_targets(self):
        cases = {
            "02-0000-0000": "tel:+82200000000",
            "02.000.0000": "tel:+8220000000",
            "(02)0000-0000": "tel:+82200000000",
            "031 000 0000": "tel:+82310000000",
            "064-0000-0000": "tel:+826400000000",
            "010 0000 0000": "tel:+821000000000",
            "011-000-0000": "tel:+82110000000",
            "01900000000": "tel:+821900000000",
            " +82 (10) 0000-0000 ": "tel:+821000000000",
            "+1(202)555-0123": "tel:+12025550123",
            "+44 20 0000 0000": "tel:+442000000000",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(telephone_href(text), expected)

    def test_unsafe_ambiguous_or_unsupported_input_is_not_a_dial_target(self):
        cases = [
            None,
            123,
            "",
            " ",
            "0",
            "1234567",
            "1588-0000",
            "070-0000-0000",
            "010-000-0000",
            "+8201000000000",
            "+82 (0)10-0000-0000",
            "+0123456789",
            "+1234567",
            "+" + "1" * 16,
            "tel:010-0000-0000",
            "javascript:alert(1)",
            "010-0000-0000;ext=1",
            "010-0000-0000#1",
            "010-0000-0000,1",
            "010-0000-0000/02-0000-0000",
            "010-0000-0000 +82 2 0000 0000",
            "010-0000-0000 상담",
            "[TEST] 전화 안내",
            "010-0000-0000\n",
            "\t02-0000-0000",
            "02-0000\r0000",
            "010\x0000000000",
            "０１０-００００-００００",
            "02--0000-0000",
            "02 - 0000 - 0000",
            "(02)(0000)0000",
            "(02-0000-0000",
            "02-0000-0000)",
            "2" * 81,
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(telephone_href(text), "")


class PhoneContactTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name, KAKAO_MAP_JS_KEY="")
        media.enable()
        self.addCleanup(media.disable)
        self.editor = get_user_model().objects.create_superuser("phone-test-editor")

    def publish(self, key, phone, channel=""):
        branch = Branch.objects.create(
            key=key,
            name="[TEST] " + key,
            address="[TEST] 도로명주소",
            address_detail="[TEST] 상세",
            opening_hours="[TEST] 시간 안내",
            phone=phone,
            channel=channel,
        )
        branch.save_revision().publish()
        branch.refresh_from_db()
        return branch

    def soup(self, branch="main"):
        return BeautifulSoup(
            self.client.get("/branches/?branch=" + branch).content, "html.parser"
        )

    def test_each_public_panel_owns_its_phone_and_common_routes_stay_indirect(self):
        main = self.publish("main", "(02)0000-0000", "[TEST] 카카오톡 안내")
        self.publish("second", "010 0000 0000")
        Trainer.objects.create(
            name="[TEST] 트레이너", branch=main
        ).save_revision().publish()
        original = main.live_revision.content
        for selected in ["main", "second"]:
            soup = self.soup(selected)
            for key, href in [
                ("main", "tel:+82200000000"),
                ("second", "tel:+821000000000"),
            ]:
                panel = soup.select_one("#contact-" + key)
                link = panel.select_one('.location-contact-buttons a[href^="tel:"]')
                self.assertEqual(link["href"], href)
                self.assertEqual(link["aria-label"], "[TEST] " + key + " 전화 문의")
                self.assertFalse(link.has_attr("data-preview-contact"))
                self.assertFalse(link.has_attr("data-branch-page"))
            for link in soup.select("[data-inquiry] a, a[data-inquiry]"):
                self.assertNotIn("tel:", link.get("href", ""))
            self.assertEqual(
                soup.select_one('.trainer a[href^="#contact-"]')["href"],
                "#contact-main",
            )
            self.assertIsNone(soup.select_one('[data-preview-contact="카카오톡"]'))
            self.assertFalse(soup.select('a[href^="https://pf.kakao.com/"]'))
            self.assertIn(
                "[TEST] 카카오톡 안내",
                soup.select_one("#contact-main .location-details").get_text(),
            )
            self.assertFalse(soup.select('[data-preview-contact="전화"]'))
        self.assertNotContains(self.client.get("/"), 'href="tel:')
        main.refresh_from_db()
        self.assertEqual(main.phone, "(02)0000-0000")
        self.assertEqual(main.live_revision.content, original)

    def test_draft_preview_publish_and_withdraw_select_the_right_revision(self):
        main = self.publish("main", "02-0000-0000")
        self.publish("second", "010 0000 0000")
        old = main.live_revision_id
        draft = main.get_latest_revision_as_object()
        draft.phone = "(031)0000-0000"
        revision = draft.save_revision()
        self.assertEqual(
            self.soup().select_one('#contact-main a[href^="tel:"]')["href"],
            "tel:+82200000000",
        )
        request = RequestFactory().get("/branches/")
        request.user = self.editor
        response = draft.serve_preview(request, "")
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertEqual(
            soup.select_one('#contact-main a[href^="tel:"]')["href"],
            "tel:+823100000000",
        )
        self.assertEqual(
            soup.select_one('#contact-second a[href^="tel:"]')["href"],
            "tel:+821000000000",
        )
        self.assertIn("private, no-store", response.headers["Cache-Control"])
        main.refresh_from_db()
        self.assertEqual(main.live_revision_id, old)
        request.user = get_user_model().objects.create_user(
            "phone-outsider", is_staff=True
        )
        with self.assertRaises(PermissionDenied):
            draft.serve_preview(request, "")
        revision.publish()
        self.assertEqual(
            self.soup().select_one('#contact-main a[href^="tel:"]')["href"],
            "tel:+823100000000",
        )
        main.refresh_from_db()
        self.assertEqual(main.phone, "(031)0000-0000")
        main.unpublish()
        soup = self.soup()
        self.assertIsNone(soup.select_one("#contact-main"))
        self.assertEqual(
            soup.select_one('#contact-second a[href^="tel:"]')["href"],
            "tel:+821000000000",
        )

    def test_empty_and_legacy_prose_are_optional_escaped_text_not_phone_links(self):
        for phone in [
            "",
            " \t ",
            "[TEST] 상담 안내 <script>x</script>",
            "010-0000-0000;ext=1",
        ]:
            with self.subTest(phone=phone):
                Branch.objects.all().delete()
                branch = self.publish("main", phone, "[TEST] 카카오톡 모의 안내")
                soup = self.soup()
                self.assertFalse(
                    soup.select('[href^="tel:"], [data-preview-contact="전화"]')
                )
                self.assertFalse(soup.select('[data-preview-contact="카카오톡"]'))
                self.assertIn("[TEST] 카카오톡 모의 안내", soup.get_text())
                self.assertFalse(soup.select(".location-information script"))
                if phone.strip():
                    self.assertIn(
                        phone, soup.select_one(".location-details").get_text()
                    )
                else:
                    self.assertNotIn(
                        "전화",
                        [
                            node.get_text()
                            for node in soup.select(".location-details dt")
                        ],
                    )
                if not phone.strip():
                    navigation = json.loads(
                        soup.select_one("#branch-navigation-data").string
                    )
                    self.assertFalse(navigation[0]["phone"])
                branch.refresh_from_db()
                self.assertEqual(branch.phone, phone)

    def test_no_channels_and_zero_public_branches_keep_navigation_without_contacts(
        self,
    ):
        branch = self.publish("main", "")
        soup = self.soup()
        self.assertFalse(soup.select(".location-contact-buttons"))
        self.assertTrue(
            all(node.has_attr("hidden") for node in soup.select("[data-inquiry]"))
        )
        branch.unpublish()
        for path in ["/", "/branches/", "/news/"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            soup = BeautifulSoup(response.content, "html.parser")
            self.assertFalse(soup.select('[href^="tel:"]'))
            self.assertTrue(
                all(node.has_attr("hidden") for node in soup.select("[data-inquiry]"))
            )
            self.assertTrue(soup.select_one(".primary-navigation"))
