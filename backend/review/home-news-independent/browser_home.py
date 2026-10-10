"""Reviewed home browser test copied for outputs restricted to this review folder."""

# ruff: noqa: E402
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
import json
import os
import subprocess
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db import connection
from django.test import override_settings
from django.utils import timezone

from news.models import PopupSetting, Post
from news.tests.review_fixtures import bootstrap_browser_review


@unittest.skipUnless(
    os.environ.get("Y3GYM_RUN_HOME_NEWS_BROWSER") == "1",
    "Opt-in home news UI review uses an isolated test database/media/account.",
)
class HomeNewsBrowserTests(StaticLiveServerTestCase):
    def test_home_news_navigation_empty_state_and_popup_regressions(self):
        self.assertTrue(connection.settings_dict["NAME"].startswith("test_"))
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with override_settings(BASE_DIR=base, MEDIA_ROOT=base / "media"):
                bootstrap_browser_review()
                for post in Post.objects.all():
                    post.unpublish()
                now = timezone.now()
                posts = []
                for index in range(6):
                    post = Post.objects.create(
                        title=f"[TEST] 공개 소식 {index + 1} · 홈과 소식 목록 연결 확인",
                        category="events" if index % 2 else "notices",
                        summary=f"[TEST] {index + 1}번 공개 요약입니다. 지점 선택과 본문 왕복, 모바일 줄바꿈을 확인합니다."
                        if index % 2
                        else "",
                        body=f"<p>[TEST] {index + 1}번 공개 본문입니다.</p>",
                        live=False,
                    )
                    with patch(
                        "django.utils.timezone.now",
                        return_value=now - timedelta(days=6 - index),
                    ):
                        post.save_revision().publish()
                    post.refresh_from_db()
                    posts.append(post)
                # Freeze expected public fields before Wagtail may return the
                # same mutable model object for a latest/live revision.
                public_posts = [
                    {
                        "id": post.pk,
                        "title": post.title,
                        "summary": post.summary,
                        "url": post.get_absolute_url(),
                    }
                    for post in reversed(posts)
                ]
                draft = posts[-1].get_latest_revision_as_object()
                draft.title, draft.summary, draft.body = (
                    "[TEST] 비공개 수정 초안",
                    "[TEST] 새 초안 요약",
                    "<p>[TEST] 새 초안 본문</p>",
                )
                draft.save_revision()
                Post.objects.create(
                    title="[TEST] 새 미공개 글", live=False
                ).save_revision()
                for post in posts[:2]:
                    PopupSetting.objects.create(
                        post=post,
                        enabled=True,
                        starts_at=now - timedelta(hours=1),
                        ends_at=now + timedelta(hours=1),
                    )
                credentials = json.loads((base / ".local-credentials").read_text())
                environment = os.environ.copy()
                environment.update(
                    Y3GYM_HOME_NEWS_ORIGIN=self.live_server_url,
                    Y3GYM_HOME_NEWS_PASSWORD=credentials["cms-review-editor"],
                    Y3GYM_HOME_NEWS_POSTS=json.dumps(public_posts),
                )
                # Existing popup assertions copied byte-for-byte except the
                # origin/output/import adaptation, with original hashes recorded.
                for script in (
                    "review/home-news-independent/popup-revisit.mjs",
                    "review/home-news-independent/popup-edges.mjs",
                ):
                    result = subprocess.run(
                        ["node", script],
                        cwd=settings.PROTOTYPE_DIR.parent / "backend",
                        env=environment,
                        text=True,
                        capture_output=True,
                        timeout=240,
                    )
                    self.assertEqual(
                        result.returncode, 0, result.stdout + result.stderr
                    )
                    print(result.stdout)
                for post in posts:
                    PopupSetting.objects.update_or_create(
                        post=post,
                        defaults={
                            "enabled": True,
                            "starts_at": now - timedelta(hours=1),
                            "ends_at": now + timedelta(hours=1),
                        },
                    )
                environment["Y3GYM_INDEPENDENT_POPUP_MANIFEST"] = json.dumps(
                    [
                        {"id": post.pk, "title": item["title"]}
                        for post, item in zip(
                            posts, reversed(public_posts), strict=True
                        )
                    ]
                )
                result = subprocess.run(
                    ["node", "review/home-news-independent/all-popups.mjs"],
                    cwd=settings.PROTOTYPE_DIR.parent / "backend",
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=180,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                print(result.stdout)
                result = subprocess.run(
                    ["node", "scripts/review-home-news.mjs"],
                    cwd=settings.PROTOTYPE_DIR.parent / "backend",
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=240,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                print(result.stdout)


if __name__ == "__main__":
    from django.test.utils import get_runner

    raise SystemExit(
        bool(
            get_runner(settings)(verbosity=2, interactive=False).run_tests(
                ["__main__.HomeNewsBrowserTests"]
            )
        )
    )
