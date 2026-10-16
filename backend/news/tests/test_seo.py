from datetime import timedelta
from pathlib import Path
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from config.runtime import read_runtime
from news.home import render_home
from news.models import Branch, BrandContent, PopupSetting, Post


@override_settings(
    Y3GYM_ENV="production",
    WAGTAILADMIN_BASE_URL="https://public.example",
    SECURE_SSL_REDIRECT=False,
    KAKAO_MAP_JS_KEY="",
)
class SearchDiscoveryTests(TestCase):
    def setUp(self):
        self.brand = self.publish(
            BrandContent.objects.create(
                name="공개 브랜드",
                intro_title="운동 안내",
                intro_text="공개 브랜드 소개",
            )
        )
        self.branch = self.publish(
            Branch.objects.create(
                key="published",
                name="공개 지점",
                address="공개 도로명주소",
                address_detail="공개 상세주소",
                opening_hours="09:00–22:00",
            )
        )
        self.post = self.publish(
            Post.objects.create(
                title="공개 소식", summary="공개 요약", body="<p>공개 본문</p>"
            )
        )

    def publish(self, instance):
        instance.save_revision().publish()
        instance.refresh_from_db()
        return instance

    def document(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return BeautifulSoup(response.content, "html.parser")

    def test_robots_allows_public_content_and_keeps_development_blocked(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/plain"))
        self.assertIn("Disallow: /admin/\n", response.text)
        self.assertIn("Sitemap: https://public.example/sitemap.xml", response.text)
        self.assertNotIn("Disallow: /media/", response.text)
        with override_settings(Y3GYM_ENV="development"):
            self.assertEqual(
                self.client.get("/robots.txt").text, "User-agent: *\nDisallow: /\n"
            )

    def test_sitemap_uses_live_revisions_and_removes_withdrawn_content(self):
        private_branch = Branch.objects.create(key="private", name="비공개 지점")
        private_branch.save_revision()
        private_post = Post.objects.create(title="비공개 소식")
        private_post.save_revision()
        self.branch.name = "수정 초안 지점"
        self.branch.address = "비공개 수정 주소"
        self.branch.save_revision()
        self.post.title = "수정 초안 소식"
        self.post.save_revision()
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        root = ElementTree.fromstring(response.content)
        urls = [element.text for element in root.findall("{*}url/{*}loc")]
        self.assertEqual(
            set(urls),
            {
                "https://public.example/",
                "https://public.example/news/",
                "https://public.example/branches/?branch=published",
                f"https://public.example/news/{self.post.pk}/",
            },
        )
        self.assertNotIn("private", response.text)
        metadata = self.document("/branches/?branch=published")
        self.assertIn(
            "공개 도로명주소",
            metadata.select_one('meta[name="description"]')["content"],
        )
        self.assertNotIn(
            "비공개 수정 주소",
            metadata.select_one('meta[name="description"]')["content"],
        )
        self.assertNotIn("/popups/", response.text)
        self.assertNotIn("/admin/", response.text)
        Post.objects.filter(pk=self.post.pk).update(live=False)
        Branch.objects.filter(pk=self.branch.pk).update(live=False)
        response = self.client.get("/sitemap.xml")
        self.assertNotIn(f"/news/{self.post.pk}/", response.text)
        self.assertNotIn("/branches/", response.text)

    def test_metadata_canonicals_keep_branch_pages_and_strip_shared_branch_query(self):
        cases = [
            ("/?branch=published&utm_source=sample", "https://public.example/"),
            (
                "/branches/?branch=published&utm_source=sample",
                "https://public.example/branches/?branch=published",
            ),
            ("/news/?branch=published", "https://public.example/news/"),
            (
                "/news/?category=events&branch=published",
                "https://public.example/news/?category=events",
            ),
            (
                f"/news/{self.post.pk}/?branch=published&page=3",
                f"https://public.example/news/{self.post.pk}/",
            ),
        ]
        for path, canonical in cases:
            with self.subTest(path=path):
                soup = self.document(path)
                self.assertEqual(len(soup.select("title")), 1)
                self.assertEqual(
                    soup.select_one('link[rel="canonical"]')["href"], canonical
                )
                self.assertEqual(
                    soup.select_one('meta[property="og:url"]')["content"], canonical
                )
                self.assertIsNone(soup.select_one('meta[name="robots"]'))
        soup = self.document("/branches/?branch=published")
        self.assertIn("공개 지점", soup.title.text)
        self.assertIn(
            "공개 도로명주소", soup.select_one('meta[name="description"]')["content"]
        )

    def test_pagination_has_its_own_canonical(self):
        for number in range(10):
            self.publish(Post.objects.create(title=f"추가 소식 {number}"))
        soup = self.document("/news/?page=2&branch=published")
        self.assertEqual(
            soup.select_one('link[rel="canonical"]')["href"],
            "https://public.example/news/?page=2",
        )

    def test_drafts_do_not_change_public_metadata_and_preview_is_noindex(self):
        self.brand.name = "비공개 브랜드 수정"
        self.brand.intro_text = "비공개 설명"
        self.brand.save_revision()
        self.post.title = "비공개 글 제목"
        self.post.summary = "비공개 글 요약"
        self.post.save_revision()
        home = self.document("/")
        self.assertIn("공개 브랜드", home.title.text)
        self.assertEqual(
            home.select_one('meta[name="description"]')["content"], "공개 브랜드 소개"
        )
        post = self.document(f"/news/{self.post.pk}/")
        self.assertEqual(
            post.select_one('meta[name="description"]')["content"], "공개 요약"
        )
        request = RequestFactory().get("/admin/preview/")
        preview = BeautifulSoup(
            render_home(request, self.brand, is_preview=True).content, "html.parser"
        )
        self.assertEqual(
            preview.select_one('meta[name="robots"]')["content"], "noindex,nofollow"
        )
        self.assertFalse(preview.select('link[rel="canonical"]'))
        PopupSetting.objects.create(
            post=self.post,
            enabled=True,
            starts_at=timezone.now() - timedelta(hours=1),
            ends_at=timezone.now() + timedelta(hours=1),
        )
        popup = self.document(f"/popups/{self.post.pk}/")
        self.assertEqual(
            popup.select_one('meta[name="robots"]')["content"], "noindex,follow"
        )

    @override_settings(
        SEARCH_ENGINE_VERIFICATION={
            "naver-site-verification": "naver_public_fixture",
            "google-site-verification": "google_public_fixture",
        }
    )
    def test_verification_is_server_rendered_only_on_public_home(self):
        home = self.document("/")
        self.assertEqual(
            home.head.select_one('meta[name="naver-site-verification"]')["content"],
            "naver_public_fixture",
        )
        self.assertEqual(
            home.head.select_one('meta[name="google-site-verification"]')["content"],
            "google_public_fixture",
        )
        self.assertFalse(
            self.document("/news/").select('meta[name="naver-site-verification"]')
        )
        request = RequestFactory().get("/admin/preview/")
        preview = BeautifulSoup(
            render_home(request, self.brand, is_preview=True).content, "html.parser"
        )
        self.assertFalse(preview.select('meta[name="naver-site-verification"]'))

    def test_verification_accepts_content_values_and_rejects_html(self):
        values = {
            "Y3GYM_ENV": "development",
            "DJANGO_SECRET_KEY": "fixture-only",
            "Y3GYM_DB_NAME": "fixture",
            "Y3GYM_DB_USER": "fixture",
            "Y3GYM_DB_PASSWORD": "fixture",
            "Y3GYM_DB_HOST": "localhost",
            "Y3GYM_DB_PORT": "5432",
            "Y3GYM_NAVER_SITE_VERIFICATION": "naver_fixture",
        }
        result = read_runtime(Path(__file__).resolve().parents[2], values)
        self.assertEqual(
            result["SEARCH_ENGINE_VERIFICATION"]["naver-site-verification"],
            "naver_fixture",
        )
        values["Y3GYM_NAVER_SITE_VERIFICATION"] = '<meta name="invalid">'
        with self.assertRaises(ImproperlyConfigured):
            read_runtime(Path(__file__).resolve().parents[2], values)
