from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from news.models import Branch, ContentImage, Trainer


class Command(BaseCommand):
    help = "Create approved temporary trainers A/B once; preserve existing profiles and media."

    @transaction.atomic
    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name="로컬 소식 검토 운영자")
        group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="news",
                content_type__model="trainer",
                codename__in=[
                    "add_trainer",
                    "change_trainer",
                    "view_trainer",
                    "publish_trainer",
                ],
            )
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [730033])
        if Trainer.objects.exists():
            self.stdout.write(
                "Existing trainer content/revisions/media preserved. Local review permissions updated."
            )
            return
        branches = {
            branch.key: branch
            for branch in Branch.objects.filter(key__in=["main", "second"])
        }
        if set(branches) != {"main", "second"}:
            self.stdout.write(
                "No seed created: save main/second branches first. Existing content preserved."
            )
            return
        specs = [
            (
                "main",
                "A",
                "짙은 회색 운동복을 입은 가상의 남성 트레이너",
                "운동을 시작하기 전, 목표와 궁금한 점을 함께 이야기해보세요.",
            ),
            (
                "second",
                "B",
                "짙은 회색 운동복을 입은 가상의 여성 트레이너",
                "시설 이용과 운동에 관해 궁금한 내용을 편하게 문의하세요.",
            ),
        ]
        for key, label, alt, intro in specs:
            filename = "trainer-" + label.lower() + ".png"
            with (settings.PROTOTYPE_DIR / "assets/images" / filename).open(
                "rb"
            ) as source:
                photo = ContentImage.objects.create(
                    title=f"TEST · 트레이너 {label} · 임시 합성 인물",
                    file=File(source, name="review-" + filename),
                )
            trainer = Trainer.objects.create(
                name="트레이너 " + label,
                branch=branches[key],
                photo=photo,
                photo_alt=alt,
                intro=intro,
            )
            trainer.save_revision().publish()
            photo.get_rendition("fill-640x800")
        self.stdout.write(
            "Created two approved temporary trainers A/B. No position/biography claims added. Existing content/accounts/credentials preserved."
        )
