import io
from copy import deepcopy
from datetime import timedelta

from bs4 import BeautifulSoup
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.utils import timezone
from PIL import Image

from news.content_images import EXPANDED_FILTER
from news.models import BrandContent, FacilityImage, PopupSetting, Post, Trainer
from news.tests import test_branches as helpers
from news.tests import test_facility_image_fit as edge_helpers


class ContentImageTests(TestCase):
    setUp = helpers.BranchTests.setUp
    branch = helpers.BranchTests.branch
    publish = helpers.BranchTests.publish
    marked_image = edge_helpers.FacilityImageFitTests.marked_image

    def photo_tags(self, route):
        response = self.client.get(route)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        return BeautifulSoup(response.content, "html.parser").select(
            "img[data-image-full]"
        )

    def assert_bytes(self, url, size):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        with Image.open(io.BytesIO(b"".join(response.streaming_content))) as image:
            w, h = image.size
            self.assertLessEqual(abs(w * size[1] - h * size[0]), max(size))
            self.assertEqual(
                [
                    image.convert("RGB").getpixel(point)
                    for point in [
                        (w // 2, 3),
                        (w // 2, h - 4),
                        (3, h // 2),
                        (w - 4, h // 2),
                    ]
                ],
                [(227, 66, 52), (52, 120, 227), (34, 166, 103), (244, 185, 66)],
            )

    def test_every_public_photo_route_has_non_cropped_display_and_expansion(self):
        sizes = [(900, 1800), (1800, 900), (1800, 1800), (600, 3000)]
        images = [self.marked_image(size, str(i)) for i, size in enumerate(sizes)]
        branch = self.branch()
        branch.facilities = [
            FacilityImage(image=image, sort_order=i) for i, image in enumerate(images)
        ]
        self.publish(branch)
        self.publish(
            BrandContent.objects.create(
                name="TEST", intro_title="TEST", hero_image=images[0]
            )
        )
        for image in images:
            self.publish(
                Trainer.objects.create(name="TEST", branch=branch, photo=image)
            )
        body = "".join(
            f'<embed embedtype="image" id="{image.pk}" format="fullwidth" alt="TEST"/>'
            for image in images
        )
        post = self.publish(
            Post.objects.create(title="TEST notice", cover_image=images[0], body=body)
        )
        now = timezone.now()
        setting, _ = PopupSetting.objects.update_or_create(
            post=post,
            defaults={
                "enabled": True,
                "starts_at": now - timedelta(hours=1),
                "ends_at": now + timedelta(days=1),
            },
        )
        self.assertTrue(setting.enabled)
        expected = {
            image.get_rendition(EXPANDED_FILTER).url: size
            for image, size in zip(images, sizes, strict=True)
        }
        for route, count in [
            ("/", 5),
            ("/branches/", 8),
            (post.get_absolute_url(), 5),
            (f"/popups/{post.pk}/", 1),
        ]:
            tags = self.photo_tags(route)
            self.assertEqual(len(tags), count, route)
            for tag in tags:
                full = tag["data-image-full"]
                self.assertIn(full, expected)
                self.assertNotIn("fill-", tag["src"])
                self.assert_bytes(tag["src"], expected[full])
                self.assert_bytes(full, expected[full])
        payload = self.client.get(f"/popups/{post.pk}/data/").json()
        self.assertEqual(
            payload["imageFull"]["data-image-full"],
            images[0].get_rendition(EXPANDED_FILTER).url,
        )
        for image in images:
            self.assertEqual(self.client.get(image.file.url).status_code, 404)

    def test_body_formats_sanitizer_links_and_saved_source_are_preserved(self):
        image = self.marked_image((900, 1800), "body")
        body = "".join(
            f'<embed embedtype="image" id="{image.pk}" format="{fmt}" alt="TEST &amp; quote"/>'
            for fmt in ["fullwidth", "left", "right"]
        )
        post = Post.objects.create(
            title="TEST event",
            category="events",
            body=body
            + '<p><a href="/news/" onclick="bad()">navigation</a></p><script>bad()</script>',
        )
        post.full_clean()
        post = self.publish(post)
        saved = deepcopy(post.live_revision.content)
        tags = self.photo_tags(post.get_absolute_url())
        self.assertEqual(len(tags), 3)
        self.assertEqual([tag["width"] for tag in tags], ["800", "500", "500"])
        self.assertEqual([tag["alt"] for tag in tags], ["TEST & quote"] * 3)
        html = self.client.get(post.get_absolute_url()).content.decode()
        self.assertNotIn("onclick", html)
        self.assertNotIn("<script>bad()", html)
        self.assertIn('href="/news/"', html)
        post.refresh_from_db()
        self.assertEqual(post.live_revision.content, saved)
        self.assertNotIn("data-image-full", str(post.body))

    def test_expansion_obeys_current_revision_shared_usage_and_last_withdrawal(self):
        image = self.marked_image((900, 1800), "public")
        private = self.marked_image((1800, 900), "draft")
        post = self.publish(Post.objects.create(title="TEST", cover_image=image))
        shared = self.publish(
            Post.objects.create(
                title="TEST shared",
                body=f'<embed embedtype="image" id="{image.pk}" format="left" alt="TEST"/>',
            )
        )
        full = self.photo_tags(post.get_absolute_url())[0]["data-image-full"]
        old_crop = image.get_rendition("fill-640x800").url
        draft = post.get_latest_revision_as_object()
        draft.cover_image = private
        draft.save_revision()
        self.assertEqual(
            self.photo_tags(post.get_absolute_url())[0]["data-image-full"], full
        )
        hidden = private.get_rendition(EXPANDED_FILTER).url
        self.assertEqual(self.client.get(hidden).status_code, 404)
        post.unpublish()
        for url in [full, old_crop]:
            self.assertEqual(self.client.get(url).status_code, 200)
        shared.unpublish()
        for url in [full, old_crop, image.file.url, hidden]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)
            self.assertIn("no-store", response["Cache-Control"])

    def test_private_preview_expansion_requires_real_editor_permission(self):
        image = self.marked_image((900, 1800), "preview")
        post = Post.objects.create(title="TEST draft", cover_image=image, live=False)
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            post.serve_preview(request, None)
        request.user = self.admin
        response = post.serve_preview(request, None).render()
        self.assertIn("no-store", response["Cache-Control"])
        tag = BeautifulSoup(response.content, "html.parser").select_one(
            "img[data-image-full]"
        )
        self.assertIsNotNone(tag)
        self.assertEqual(self.client.get(tag["data-image-full"]).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(tag["data-image-full"]).status_code, 200)

    def test_missing_photos_have_no_trigger_metadata_and_logo_is_excluded(self):
        logo = self.marked_image((1800, 900), "logo")
        self.publish(
            BrandContent.objects.create(
                name="TEST", intro_title="TEST", logo_image=logo
            )
        )
        branch = self.publish(self.branch())
        self.publish(Trainer.objects.create(name="TEST", branch=branch))
        post = self.publish(
            Post.objects.create(
                title="TEST",
                body='<p>text</p><embed embedtype="image" id="999999" format="fullwidth" alt="missing"/>',
            )
        )
        for route in ["/", "/branches/", "/news/", post.get_absolute_url()]:
            self.assertEqual(self.photo_tags(route), [])
