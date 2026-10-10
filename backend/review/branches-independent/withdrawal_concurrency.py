"""Reproduce simultaneous draft-save / withdrawal in an isolated test DB."""

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

import test_independent as harness
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext

from news.models import Branch
from news.wagtail_hooks import BranchUnpublishView


class WithdrawalConcurrency(TransactionTestCase):
    def edit_url(self, branch):
        return harness.reverse("wagtailsnippets_news_branch:edit", args=[branch.pk])

    def test_draft_saved_during_withdrawal_is_not_overwritten(self):
        admin = harness.get_user_model().objects.create_superuser(
            "withdraw-race", password="test-password"
        )
        branch = Branch.objects.create(
            key="main",
            name="공개 본점",
            address="이전 공개 주소",
            opening_hours="시간 예시",
        )
        branch.save_revision().publish()
        branch.refresh_from_db()
        initial = branch.latest_revision_id
        withdraw_client = harness.Client()
        draft_client = harness.Client()
        withdraw_client.force_login(admin)
        draft_client.force_login(admin)
        self.client = draft_client
        payload = harness.test_branches.BranchTests.payload(self, branch)
        payload["address"] = "반드시 보존할 새 초안 주소"
        loaded, saved = Event(), Event()
        original = BranchUnpublishView.get_object

        def pause_after_read(view, queryset=None):
            obj = original(view, queryset)
            loaded.set()
            saved.wait(timeout=4)
            return obj

        def withdraw():
            close_old_connections()
            try:
                with CaptureQueriesContext(connection) as queries:
                    response = withdraw_client.post(
                        harness.reverse(
                            "wagtailsnippets_news_branch:unpublish", args=[branch.pk]
                        )
                    )
                return {
                    "status": response.status_code,
                    "branch_select_for_update": any(
                        "FOR UPDATE" in q["sql"] and "news_branch" in q["sql"]
                        for q in queries
                    ),
                }
            finally:
                close_old_connections()

        def save():
            close_old_connections()
            try:
                self.assertTrue(loaded.wait(timeout=10))
                response = draft_client.post(self.edit_url(branch), payload)
                return response.status_code
            finally:
                saved.set()
                close_old_connections()

        with patch.object(BranchUnpublishView, "get_object", pause_after_read):
            with ThreadPoolExecutor(max_workers=2) as pool:
                withdraw_future = pool.submit(withdraw)
                save_future = pool.submit(save)
                withdraw_result = withdraw_future.result(timeout=15)
                save_status = save_future.result(timeout=15)
        branch.refresh_from_db()
        newest = branch.revisions.order_by("pk").last()
        result = {
            "initial_revision": initial,
            "newest_revision": newest.pk,
            "current_latest_revision": branch.latest_revision_id,
            "current_address": branch.address,
            "newest_revision_address": newest.as_object().address,
            "live": branch.live,
            "withdrawal": withdraw_result,
            "draft_save_status": save_status,
            "expected": "Withdrawal keeps the committed newer draft and latest revision pointer.",
            "isolated_test_database": True,
        }
        output = (
            harness.settings.PROTOTYPE_DIR.parent
            / "backend/review/branches-independent/withdrawal-concurrency-result.json"
        )
        if output.exists():
            output = output.with_name(
                f"withdrawal-concurrency-result-{uuid.uuid4().hex[:8]}.json"
            )
        with output.open("x") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False))
        self.assertEqual(save_status, 302)
        self.assertFalse(branch.live)
        self.assertEqual(
            branch.latest_revision_id,
            newest.pk,
            "Withdrawal overwrote the newer draft's revision pointer",
        )
        self.assertEqual(branch.address, "반드시 보존할 새 초안 주소")


if __name__ == "__main__":
    failures = harness.get_runner(harness.settings)(
        verbosity=2, interactive=False
    ).run_tests(["__main__.WithdrawalConcurrency"])
    raise SystemExit(bool(failures))
