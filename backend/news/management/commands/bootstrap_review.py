import json
import os
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import Collection, GroupCollectionPermission

from news.models import Post


class Command(BaseCommand):
    help = "Create local CMS review accounts and two test news posts once; never reset existing data."

    @transaction.atomic
    def handle(self, *args, **options):
        users = get_user_model()
        path = settings.BASE_DIR / ".local-credentials"
        if path.exists():
            self.stdout.write(
                "Existing review accounts and content preserved. No reseed performed."
            )
            return
        if users.objects.filter(
            username__in=["cms-review-admin", "cms-review-editor"]
        ).exists():
            raise CommandError(
                "Review accounts already exist. Credentials will not be reset."
            )
        credentials = {}
        group, _ = Group.objects.get_or_create(name="로컬 소식 검토 운영자")
        group.permissions.set(
            Permission.objects.filter(
                content_type__app_label="news",
                content_type__model="post",
                codename__in=["add_post", "change_post", "view_post", "publish_post"],
            )
        )
        group.permissions.add(
            Permission.objects.get(
                codename="access_admin", content_type__app_label="wagtailadmin"
            )
        )
        for codename in ["add_image", "change_image", "choose_image"]:
            permission = Permission.objects.get(
                content_type__app_label="wagtailimages",
                content_type__model="image",
                codename=codename,
            )
            GroupCollectionPermission.objects.get_or_create(
                group=group,
                collection=Collection.get_first_root_node(),
                permission=permission,
            )
        for name, superuser in [
            ("cms-review-admin", True),
            ("cms-review-editor", False),
        ]:
            password = secrets.token_urlsafe(24)
            user = users.objects.create_user(
                username=name, password=password, is_staff=True, is_superuser=superuser
            )
            if not superuser:
                user.groups.add(group)
            credentials[name] = password
        # No branch CMS is created. Public branch links still use the two prototype fixtures.
        for category, title, summary in [
            (
                "notices",
                "방문 전 확인해주세요",
                "운영시간과 위치, 문의 방법을 확인한 뒤 방문해주세요.",
            ),
            (
                "events",
                "이벤트 소식 안내",
                "이벤트가 등록되면 진행 기간과 자세한 내용을 안내합니다.",
            ),
        ]:
            post = Post.objects.create(
                title=title,
                category=category,
                summary=summary,
                body="<p>로컬 CMS 검토를 위한 테스트 소식입니다. 실제 운영 정보나 행사 혜택이 아닙니다.</p>",
                live=False,
            )
            post.save_revision().publish()
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            json.dump(credentials, handle)
        self.stdout.write(
            "Created two local accounts and two test posts. Credentials saved privately; values not printed."
        )
