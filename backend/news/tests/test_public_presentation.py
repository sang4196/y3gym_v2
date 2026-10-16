import os
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.utils import timezone

from news.models import Branch, BrandContent, FacilityImage, PopupSetting, Post, Trainer
from news.tests.test_publication import picture


@override_settings(KAKAO_MAP_JS_KEY="")
class PublicPresentationTests(StaticLiveServerTestCase):
    serialized_rollback = True

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable()
        self.addCleanup(media.disable)
        self.image = picture("presentation.png")
        self.brand = self.publish(
            BrandContent.objects.create(
                name="공개 브랜드", intro_title="운동 공간 안내", hero_image=self.image
            )
        )
        self.branches = []
        for key, name in [("main", "본점"), ("second", "추가 지점")]:
            branch = Branch.objects.create(
                key=key,
                name=name,
                address="서울시 공개 주소 " + key,
                opening_hours="09:00–22:00",
                phone="02-0000-0001" if key == "main" else "",
                kakao_chat_url="https://pf.kakao.com/_fixture/chat"
                if key == "main"
                else "",
            )
            FacilityImage.objects.create(
                branch=branch, image=self.image, title="운동 공간", alt="시설 사진"
            )
            self.branches.append(self.publish(branch))
        self.publish(
            Trainer.objects.create(
                name="김코치", branch=self.branches[0], photo=self.image
            )
        )
        self.post = self.publish(
            Post.objects.create(
                title="이용 안내",
                summary="운영 소식",
                body="<p>공개 안내</p>",
                cover_image=self.image,
            )
        )
        PopupSetting.objects.create(
            post=self.post,
            enabled=True,
            starts_at=timezone.now() - timedelta(hours=1),
            ends_at=timezone.now() + timedelta(hours=1),
        )

    def publish(self, instance):
        instance.save_revision().publish()
        instance.refresh_from_db()
        return instance

    def test_public_html_metadata_and_images_have_no_development_annotations(self):
        routes = [
            "/",
            "/branches/",
            "/news/",
            f"/news/{self.post.pk}/",
            f"/popups/{self.post.pk}/",
        ]
        forbidden = [
            "시각 검토용",
            "로컬 CMS",
            "임시 자료",
            "테스트 자료",
            "임시·검토용",
            "실제 서비스는 연결하지 않습니다",
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                soup = BeautifulSoup(response.content, "html.parser")
                text = soup.get_text(" ") + " ".join(
                    str(element.get(attribute, ""))
                    for element in soup.select("[alt], [title], [aria-label], meta")
                    for attribute in ["alt", "title", "aria-label", "content"]
                )
                for term in forbidden:
                    self.assertNotIn(term, text)
                self.assertFalse(soup.select("[data-preview-contact]"))
                if not route.startswith("/popups/"):
                    footer = soup.select_one(".site-footer")
                    self.assertIn("Copyright ©", footer.text)
                    self.assertIn("공개 브랜드", footer.text)
                if route.startswith("/popups/"):
                    self.assertEqual(
                        soup.select_one("[data-popup-image]")["alt"], self.post.title
                    )

    def test_cms_text_is_preserved_and_unpublished_brand_draft_does_not_leak(self):
        self.brand.intro_title = "사용자가 저장한 테스트 제목"
        self.publish(self.brand)
        self.brand.name = "비공개 수정 브랜드"
        self.brand.save_revision()
        response = self.client.get("/")
        self.assertContains(response, "사용자가 저장한 테스트 제목")
        self.assertContains(response, "Copyright ©")
        self.assertNotContains(response, "비공개 수정 브랜드")

    def test_zero_public_branches_keeps_empty_state_without_fake_contacts(self):
        Branch.objects.update(live=False)
        Post.objects.update(live=False)
        soup = BeautifulSoup(self.client.get("/").content, "html.parser")
        self.assertIn("지점 안내를 준비 중입니다.", soup.text)
        self.assertFalse(soup.select("[data-footer-branch]"))
        self.assertTrue(
            all(element.has_attr("hidden") for element in soup.select("[data-inquiry]"))
        )
        self.assertFalse(soup.select('[href^="tel:"], [href^="https://pf.kakao.com/"]'))

    def test_desktop_mobile_tabs_contacts_and_popup_browser(self):
        script = (
            Path(__file__).resolve().parents[2]
            / "scripts/review-public-presentation.mjs"
        )
        env = {
            **os.environ,
            "Y3GYM_QA_ORIGIN": self.live_server_url,
            "Y3GYM_PRESENTATION_POST": str(self.post.pk),
        }
        result = subprocess.run(
            ["node", str(script)], env=env, capture_output=True, text=True, timeout=90
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        print(result.stdout)
