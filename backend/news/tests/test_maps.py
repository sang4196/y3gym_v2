from urllib.parse import quote

from bs4 import BeautifulSoup
from django.test import TestCase, override_settings

from news.models import Branch


class BranchMapTests(TestCase):
    def branch(self, key="main", address="서울특별시 중구 세종대로 110"):
        branch = Branch.objects.create(
            key=key,
            name='검수 지점 , / ? # <script>"',
            address=address,
            opening_hours="검수 시간",
        )
        branch.save_revision().publish()
        branch.refresh_from_db()
        return branch

    def maps(self):
        response = self.client.get("/branches/")
        self.assertEqual(response.status_code, 200)
        return BeautifulSoup(response.content, "html.parser")

    def test_zero_public_branches_has_no_sdk_configuration_or_map(self):
        Branch.objects.create(address="비공개 초안 주소")
        soup = self.maps()
        self.assertFalse(soup.select("[data-branch-map], #branch-map-config"))
        self.assertNotIn("비공개 초안 주소", str(soup))

    def test_two_branches_have_encoded_html_links_without_javascript(self):
        branches = [
            self.branch(),
            self.branch("second", "주소 , / ? # & <script> 입력 검수"),
        ]
        soup = self.maps()
        elements = soup.select("[data-branch-map]")
        self.assertEqual(len(elements), 2)
        for element, branch in zip(elements, branches, strict=True):
            self.assertEqual(element["data-map-address"], branch.address)
            self.assertEqual(element["data-map-name"], branch.name)
            link = element.select_one("[data-map-link]")
            self.assertEqual(
                link["href"],
                "https://map.kakao.com/link/search/" + quote(branch.address, safe=""),
            )
            self.assertEqual(set(link["rel"]), {"noopener", "noreferrer"})
            self.assertEqual(link["target"], "_blank")
        self.assertEqual(len(soup.select("#branch-map-config")), 1)

    def test_address_draft_is_private_until_publish_and_withdrawal_removes_it(self):
        branch = self.branch()
        branch.address = "아직 공개하지 않은 주소"
        branch.save()
        revision = branch.save_revision()
        soup = self.maps()
        self.assertEqual(
            soup.select_one("[data-branch-map]")["data-map-address"],
            "서울특별시 중구 세종대로 110",
        )
        self.assertNotIn(branch.address, str(soup))
        revision.publish()
        self.assertEqual(
            self.maps().select_one("[data-branch-map]")["data-map-address"],
            branch.address,
        )
        branch.refresh_from_db()
        branch.unpublish()
        self.assertFalse(self.maps().select("[data-branch-map]"))

    @override_settings(KAKAO_MAP_JS_KEY="mock-key-</script><script>injected</script>")
    def test_browser_key_is_safely_serialized_only_on_branches(self):
        self.branch()
        soup = self.maps()
        configuration = soup.select_one("#branch-map-config")
        self.assertIn(r"\u003C/script\u003E", configuration.string)
        self.assertFalse(soup.find("script", string="injected"))
        for path in ["/", "/news/"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "branch-map.js")
            self.assertNotContains(response, "branch-map-config")
            self.assertNotContains(response, "mock-key-")
