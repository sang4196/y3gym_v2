"""Independent HTTP contracts for the repaired trainer search; test DB only."""

import copy
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import audit_trainers as h


class SearchSemantics(h.Setup, h.TestCase):
    def setUp(self):
        super().setUp()
        self.observations = []

    def get_rows(self, query=None, branch=None, fragment=False, **filters):
        route = h.reverse(
            "wagtailsnippets_news_trainer:" + ("list_results" if fragment else "list")
        )
        data = dict(filters)
        if query is not None:
            data["q"] = query
        if branch is not None:
            data["branch"] = str(branch)
        response = self.client.get(route, data)
        self.assertEqual(response.status_code, 200)
        soup = h.BeautifulSoup(response.content, "html.parser")
        rows = {}
        for anchor in soup.select("table a[href]"):
            match = re.fullmatch(
                r"/admin/snippets/news/trainer/edit/(\d+)/", anchor["href"]
            )
            if match:
                rows.setdefault(int(match[1]), anchor.get_text(strip=True))
        self.observations.append(
            {"query": data, "fragment": fragment, "ids": sorted(rows), "status": 200}
        )
        return response, soup, rows

    def finish(self, name, **details):
        destination = Path(__file__).resolve().parent / "semantics"
        destination.mkdir(exist_ok=True)
        with (destination / f"{name}.json").open("x") as handle:
            json.dump(
                {
                    "status": "PASS",
                    "isolated_test_database": True,
                    "requests": self.observations,
                    **details,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )

    def test_latest_affiliation_or_search_and_full_public_snapshot(self):
        live = copy.deepcopy(self.trainer.live_revision.content)
        files = self.hashes()
        before = self.state(h.published_trainers()[0])
        original_card = h.BeautifulSoup(
            self.client.get("/branches/?branch=main").content, "html.parser"
        ).select_one(f'[data-trainer-id="{self.trainer.pk}"]')
        payload = self.payload()
        payload.update(name='새 이름 Alpha"Token', intro="새 소개 BetaToken")
        self.assertEqual(
            self.client.post(self.edit_url(self.trainer), payload).status_code, 302
        )
        decoy = h.Trainer.objects.create(
            name=payload["name"], intro=payload["intro"], branch=self.branches[0]
        )
        decoy.save_revision()
        terms = ["새 이름", 'alpha"token', 'ALPHA"TOKEN', "새 소개", "BETAtoken"]
        for fragment in [False, True]:
            for term in terms:
                with self.subTest(fragment=fragment, term=term):
                    _, _, rows = self.get_rows(term, self.branches[1].pk, fragment)
                    self.assertEqual(rows, {self.trainer.pk: payload["name"]})
                    _, _, rows = self.get_rows(term, self.branches[0].pk, fragment)
                    self.assertEqual(rows, {decoy.pk: payload["name"]})
            for term in ["공개 이름", "공개 소개", "없는 결과"]:
                _, _, rows = self.get_rows(term, self.branches[1].pk, fragment)
                self.assertEqual(rows, {})
            _, _, rows = self.get_rows("Alpha", None, fragment)
            self.assertEqual(set(rows), {self.trainer.pk, decoy.pk})
            for invalid in ["bad", "-1", "", "999999"]:
                _, _, rows = self.get_rows("Alpha", invalid, fragment)
                self.assertEqual(rows, {})
            for value, expected in [("true", {self.trainer.pk}), ("false", set())]:
                _, _, rows = self.get_rows(
                    "Beta", self.branches[1].pk, fragment, live=value
                )
                self.assertEqual(set(rows), expected)
        _, soup, _ = self.get_rows("Alpha", self.branches[1].pk)
        hidden = soup.select_one('form[data-search-form] input[name="branch"]')
        self.assertEqual(
            (hidden["type"], hidden["value"]), ("hidden", str(self.branches[1].pk))
        )
        current = h.Trainer.objects.get(pk=self.trainer.pk)
        self.assertEqual(current.live_revision.content, live)
        public = next(t for t in h.published_trainers() if t.pk == current.pk)
        self.assertEqual(self.state(public), before)
        self.assertEqual(self.hashes(), files)
        after_card = h.BeautifulSoup(
            self.client.get("/branches/?branch=main").content, "html.parser"
        ).select_one(f'[data-trainer-id="{self.trainer.pk}"]')
        self.assertEqual(str(after_card), str(original_card))
        other = h.BeautifulSoup(
            self.client.get("/branches/?branch=second").content, "html.parser"
        ).select_one(f'#branch-second [data-trainer-id="{self.trainer.pk}"]')
        self.assertIsNone(other)
        self.finish(
            "latest-and-public",
            public_state=before,
            public_revision_unchanged=True,
            photo_bytes_unchanged=True,
            public_card_identical=True,
        )

    def test_empty_revision_never_falls_back_and_unrevisioned_model_does(self):
        payload = self.payload()
        payload.update(name="", intro="")
        self.assertEqual(
            self.client.post(self.edit_url(self.trainer), payload).status_code, 302
        )
        for fragment in [False, True]:
            for term in ["공개 이름", "공개 소개", "독립 새 이름", "독립 새 소개"]:
                _, _, rows = self.get_rows(term, self.branches[1].pk, fragment)
                self.assertEqual(rows, {})
            for term in [None, "", "   "]:
                _, _, rows = self.get_rows(term, self.branches[1].pk, fragment)
                self.assertEqual(rows, {self.trainer.pk: "트레이너 (준비 초안)"})
        fallback = h.Trainer.objects.create(
            name="미저장 FallbackAlpha",
            intro="모델 FallbackBeta",
            branch=self.branches[1],
        )
        self.assertIsNone(fallback.latest_revision_id)
        for fragment in [False, True]:
            for term in ["미저장", "FALLBACKalpha", "fallbackBETA"]:
                _, _, rows = self.get_rows(term, self.branches[1].pk, fragment)
                self.assertEqual(rows, {fallback.pk: fallback.name})
                _, _, rows = self.get_rows(term, self.branches[0].pk, fragment)
                self.assertEqual(rows, {})
        draft = fallback.get_latest_revision_as_object()
        draft.name = "바뀐 RevisionName"
        draft.intro = ""
        draft.save_revision()
        for fragment in [False, True]:
            for term in ["FallbackAlpha", "FallbackBeta"]:
                _, _, rows = self.get_rows(term, self.branches[1].pk, fragment)
                self.assertEqual(rows, {})
            _, _, rows = self.get_rows("revisionNAME", self.branches[1].pk, fragment)
            self.assertEqual(rows, {fallback.pk: draft.name})
        self.finish("empty-and-fallback", fallback_only_without_revision=True)

    def test_actual_pagination_links_preserve_query_branch_and_live(self):
        expected = {"false": set(), "true": set()}
        for index in range(56):
            trainer = h.Trainer.objects.create(
                name=f"이전 행 {index:02}", branch=self.branches[0]
            )
            draft = trainer.get_latest_revision_as_object()
            draft.name = f"R1 공통조건 {index:02}"
            draft.branch = self.branches[1]
            revision = draft.save_revision()
            status = "false" if index < 43 else "true"
            if status == "true":
                revision.publish()
            expected[status].add(trainer.pk)
        decoy = h.Trainer.objects.create(
            name="R1 공통조건 다른 지점", branch=self.branches[0]
        )
        decoy.save_revision()
        page_counts = []
        for fragment in [False, True]:
            for live in ["false", "true"]:
                seen = set()
                page = 1
                lengths = []
                linked_ids = None
                while True:
                    response, soup, rows = self.get_rows(
                        "R1 공통조건", self.branches[1].pk, fragment, live=live, p=page
                    )
                    if linked_ids is not None:
                        self.assertEqual(set(rows), linked_ids)
                    self.assertFalse(seen & set(rows))
                    seen.update(rows)
                    lengths.append(len(rows))
                    next_link = soup.select_one(".pagination .next a[href]")
                    if not next_link:
                        break
                    params = parse_qs(urlsplit(next_link["href"]).query)
                    self.assertEqual(params["q"], ["R1 공통조건"])
                    self.assertEqual(params["branch"], [str(self.branches[1].pk)])
                    self.assertEqual(params["live"], [live])
                    page = int(params["p"][0])
                    linked = self.client.get(next_link["href"])
                    self.assertEqual(linked.status_code, 200)
                    linked_soup = h.BeautifulSoup(linked.content, "html.parser")
                    linked_ids = {
                        int(match[1])
                        for anchor in linked_soup.select("table a[href]")
                        if (
                            match := re.fullmatch(
                                r"/admin/snippets/news/trainer/edit/(\d+)/",
                                anchor["href"],
                            )
                        )
                    }
                    self.assertLessEqual(page, 3)
                self.assertEqual(seen, expected[live])
                self.assertEqual(lengths, [20, 20, 3] if live == "false" else [13])
                page_counts.append(
                    {"fragment": fragment, "live": live, "pages": lengths}
                )
        self.finish(
            "pagination", page_counts=page_counts, no_duplicates_or_missing=True
        )


if __name__ == "__main__":
    raise SystemExit(
        bool(
            h.get_runner(h.settings)(verbosity=2, interactive=False).run_tests(
                ["__main__.SearchSemantics"]
            )
        )
    )
