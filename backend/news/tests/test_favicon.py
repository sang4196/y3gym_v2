import io
import tempfile
from datetime import timedelta

from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from news.home import render_home
from news.models import BrandContent, ContentImage, PopupSetting, Post


class FaviconTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.brand = BrandContent.objects.create(name="브랜드", intro_title="소개")

    def picture(self, size=(80, 60), color="navy", format="PNG"):
        buffer = io.BytesIO()
        image = Image.new("RGB", size, color)
        image.save(buffer, format=format)
        return self.upload(buffer.getvalue(), format)

    def upload(self, data, format="PNG"):
        extension = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}[format]
        return ContentImage.objects.create(
            title="합성 로고",
            file=SimpleUploadedFile(
                f"logo.{extension}", data, content_type=f"image/{extension}"
            ),
        )

    def publish(self, logo):
        self.brand.logo_image = logo
        self.brand.save_revision().publish()
        self.brand.refresh_from_db()

    def icon(self):
        response = self.client.get(reverse("favicon"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("no-store", response["Cache-Control"])
        image = Image.open(io.BytesIO(response.content))
        image.load()
        self.assertEqual(image.size, (96, 96))
        self.assertEqual(image.mode, "RGBA")
        return response, image

    def test_portrait_landscape_square_and_long_logos_keep_all_four_corners(self):
        colors = [(255, 0, 0), (0, 128, 0), (0, 0, 255), (255, 255, 0)]
        for width, height in [(40, 80), (80, 40), (64, 64), (256, 32), (32, 256)]:
            with self.subTest(size=(width, height)):
                source = Image.new("RGB", (width, height))
                for color, box in zip(
                    colors,
                    [
                        (0, 0, width // 2, height // 2),
                        (width // 2, 0, width, height // 2),
                        (0, height // 2, width // 2, height),
                        (width // 2, height // 2, width, height),
                    ],
                ):
                    source.paste(color, box)
                buffer = io.BytesIO()
                source.save(buffer, format="PNG")
                self.publish(self.upload(buffer.getvalue()))
                _, icon = self.icon()
                left, top, right, bottom = icon.getbbox()
                self.assertLessEqual(abs(left - (96 - right)), 1)
                self.assertLessEqual(abs(top - (96 - bottom)), 1)
                self.assertAlmostEqual(
                    (right - left) / (bottom - top), width / height, delta=0.02
                )
                for color, position in zip(
                    colors,
                    [
                        (left, top),
                        (right - 1, top),
                        (left, bottom - 1),
                        (right - 1, bottom - 1),
                    ],
                ):
                    self.assertEqual(icon.getpixel(position), (*color, 255))

    def test_existing_png_jpeg_and_webp_uploads_produce_png(self):
        for format in ["PNG", "JPEG", "WEBP"]:
            with self.subTest(format=format):
                self.publish(self.picture(format=format))
                self.icon()

    def test_transparency_is_preserved(self):
        source = Image.new("RGBA", (80, 40), (255, 0, 0, 0))
        source.paste((0, 0, 255, 128), (10, 10, 70, 30))
        buffer = io.BytesIO()
        source.save(buffer, format="PNG")
        self.publish(self.upload(buffer.getvalue()))
        _, icon = self.icon()
        self.assertEqual(icon.getpixel((48, 48)), (0, 0, 255, 128))
        self.assertEqual(icon.getpixel((0, 0))[3], 0)

    def test_only_live_logo_is_used_until_a_new_revision_is_published(self):
        original = self.picture(color="red")
        replacement = self.picture(color="blue")
        self.publish(original)
        before, _ = self.icon()
        draft = self.brand.get_latest_revision_as_object()
        draft.logo_image = replacement
        revision = draft.save_revision()
        during, _ = self.icon()
        self.assertEqual(before.content, during.content)
        self.assertEqual(self.client.get(replacement.file.url).status_code, 404)
        self.assertEqual(
            self.client.get(
                replacement.get_rendition("max-192x192|format-png").url
            ).status_code,
            404,
        )
        self.assertEqual(self.client.get(original.file.url).status_code, 404)
        revision.publish()
        after, image = self.icon()
        self.assertNotEqual(before.content, after.content)
        self.assertEqual(image.getpixel((48, 48)), (0, 0, 255, 255))

    def test_draft_only_missing_logo_and_withdrawal_return_404(self):
        self.brand.logo_image = self.picture()
        self.brand.save_revision()
        response = self.client.get("/favicon.png")
        self.assertEqual(response.status_code, 404)
        self.assertIn("no-store", response["Cache-Control"])
        self.publish(self.brand.logo_image)
        self.icon()
        BrandContent.objects.filter(pk=self.brand.pk).update(live=False)
        self.assertEqual(self.client.get("/favicon.png").status_code, 404)
        self.publish(None)
        self.assertEqual(self.client.get("/favicon.png").status_code, 404)
        self.assertFalse(
            BeautifulSoup(self.client.get("/").content, "html.parser").select(
                'link[rel="icon"]'
            )
        )

    def test_missing_source_file_does_not_expose_a_broken_original(self):
        logo = self.picture()
        self.publish(logo)
        logo.file.storage.delete(logo.file.name)
        self.assertEqual(self.client.get("/favicon.png").status_code, 404)

    def test_public_pages_and_popup_share_one_stable_icon_link(self):
        self.publish(self.picture())
        post = Post.objects.create(title="공개 글")
        post.save_revision().publish()
        PopupSetting.objects.create(
            post=post,
            enabled=True,
            starts_at=timezone.now() - timedelta(hours=1),
            ends_at=timezone.now() + timedelta(hours=1),
        )
        for path in [
            "/",
            "/branches/",
            "/news/",
            f"/news/{post.pk}/",
            f"/popups/{post.pk}/",
        ]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                links = BeautifulSoup(response.content, "html.parser").head.select(
                    'link[rel="icon"]'
                )
                self.assertEqual(len(links), 1)
                self.assertEqual(links[0]["href"], "/favicon.png")
                self.assertEqual(links[0]["sizes"], "96x96")
                self.assertEqual(links[0]["type"], "image/png")
        self.assertEqual(self.client.head("/favicon.png").status_code, 200)
        self.assertEqual(self.client.post("/favicon.png").status_code, 405)

    def test_private_preview_keeps_the_public_favicon(self):
        self.publish(self.picture(color="red"))
        public, _ = self.icon()
        draft = self.brand.get_latest_revision_as_object()
        draft.logo_image = self.picture(color="blue")
        draft.save_revision()
        response = render_home(
            RequestFactory().get("/admin/preview/"), draft, is_preview=True
        )
        link = BeautifulSoup(response.content, "html.parser").head.select_one(
            'link[rel="icon"]'
        )
        self.assertEqual(link["href"], "/favicon.png")
        self.assertEqual(self.icon()[0].content, public.content)
