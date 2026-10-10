from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import Client, TransactionTestCase
from django.urls import reverse

from news.models import Branch, BrandContent, Post


class ConcurrentSaveTests(TransactionTestCase):
    def branch_race(self, publish):
        from news.tests.test_branches import BranchTests

        user = get_user_model().objects.create_superuser(
            "branch-concurrency", password="test-password"
        )
        branch = Branch.objects.create(
            key="main", name="공개 본점", address="임시 주소", opening_hours="시간 예시"
        )
        branch.save_revision(user=user).publish(user=user)
        initial_live = Branch.objects.get(pk=branch.pk).live_revision_id
        url = reverse("wagtailsnippets_news_branch:edit", args=[branch.pk])
        clients = [Client(), Client()]
        payloads = []
        for number, client in enumerate(clients):
            client.force_login(user)
            # Reuse the form reader, not the implementation under test.
            self.client = client
            self.edit_url = lambda instance: url
            payload = BranchTests.payload(self, branch)
            payload["name"] = f"동시 지점 {number}"
            if publish:
                payload["action-publish"] = "1"
            payloads.append(payload)
        barrier = Barrier(2)

        def save(number):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                response = clients[number].post(url, payloads[number])
                return response.status_code, "더 최근 내용" in response.content.decode()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(save, [0, 1]))
        self.assertEqual(sorted(status for status, _ in results), [200, 302])
        self.assertEqual(sum(conflict for _, conflict in results), 1)
        branch.refresh_from_db()
        self.assertEqual(branch.revisions.count(), 2)
        if publish:
            self.assertNotEqual(branch.live_revision_id, initial_live)
            self.assertIn(
                branch.live_revision.as_object().name, ["동시 지점 0", "동시 지점 1"]
            )
        else:
            self.assertEqual(branch.live_revision_id, initial_live)

    def test_simultaneous_branch_drafts_only_save_one_and_keep_public_revision(self):
        self.branch_race(False)

    def test_simultaneous_branch_publications_only_publish_one_revision(self):
        self.branch_race(True)

    def test_simultaneous_brand_saves_keep_one_draft_and_live_revision(self):
        user = get_user_model().objects.create_superuser(
            "brand-concurrency", password="test-password"
        )
        brand = BrandContent.objects.create(name="공개 브랜드", intro_title="공개 소개")
        brand.save_revision(user=user).publish(user=user)
        live_revision = BrandContent.objects.get().live_revision_id
        url = reverse("wagtailsnippets_news_brandcontent:edit", args=[1])
        clients = [Client(), Client()]
        payloads = []
        for number, client in enumerate(clients):
            client.force_login(user)
            page = BeautifulSoup(client.get(url).content, "html.parser")
            payload = {
                "name": f"동시 브랜드 {number}",
                "intro_title": "수정 초안",
                "intro_text": "",
                "hero_image": "",
                "logo_image": "",
                "hero_alt": "",
                "hero_position_x": 50,
                "hero_position_y": 50,
            }
            for name in ["loaded_revision_id", "loaded_revision_created_at"]:
                payload[name] = page.find("input", {"name": name}).get("value", "")
            payloads.append(payload)
        barrier = Barrier(2)

        def save(number):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                response = clients[number].post(url, payloads[number])
                return response.status_code, "더 최근 내용" in response.content.decode()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(save, [0, 1]))
        self.assertEqual(sorted(status for status, _ in results), [200, 302])
        self.assertEqual(sum(conflict for _, conflict in results), 1)
        brand.refresh_from_db()
        self.assertEqual(brand.revisions.count(), 2)
        self.assertEqual(brand.live_revision_id, live_revision)

    def test_simultaneous_saves_from_same_revision_only_commit_one_change(self):
        user = get_user_model().objects.create_superuser(
            "concurrency-admin", password="test-password"
        )
        post = Post.objects.create(title="원래 제목", live=False)
        post.save_revision(user=user).publish(user=user)
        url = reverse("wagtailsnippets_news_post:edit", args=[post.pk])
        clients = [Client(), Client()]
        payloads = []
        for number, client in enumerate(clients):
            client.force_login(user)
            page = BeautifulSoup(client.get(url).content, "html.parser")
            payload = {
                "title": f"동시 저장 {number}",
                "category": "notices",
                "summary": "",
                "cover_image": "",
            }
            for name in ["body", "loaded_revision_id", "loaded_revision_created_at"]:
                payload[name] = page.find("input", {"name": name}).get("value", "")
            payloads.append(payload)
        barrier = Barrier(2)

        def save(number):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                response = clients[number].post(url, payloads[number])
                return response.status_code, "더 최근 내용" in response.content.decode()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(save, [0, 1]))
        self.assertEqual(sorted(status for status, _ in results), [200, 302])
        self.assertEqual(sum(conflict for _, conflict in results), 1)
        post.refresh_from_db()
        self.assertEqual(post.revisions.count(), 2)
        self.assertIn(
            post.get_latest_revision_as_object().title, ["동시 저장 0", "동시 저장 1"]
        )
