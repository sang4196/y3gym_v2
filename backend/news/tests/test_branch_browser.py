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
    os.environ.get("Y3GYM_RUN_BRANCH_BROWSER") == "1",
    "Opt-in browser review writes only to a temporary test database/media.",
)
class BranchBrowserTests(StaticLiveServerTestCase):
    def test_branch_editor_and_real_public_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with override_settings(BASE_DIR=base, MEDIA_ROOT=base / "media"):
                bootstrap_browser_review()
                credentials = json.loads((base / ".local-credentials").read_text())
                environment = os.environ.copy()
                environment.update(
                    Y3GYM_BRANCH_REVIEW_ORIGIN=self.live_server_url,
                    Y3GYM_BRANCH_REVIEW_PASSWORD=credentials["cms-review-editor"],
                )
                result = subprocess.run(
                    ["node", "scripts/review-branches.mjs"],
                    cwd=settings.PROTOTYPE_DIR.parent / "backend",
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=300,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                print(result.stdout)
