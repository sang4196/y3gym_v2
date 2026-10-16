import io
import json
import os
import secrets
import subprocess
import unittest
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.handlers.wsgi import WSGIHandler
from django.core.management import call_command
from PIL import Image, ImageDraw
from wagtail.models import Locale, Page

from news.models import Branch, BrandContent, ContentImage, Post, Trainer
from news.tests.review_fixtures import ensure_collection_root


@unittest.skipUnless(
    os.environ.get("Y3GYM_RUN_BRAND_BROWSER") == "1",
    "Logo browser uses the existing brand opt-in",
)
class LogoHeaderBrowserTests(StaticLiveServerTestCase):
    @staticmethod
    def static_handler(_media_handler):
        # LiveServer's default media filesystem wrapper bypasses protected_media.
        # Keep static assets, but send every media request through actual WSGI.
        return StaticFilesHandler(WSGIHandler())

    def test_logo_chooser_header_geometry_navigation_and_preview(self):
        call_command("flush", interactive=False, verbosity=0)
        ensure_collection_root()
        locale, _ = Locale.objects.get_or_create(language_code=settings.LANGUAGE_CODE)
        # Earlier TransactionTestCase browser fixtures flush migration tree rows.
        if Page.get_first_root_node() is None:
            Page.add_root(title="TEST page root", slug="root", locale=locale)
        password = secrets.token_urlsafe(32)
        get_user_model().objects.create_superuser("logo_editor", password=password)
        brand = BrandContent.objects.create(
            name="TEST Y3GYM", intro_title="TEST synthetic logo review"
        )
        brand.save_revision().publish()
        branch = Branch.objects.create(
            key="main",
            name="TEST Main",
            address="TEST address",
            opening_hours="TEST hours",
            phone="02-0000-0001",
        )
        branch.save_revision().publish()
        trainer = Trainer.objects.create(name="TEST Trainer", branch=branch)
        trainer.save_revision().publish()
        post = Post.objects.create(title="TEST Logo post")
        post.save_revision().publish()
        logos = []
        for label, size in [
            ("square", (240, 240)),
            ("wide", (480, 120)),
            ("tall", (120, 480)),
        ]:
            image = Image.new("RGBA", size, (245, 248, 255, 255))
            draw = ImageDraw.Draw(image)
            draw.rectangle(
                (0, 0, size[0] - 1, size[1] - 1), outline=(25, 80, 180), width=8
            )
            draw.text((10, 10), "QA", fill=(10, 30, 80))
            data = io.BytesIO()
            image.save(data, "PNG")
            logo = ContentImage.objects.create(
                title="TEST logo " + label,
                file=SimpleUploadedFile(
                    label + ".png", data.getvalue(), content_type="image/png"
                ),
            )
            logos.append(
                {"label": label, "id": logo.pk, "size": size, "original": logo.file.url}
            )
        run = Path(os.environ["Y3GYM_QA_RUN_DIR"])
        private = run / ".local-credentials"
        credentials = json.loads(private.read_text()) if private.exists() else {}
        credentials["logo_editor"] = password
        private.write_text(json.dumps(credentials))
        private.chmod(0o600)
        datafile = run / "logo-browser-input.json"
        datafile.write_text(json.dumps({"logos": logos, "post_id": post.pk}))
        datafile.chmod(0o600)
        env = {
            **os.environ,
            "Y3GYM_BRAND_REVIEW_ORIGIN": self.live_server_url,
            "Y3GYM_LOGO_REVIEW_PASSWORD": password,
        }
        result = subprocess.run(
            ["node", "scripts/review-logo-header.mjs"],
            cwd=settings.PROTOTYPE_DIR.parent / "backend",
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        print(result.stdout)
