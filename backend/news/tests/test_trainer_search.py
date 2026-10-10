import copy
import hashlib
import re
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from news.models import Branch, Trainer, TrainerBiography
from news.publication import published_trainers
from news.tests.test_publication import picture


class TrainerSearchTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.admin = get_user_model().objects.create_superuser(
            "trainer-search", password="test-password"
        )
        self.branches = []
        for key in ["main", "second"]:
            branch = Branch.objects.create(
                key=key,
                name="검수 " + key,
                address="검수 주소",
                opening_hours="검수 시간",
            )
            branch.save_revision().publish()
            self.branches.append(Branch.objects.get(pk=branch.pk))
        self.photos = [picture("search-live.png"), picture("search-draft.png")]
        trainer = Trainer.objects.create(
            name="공개 OldName",
            intro="이전 OldIntro",
            branch=self.branches[0],
            photo=self.photos[0],
            display_order=4,
        )
        trainer.biography = [TrainerBiography(text="공개 약력", sort_order=0)]
        trainer.save_revision().publish()
        self.trainer = Trainer.objects.get(pk=trainer.pk)
        self.assertTrue(
            self.client.login(username="trainer-search", password="test-password")
        )

    def edit_url(self, trainer):
        return reverse("wagtailsnippets_news_trainer:edit", args=[trainer.pk])

    def save_draft(self, **values):
        from news.tests.test_trainers import TrainerTests

        payload = TrainerTests.payload(self, self.trainer)
        payload.update(values)
        self.assertEqual(
            self.client.post(self.edit_url(self.trainer), payload).status_code, 302
        )

    def search(self, term=None, branch=None, results=False, **filters):
        url = reverse(
            "wagtailsnippets_news_trainer:" + ("list_results" if results else "list")
        )
        data = filters
        if term is not None:
            data["q"] = term
        if branch is not None:
            data["branch"] = branch.pk
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        rows = {}
        for link in soup.select("table a[href]"):
            match = re.fullmatch(
                r"/admin/snippets/news/trainer/edit/(\d+)/", link["href"]
            )
            if match:
                rows.setdefault(
                    int(match[1]), (link.get_text(strip=True), link["href"])
                )
        return response, soup, rows

    def test_saved_latest_name_intro_affiliation_and_public_revision_are_consistent(
        self,
    ):
        live_content = copy.deepcopy(self.trainer.live_revision.content)
        hashes = [
            hashlib.sha256(Path(photo.file.path).read_bytes()).hexdigest()
            for photo in self.photos
        ]
        self.save_draft(
            name="초안 NewName",
            intro="새 소개 NewIntro",
            branch=str(self.branches[1].pk),
            photo=str(self.photos[1].pk),
            display_order="1",
            **{"biography-0-text": "초안 약력"},
        )
        for term in ["초안", "newname", "NEWNAME", "새 소개", "newINTRO"]:
            for results in [False, True]:
                with self.subTest(term=term, results=results):
                    _, _, rows = self.search(term, self.branches[1], results=results)
                    self.assertEqual(
                        rows[self.trainer.pk],
                        ("초안 NewName", self.edit_url(self.trainer)),
                    )
        for term in ["공개 OldName", "이전 OldIntro", "일치 없는 검색"]:
            _, _, rows = self.search(term, self.branches[1])
            self.assertNotIn(self.trainer.pk, rows)
        _, _, old_branch_rows = self.search("newname", self.branches[0])
        self.assertNotIn(self.trainer.pk, old_branch_rows)
        for term in [None, "", "   "]:
            _, soup, rows = self.search(term, self.branches[1])
            self.assertIn(self.trainer.pk, rows)
            hidden = soup.select_one('form[data-search-form] input[name="branch"]')
            self.assertEqual(hidden["type"], "hidden")
            self.assertEqual(hidden["value"], str(self.branches[1].pk))
        current = Trainer.objects.get(pk=self.trainer.pk)
        self.assertEqual(current.live_revision.content, live_content)
        self.assertEqual(current.name, "공개 OldName")
        self.assertEqual(current.intro, "이전 OldIntro")
        self.assertEqual(current.branch_id, self.branches[0].pk)
        public = next(t for t in published_trainers() if t.pk == current.pk)
        for field in [
            "name",
            "intro",
            "branch",
            "photo",
            "display_order",
            "position",
            "photo_alt",
            "biography",
        ]:
            self.assertEqual(public.serializable_data()[field], live_content[field])
        for branch, expected in [("main", True), ("second", False)]:
            soup = BeautifulSoup(
                self.client.get("/branches/", {"branch": branch}).content, "html.parser"
            )
            card = soup.select_one(f'#branch-{branch} [data-trainer-id="{current.pk}"]')
            self.assertEqual(card is not None, expected)
            if card:
                self.assertIn("공개 OldName", card.get_text())
                self.assertIn("이전 OldIntro", card.get_text())
                self.assertIn("공개 약력", card.get_text())
                self.assertNotIn("초안", card.get_text())
        self.assertEqual(
            hashes,
            [
                hashlib.sha256(Path(photo.file.path).read_bytes()).hexdigest()
                for photo in self.photos
            ],
        )

    def test_empty_latest_draft_does_not_search_previous_model_fields(self):
        self.save_draft(name="", intro="")
        for term in ["공개", "OldName", "이전", "OldIntro"]:
            _, _, rows = self.search(term, self.branches[0])
            self.assertNotIn(self.trainer.pk, rows)
        _, _, rows = self.search("", self.branches[0])
        self.assertEqual(rows[self.trainer.pk][0], "트레이너 (준비 초안)")
        self.assertEqual(Trainer.objects.get(pk=self.trainer.pk).name, "공개 OldName")

    def test_model_fallback_only_when_no_latest_revision_exists(self):
        trainer = Trainer.objects.create(
            name="미저장 FallbackName",
            intro="소개 FallbackIntro",
            branch=self.branches[1],
        )
        self.assertIsNone(trainer.latest_revision_id)
        for term in ["미저장", "fallbackNAME", "fallbackINTRO"]:
            _, _, rows = self.search(term, self.branches[1])
            self.assertEqual(rows[trainer.pk], (trainer.name, self.edit_url(trainer)))
        _, _, rows = self.search("FallbackName", self.branches[0])
        self.assertNotIn(trainer.pk, rows)

    def test_pagination_and_publication_filter_preserve_query_and_draft_branch(self):
        expected = set()
        for index in range(25):
            trainer = Trainer.objects.create(branch=self.branches[0])
            draft = trainer.get_latest_revision_as_object()
            draft.name = f"페이지 검색 대상 {index:02}"
            draft.branch = self.branches[1]
            draft.save_revision()
            expected.add(trainer.pk)
        live = Trainer.objects.create(
            name="페이지 검색 대상 공개", branch=self.branches[1]
        )
        live.save_revision().publish()
        response, soup, first = self.search("검색 대상", self.branches[1], live="false")
        self.assertEqual(response.context["paginator"].count, 25)
        self.assertEqual(len(first), 20)
        next_link = soup.select_one(".pagination .next a[href]")
        params = parse_qs(urlsplit(next_link["href"]).query)
        self.assertEqual(params["q"], ["검색 대상"])
        self.assertEqual(params["branch"], [str(self.branches[1].pk)])
        self.assertEqual(params["live"], ["false"])
        second_response = self.client.get(next_link["href"])
        self.assertEqual(second_response.status_code, 200)
        _, _, second = self.search("검색 대상", self.branches[1], live="false", p=2)
        self.assertEqual(len(second), 5)
        self.assertFalse(set(first) & set(second))
        self.assertEqual(set(first) | set(second), expected)
        _, _, public_only = self.search("검색 대상", self.branches[1], live="true")
        self.assertEqual(set(public_only), {live.pk})
        _, soup, missing = self.search("없는 결과", self.branches[1], live="false")
        self.assertEqual(missing, {})
        self.assertIsNone(soup.select_one(".pagination .next a[href]"))
