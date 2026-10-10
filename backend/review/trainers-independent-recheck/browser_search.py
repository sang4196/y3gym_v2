"""Explicit trainer search browser review in an isolated DB/account/media."""

# ruff: noqa: E402
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.test.utils import get_runner

from news.models import Branch, Trainer
from news.tests.review_fixtures import bootstrap_browser_review


class TrainerSearchBrowser(StaticLiveServerTestCase):
    def test_real_saved_draft_search_and_branch_context(self):
        self.assertTrue(connection.settings_dict["NAME"].startswith("test_"))
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with override_settings(BASE_DIR=base, MEDIA_ROOT=base / "media"):
                bootstrap_browser_review()
                call_command("bootstrap_trainer_review", verbosity=0)
                decoy = Trainer.objects.create(
                    name="R1 DraftName · 다른 지점",
                    intro="R1 DraftIntro · 다른 지점",
                    branch=Branch.objects.get(key="main"),
                )
                decoy.save_revision()
                credentials = json.loads((base / ".local-credentials").read_text())
                environment = os.environ.copy()
                environment.update(
                    Y3GYM_SEARCH_REVIEW_ORIGIN=self.live_server_url,
                    Y3GYM_SEARCH_REVIEW_PASSWORD=credentials["cms-review-editor"],
                )
                result = subprocess.run(
                    ["node", "review/trainers-independent-recheck/review-search.mjs"],
                    cwd=settings.PROTOTYPE_DIR.parent / "backend",
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=180,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                print(result.stdout)


if __name__ == "__main__":
    raise SystemExit(
        bool(
            get_runner(settings)(verbosity=2, interactive=False).run_tests(
                ["__main__.TrainerSearchBrowser"]
            )
        )
    )
