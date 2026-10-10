"""Verify long biographies around the fixed inquiry bar in an isolated server."""
# ruff: noqa: E402

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
from django.test import override_settings
from django.test.utils import get_runner

from news.models import Trainer, TrainerBiography
from news.tests.review_fixtures import bootstrap_browser_review


class LongBiographyBrowser(StaticLiveServerTestCase):
    def test_fixed_bar_and_long_biography_readability(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with override_settings(BASE_DIR=base, MEDIA_ROOT=base / "media"):
                bootstrap_browser_review()
                call_command("bootstrap_trainer_review", verbosity=0)
                trainer = Trainer.objects.get(name="트레이너 A")
                trainer.name = "검수용긴이름" * 10
                trainer.position = "[검수용] 직급"
                trainer.biography = [
                    TrainerBiography(
                        text=f"[검수용 {i}] " + "약력표시확인" * 12, sort_order=i
                    )
                    for i in range(12)
                ]
                trainer.save_revision().publish()
                text_only = Trainer.objects.create(
                    name="[검수용] 선택정보 없음", branch_id=trainer.branch_id
                )
                text_only.save_revision().publish()
                result = subprocess.run(
                    ["node", "review/trainers-independent/probe-long.mjs"],
                    env={
                        **os.environ,
                        "Y3GYM_INDEPENDENT_ORIGIN": self.live_server_url,
                        "Y3GYM_INDEPENDENT_TRAINER": str(trainer.pk),
                    },
                    cwd=settings.PROTOTYPE_DIR.parent / "backend",
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                print(result.stdout)


if __name__ == "__main__":
    raise SystemExit(
        bool(
            get_runner(settings)(verbosity=2, interactive=False).run_tests(
                ["__main__.LongBiographyBrowser"]
            )
        )
    )
