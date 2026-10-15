import tempfile
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup
from django.test import TestCase, override_settings
from django.urls import include, path, reverse

from news.models import Branch, BrandContent, Post
from news.tests.test_publication import picture

urlpatterns = [path("gym/", include("config.urls"))]


class HeaderHomeTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.brand = BrandContent.objects.create(
            name="TEST brand", intro_title="TEST introduction"
        )
        self.publish(self.brand)
        for key in ["main", "second"]:
            self.publish(
                Branch.objects.create(
                    key=key,
                    name="TEST " + key,
                    address="TEST address",
                    opening_hours="TEST hours",
                    phone="02-0000-0001",
                )
            )
        self.posts = [
            self.publish(
                Post.objects.create(title="TEST " + category, category=category)
            )
            for category in ["notices", "events"]
        ]

    def publish(self, instance):
        instance.save_revision().publish()
        instance.refresh_from_db()
        return instance

    def pages(self):
        return [
            reverse("home"),
            reverse("branches"),
            reverse("news:list"),
            *(reverse("news:detail", args=[post.pk]) for post in self.posts),
        ]

    def assert_header_navigation(self, logo=False):
        for route in self.pages():
            with self.subTest(route=route, logo=logo):
                response = self.client.get(route, {"branch": "second"})
                self.assertEqual(response.status_code, 200)
                soup = BeautifulSoup(response.content, "html.parser")
                header = soup.select_one(".site-header .wordmark")
                self.assertEqual(header["href"], reverse("home"))
                self.assertNotIn("data-branch-page", header.attrs)
                self.assertEqual(len(header.select("img.brand-logo")), int(logo))
                self.assertFalse(header.select("[data-image-full]"))
                for link in soup.select("[data-branch-page]"):
                    self.assertEqual(
                        parse_qs(urlsplit(link["href"]).query)["branch"], ["second"]
                    )
                footer = soup.select_one(".site-footer .wordmark")
                if route == reverse("home"):
                    self.assertEqual(footer["href"], "#main")
                    self.assertEqual(soup.body["data-common-home"], reverse("home"))
                else:
                    self.assertEqual(footer["href"], "/?branch=second")
                    self.assertIn("data-branch-page", footer.attrs)
                    self.assertNotIn("data-common-home", soup.body.attrs)
                    self.assertEqual(
                        soup.select_one(".breadcrumb a")["href"], "/?branch=second"
                    )

    def test_text_header_uses_common_home_and_other_links_keep_branch(self):
        self.assert_header_navigation()

    def test_logo_header_uses_common_home_without_image_enhancement_metadata(self):
        self.brand.logo_image = picture("nav-logo.png")
        self.publish(self.brand)
        self.assert_header_navigation(logo=True)

    @override_settings(ROOT_URLCONF=__name__)
    def test_header_resolves_named_home_under_a_route_prefix(self):
        self.assertEqual(reverse("home"), "/gym/")
        for route in self.pages():
            with self.subTest(route=route):
                response = self.client.get(route, {"branch": "second"})
                self.assertEqual(response.status_code, 200)
                soup = BeautifulSoup(response.content, "html.parser")
                self.assertEqual(
                    soup.select_one(".site-header .wordmark")["href"], "/gym/"
                )
                if route == reverse("home"):
                    self.assertEqual(soup.body["data-common-home"], "/gym/")

    def test_common_home_without_branch_keeps_server_default_and_zero_branch_fallback(
        self,
    ):
        soup = BeautifulSoup(self.client.get(reverse("home")).content, "html.parser")
        self.assertEqual(
            soup.select_one(".site-header .wordmark")["href"], reverse("home")
        )
        self.assertIn("main", soup.select_one("#branch-navigation-data").text)
        for branch in Branch.objects.all():
            branch.unpublish()
        soup = BeautifulSoup(self.client.get(reverse("home")).content, "html.parser")
        self.assertEqual(
            soup.select_one(".site-header .wordmark")["href"], reverse("home")
        )
        self.assertEqual(soup.select_one("#branch-navigation-data").text, "[]")
        self.assertFalse(soup.select("[data-branch-tab]"))
