"""Exercise unchanged brand browser script with the now-required branch fixture."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import test_independent as harness


class BrandWithBranchFixture(harness.StaticLiveServerTestCase):
    def test_brand_workflow_with_two_public_branches(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with harness.override_settings(BASE_DIR=base, MEDIA_ROOT=base / "media"):
                for command in [
                    "bootstrap_review",
                    "bootstrap_brand_review",
                    "bootstrap_branch_review",
                ]:
                    harness.call_command(command, verbosity=0)
                environment = os.environ.copy()
                environment.update(
                    Y3GYM_BRAND_REVIEW_ORIGIN=self.live_server_url,
                    Y3GYM_BRAND_REVIEW_PASSWORD=json.loads(
                        (base / ".local-credentials").read_text()
                    )["cms-review-editor"],
                    Y3GYM_BRAND_REVIEW_DIR="review/branches-independent/brand-browser-with-branches",
                )
                result = subprocess.run(
                    ["node", "scripts/review-brand-home.mjs"],
                    cwd=harness.settings.PROTOTYPE_DIR.parent / "backend",
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=180,
                )
                print(result.stdout)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    failures = harness.get_runner(harness.settings)(
        verbosity=2, interactive=False
    ).run_tests(["__main__.BrandWithBranchFixture"])
    raise SystemExit(bool(failures))
