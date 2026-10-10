"""Check actual admin search against names/intros shown from the latest draft."""

import json
import uuid
from pathlib import Path

import audit_trainers as harness
from bs4 import BeautifulSoup


class TrainerDraftSearch(harness.Setup, harness.TestCase):
    def test_search_uses_the_displayed_latest_draft(self):
        payload = self.payload()
        self.assertEqual(
            self.client.post(self.edit_url(self.trainer), payload).status_code, 302
        )
        index = harness.reverse("wagtailsnippets_news_trainer:list")

        def query(term=None):
            data = {"branch": self.branches[1].pk}
            if term is not None:
                data["q"] = term
            response = self.client.get(index, data)
            self.assertEqual(response.status_code, 200)
            soup = BeautifulSoup(response.content, "html.parser")
            links = [
                a
                for a in soup.select("table a[href]")
                if self.edit_url(self.trainer) in a["href"]
            ]
            return {
                "query": term,
                "rows": [
                    {"href": a["href"], "displayed_name": a.get_text(strip=True)}
                    for a in links
                ],
            }

        current = harness.Trainer.objects.get(pk=self.trainer.pk)
        cases = {
            "unsearched": query(),
            "draft_name": query("독립 새 이름"),
            "draft_intro": query("독립 새 소개"),
            "old_name": query("공개 이름"),
            "old_intro": query("공개 소개"),
        }
        result = {
            "status": "PASS"
            if cases["draft_name"]["rows"] and cases["draft_intro"]["rows"]
            else "FAIL",
            "isolated_test_database": True,
            "save_status": 302,
            "actual_editor_login": True,
            "mutable_name": current.name,
            "mutable_intro": current.intro,
            "latest_name": current.get_latest_revision_as_object().name,
            "latest_intro": current.get_latest_revision_as_object().intro,
            "cases": cases,
            "expected": "Searching the latest draft name/intro shown in the administrator list returns this profile.",
            "file": "news/wagtail_hooks.py",
            "search_fields": ["name", "intro"],
        }
        target = Path(__file__).resolve().parent / "trainer-search-result.json"
        if target.exists():
            target = target.with_name(
                f"trainer-search-result-{uuid.uuid4().hex[:8]}.json"
            )
        with target.open("x") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False))
        self.assertTrue(
            cases["unsearched"]["rows"],
            "Unfiltered branch list must show the saved moved draft",
        )
        self.assertEqual(
            cases["unsearched"]["rows"][0]["displayed_name"], "독립 새 이름"
        )
        self.assertEqual(result["status"], "PASS", result)


if __name__ == "__main__":
    raise SystemExit(
        bool(
            harness.get_runner(harness.settings)(
                verbosity=2, interactive=False
            ).run_tests(["__main__.TrainerDraftSearch"])
        )
    )
