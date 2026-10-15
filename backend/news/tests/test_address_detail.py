from copy import deepcopy
from urllib.parse import quote

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse

from news.models import Branch
from news.publication import published_branches
from news.tests import test_branches as helpers


class BranchAddressDetailTests(TestCase):
    setUp = helpers.BranchTests.setUp
    branch = helpers.BranchTests.branch
    publish = helpers.BranchTests.publish
    edit_url = helpers.BranchTests.edit_url
    payload = helpers.BranchTests.payload

    def test_optional_detail_and_existing_road_address_constraints(self):
        branch = self.publish(self.branch())
        self.client.force_login(self.admin)
        response = self.client.get(self.edit_url(branch))
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertEqual(
            soup.select_one('label[for="id_address"]').text.strip(), "도로명주소"
        )
        for name in ["address", "address_detail"]:
            field = Branch._meta.get_field(name)
            self.assertTrue(field.blank)
            self.assertEqual(field.max_length, 200)
            self.assertNotIn("required", soup.select_one(f"#id_{name}").attrs)
        self.assertEqual(Branch._meta.get_field("address_detail").default, "")
        for detail in ["", "상" * 200]:
            branch.address_detail = detail
            branch.full_clean()
        branch.address_detail = "상" * 201
        with self.assertRaises(ValidationError):
            branch.full_clean()
        branch.address_detail = "선택 값"
        branch.address = " "
        with self.assertRaises(ValidationError) as error:
            branch.validate_for_publication()
        self.assertIn("address", error.exception.message_dict)

    def test_real_form_detail_draft_reopen_preview_publish_and_withdraw(self):
        main = self.publish(self.branch(address_detail="공개 상세"))
        second = self.publish(self.branch("second", address_detail="다른 지점 상세"))
        self.client.force_login(self.admin)
        data = self.payload(main)
        data["address_detail"] = "1동 302, 303호"
        self.assertEqual(self.client.post(self.edit_url(main), data).status_code, 302)
        self.assertEqual(self.payload(main)["address_detail"], data["address_detail"])
        self.assertContains(self.client.get("/branches/"), "공개 상세")
        self.assertNotContains(self.client.get("/branches/"), data["address_detail"])
        preview = reverse("wagtailsnippets_news_branch:preview_on_edit", args=[main.pk])
        self.assertEqual(self.client.post(preview, self.payload(main)).status_code, 200)
        response = self.client.get(preview)
        self.assertContains(response, data["address_detail"])
        self.assertIn("no-store", response.headers["Cache-Control"])
        main.refresh_from_db()
        request = RequestFactory().get("/preview/")
        request.user = get_user_model().objects.create_user(
            "detail-outsider", is_staff=True
        )
        with self.assertRaises(PermissionDenied):
            main.get_latest_revision_as_object().serve_preview(request, "")
        data = self.payload(main)
        data["action-publish"] = "1"
        self.assertEqual(self.client.post(self.edit_url(main), data).status_code, 302)
        public = {b.key: b for b in published_branches()}
        self.assertEqual(public["main"].address_detail, "1동 302, 303호")
        self.assertEqual(public["second"].address_detail, second.address_detail)
        main.refresh_from_db()
        main.unpublish()
        self.assertNotContains(self.client.get("/branches/"), "1동 302, 303호")
        self.assertContains(self.client.get("/branches/"), second.address_detail)

    def test_old_public_revision_missing_detail_never_uses_new_draft(self):
        branch = self.publish(self.branch())
        revision = branch.live_revision
        old = deepcopy(revision.content)
        del old["address_detail"]
        revision.content = old
        revision.save(update_fields=["content"])
        branch.address_detail = "노출되면 안 되는 최신 초안 상세"
        branch.save()
        branch.save_revision()
        self.assertEqual(published_branches()[0].address_detail, "")
        for url in ["/", "/branches/"]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, branch.address_detail)
            self.assertNotContains(response, 'class="branch-address-detail"')
        revision.refresh_from_db()
        self.assertEqual(revision.content, old)
        self.assertNotIn("address_detail", revision.content)
        self.assertEqual(branch.with_content_json(old).address_detail, "")
        self.assertEqual(old, revision.content)

    def test_safe_multiline_detail_in_summary_contact_home_and_road_only_map(self):
        road = "경기도 용인시 기흥구 동백중앙로 269"
        detail = '<script>alert("detail")</script>\n1동 302, 303호 & ' + "X" * 100
        self.publish(self.branch(address_detail=detail))
        branch = Branch.objects.get(key="main")
        branch.address = road
        self.publish(branch)
        second = self.publish(self.branch("second"))
        for url, count in [("/branches/", 2), ("/", 1)]:
            response = self.client.get(url)
            soup = BeautifulSoup(response.content, "html.parser")
            details = soup.select("#branch-main .branch-address-detail")
            self.assertEqual(len(details), count)
            for node in details:
                self.assertEqual(node.get_text("\n"), detail)
                self.assertIsNone(node.find("script"))
                self.assertIsNotNone(node.find("br"))
            self.assertFalse(soup.select("#branch-second .branch-address-detail"))
        soup = BeautifulSoup(self.client.get("/branches/").content, "html.parser")
        maps = soup.select("[data-branch-map]")
        for node, address in zip(maps, [road, second.address], strict=True):
            self.assertEqual(node["data-map-address"], address)
            self.assertEqual(
                node.select_one("[data-map-link]")["href"],
                "https://map.kakao.com/link/search/" + quote(address, safe=""),
            )
        self.assertNotIn("302", maps[0]["data-map-address"])

    def test_empty_detail_has_no_extra_line_and_can_clear_published_detail(self):
        branch = self.publish(self.branch(address_detail="이전 상세"))
        self.client.force_login(self.admin)
        data = self.payload(branch)
        data.update(address_detail="", **{"action-publish": "1"})
        self.assertEqual(self.client.post(self.edit_url(branch), data).status_code, 302)
        soup = BeautifulSoup(self.client.get("/branches/").content, "html.parser")
        self.assertFalse(soup.select(".branch-address-detail"))
        self.assertIsNone(soup.select_one(".branch-information-item dd").find("br"))
        self.assertEqual(published_branches()[0].address_detail, "")

    def test_stale_detail_form_does_not_overwrite_newer_draft_or_publication(self):
        branch = self.publish(self.branch(address_detail="공개 상세"))
        self.client.force_login(self.admin)
        stale = self.payload(branch)
        draft = branch.get_latest_revision_as_object()
        draft.address_detail = "더 최신 상세 초안"
        draft.save_revision()
        stale["address_detail"] = "충돌한 상세"
        self.assertContains(
            self.client.post(self.edit_url(branch), stale), "더 최근 내용"
        )
        branch.refresh_from_db()
        self.assertEqual(
            branch.get_latest_revision_as_object().address_detail, "더 최신 상세 초안"
        )
        self.assertEqual(published_branches()[0].address_detail, "공개 상세")


class AddressDetailMigrationTests(TransactionTestCase):
    def test_additive_migration_preserves_unsplit_existing_address(self):
        previous = ("news", "0005_trainer_trainerbiography")
        target = ("news", "0006_branch_address_detail")
        executor = MigrationExecutor(connection)
        latest_graph = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([previous])
            old_branch = executor.loader.project_state([previous]).apps.get_model(
                "news", "Branch"
            )
            combined = "경기도 용인시 기흥구 동백중앙로 269 1동 302, 303호"
            row = old_branch.objects.create(
                key="migration-existing",
                name="[TEST] 기존 행",
                address=combined,
                opening_hours="임시 시간",
            )
            executor = MigrationExecutor(connection)
            executor.migrate([target])
            target_branch = executor.loader.project_state([target]).apps.get_model(
                "news", "Branch"
            )
            restored = target_branch.objects.get(pk=row.pk)
            self.assertEqual(restored.address, combined)
            self.assertEqual(restored.address_detail, "")
        finally:
            MigrationExecutor(connection).migrate(latest_graph)
        # A current-model lookup must work after restoring the full graph,
        # including columns added after the migration under examination.
        current = Branch.objects.get(pk=row.pk)
        self.assertEqual(current.address, combined)
        self.assertEqual(current.address_detail, "")
        self.assertEqual(current.kakao_chat_url, "")
