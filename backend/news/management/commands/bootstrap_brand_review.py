from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from news.models import BrandContent, ContentImage


class Command(BaseCommand):
    help = "Create the approved local brand fixture once; preserve existing content and credentials."

    @transaction.atomic
    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name="로컬 소식 검토 운영자")
        group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="news",
                content_type__model="brandcontent",
                codename__in=[
                    "change_brandcontent",
                    "view_brandcontent",
                    "publish_brandcontent",
                ],
            )
        )
        # The advisory lock serializes this one-time seed without locking or
        # resetting user content. The singleton's PK/check also enforce one row.
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [730031])
        if BrandContent.objects.exists():
            self.stdout.write(
                "Existing brand revisions, files and credentials preserved. Local permissions updated."
            )
            return
        with (settings.PROTOTYPE_DIR / "assets/images/gym-hero.png").open(
            "rb"
        ) as source:
            image = ContentImage.objects.create(
                title="TEST · 승인된 홈 대표 사진 · 임시 합성 자료",
                file=File(source, name="brand-review-hero.png"),
            )
        brand = BrandContent.objects.create(
            name="Y3GYM",
            intro_title="운동할 공간을\n먼저 둘러보세요.",
            intro_text="시설과 위치, 이용 정보를 확인하고\n 궁금한 점은 편한 방법으로 문의하세요.",
            hero_image=image,
            hero_alt="창가와 근력 운동 기구가 보이는 가상의 헬스장 전경",
        )
        brand.save_revision().publish()
        self.stdout.write(
            "Created and published the approved local brand fixture. Prototype files and credentials unchanged."
        )
