import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

from news.tests.review_fixtures import bootstrap_browser_review


@unittest.skipUnless(
    os.environ.get("Y3GYM_RUN_BRAND_BROWSER") == "1",
    "Separate opt-in Chromium review uses a temporary test database.",
)
class BrandBrowserTests(StaticLiveServerTestCase):
    def test_brand_editor_and_public_home(self):
        # All writes, uploads and accounts belong to Django's test database.
        # The currently running local CMS database and credentials are untouched.
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with override_settings(BASE_DIR=base, MEDIA_ROOT=base / "media"):
                bootstrap_browser_review()
                credentials = json.loads((base / ".local-credentials").read_text())
                environment = os.environ.copy()
                environment.update(
                    Y3GYM_BRAND_REVIEW_ORIGIN=self.live_server_url,
                    Y3GYM_BRAND_REVIEW_PASSWORD=credentials["cms-review-editor"],
                )
                result = subprocess.run(
                    ["node", "scripts/review-brand-home.mjs"],
                    cwd=settings.PROTOTYPE_DIR.parent / "backend",
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=180,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                print(result.stdout)
