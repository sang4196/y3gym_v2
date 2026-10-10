import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from django.test import override_settings

from news.tests.review_fixtures import bootstrap_browser_review


@unittest.skipUnless(
    os.environ.get("Y3GYM_RUN_TRAINER_BROWSER") == "1",
    "Opt-in trainer browser review uses an isolated test DB/media.",
)
class TrainerBrowserTests(StaticLiveServerTestCase):
    def test_trainer_management_publication_and_cards(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with override_settings(BASE_DIR=base, MEDIA_ROOT=base / "media"):
                bootstrap_browser_review()
                # Keep existing brand/branch zero-trainer fixtures untouched.
                call_command("bootstrap_trainer_review", verbosity=0)
                credentials = json.loads((base / ".local-credentials").read_text())
                environment = os.environ.copy()
                environment.update(
                    Y3GYM_TRAINER_REVIEW_ORIGIN=self.live_server_url,
                    Y3GYM_TRAINER_REVIEW_PASSWORD=credentials["cms-review-editor"],
                )
                result = subprocess.run(
                    ["node", "scripts/review-trainers.mjs"],
                    cwd=settings.PROTOTYPE_DIR.parent / "backend",
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=300,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                print(result.stdout)
