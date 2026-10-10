from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from news.models import Branch, ContentImage, FacilityImage


class Command(BaseCommand):
    help = "Create main/second local branch fixtures once without overwriting user content."

    @transaction.atomic
    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name="로컬 소식 검토 운영자")
        group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="news",
                content_type__model="branch",
                codename__in=[
                    "add_branch",
                    "change_branch",
                    "view_branch",
                    "publish_branch",
                ],
            )
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [730032])
        if Branch.objects.exists():
            self.stdout.write(
                "Existing branch revisions and media preserved. Local permissions updated."
            )
            return
        # Exact text/images from prototype/branch-data.js; no operational claims.
        assets = [
            (
                "gym-strength.png",
                "웨이트 공간",
                "덤벨과 벤치가 놓인 가상의 웨이트 운동 공간",
                "덤벨과 벤치, 근력 운동 기구를 살펴볼 수 있는 공간입니다.",
            ),
            (
                "gym-cardio.png",
                "유산소 공간",
                "창가에 러닝머신과 실내 자전거가 배치된 가상의 유산소 운동 공간",
                "러닝머신과 실내 자전거가 배치된 운동 공간입니다.",
            ),
            (
                "gym-stretch.png",
                "스트레칭 공간",
                "운동 매트와 폼롤러가 준비된 가상의 스트레칭 공간",
                "운동 전후 스트레칭을 위한 매트와 소도구 공간입니다.",
            ),
        ]
        images = []
        for filename, title, alt, description in assets:
            with (settings.PROTOTYPE_DIR / "assets/images" / filename).open(
                "rb"
            ) as source:
                image = ContentImage.objects.create(
                    title=f"TEST · {title} · 임시 합성 사진",
                    file=File(source, name="branch-review-" + filename),
                )
            images.append((image, title, alt, description))
        specs = [
            (
                "main",
                "Y3GYM 본점",
                "서울 ○○구 ○○로 00",
                "평일 06:00–23:00\n주말 09:00–18:00",
                "02-0000-0001",
                "본점 채널 예시",
            ),
            (
                "second",
                "Y3GYM 예시점",
                "경기 ○○시 ○○로 00",
                "평일 07:00–22:00\n주말 10:00–18:00",
                "031-000-0002",
                "예시점 채널 예시",
            ),
        ]
        for index, (key, name, address, hours, phone, channel) in enumerate(specs):
            branch = Branch(
                key=key,
                name=name,
                address=address,
                opening_hours=hours,
                phone=phone,
                channel=channel,
                display_order=index,
            )
            branch.facilities = [
                FacilityImage(
                    image=image,
                    title=title,
                    alt=alt,
                    description=description,
                    sort_order=order,
                )
                for order, (image, title, alt, description) in enumerate(images)
            ]
            branch.save()
            branch.save_revision().publish()
        self.stdout.write(
            "Created and published two TEST branches and shared facility images. Existing brand/news/popups/accounts/credentials preserved."
        )
