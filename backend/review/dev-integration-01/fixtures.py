"""Only fresh integration sandbox fixture preparation and boundary validation."""

import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.images import ImageFile
from django.db import connection

from news.models import ContentImage
from news.popups import eligible_popups


def own_work():
    work = Path(settings.BASE_DIR).resolve()
    assert work.parent == Path("/tmp") and work.name.startswith(
        "y3gym-dev-integration-"
    )
    spec = json.loads((work / "instance.json").read_text())
    assert spec["scratch"] == str(work)
    assert spec["database"].startswith("test_y3gym_dev_integration_")
    assert connection.settings_dict["NAME"] == spec["database"]
    assert spec["test_database"] == spec["database"] + "_runner"
    assert spec["origin"] == settings.WAGTAILADMIN_BASE_URL == "http://localhost:8772"
    assert Path(settings.MEDIA_ROOT).resolve() == work / "media"
    assert not settings.KAKAO_MAP_JS_KEY
    return work


def seed_w02():
    work = own_work()
    assert not (work / "original-image.json").exists()
    with (work / "fixture.png").open("rb") as handle:
        image = ContentImage(
            title="[TEST] dev-integration W02 synthetic image",
            file=ImageFile(handle, name="integration-focus.png"),
        )
        image.save()
    # Installed Wagtail's public API computes and saves its normal file hash.
    file_hash = image.get_file_hash()
    image.refresh_from_db()
    assert file_hash and image.file_hash == file_hash
    with (work / "original-image.json").open("x") as handle:
        json.dump({"id": str(image.pk)}, handle)
    return {"image_id": image.pk, "file_hash_present": True}


def validate_seed_and_permissions():
    work = own_work()
    spec = json.loads((work / "instance.json").read_text())
    image = ContentImage.objects.get(
        pk=json.loads((work / "original-image.json").read_text())["id"]
    )
    from wagtail.images.models import hash_filelike

    with (work / "fixture.png").open("rb") as handle:
        upload_hash = hash_filelike(handle)
    assert image.file_hash == upload_hash
    assert (
        ContentImage.objects.filter(file_hash=upload_hash).filter(pk=image.pk).exists()
    )
    user = get_user_model().objects.get(username=spec["username"])
    permissions = ["add_trainer", "change_trainer", "view_trainer", "publish_trainer"]
    assert all(user.has_perm("news." + permission) for permission in permissions)
    return {
        "duplicate_hash_lookup_matches_seed": True,
        "trainer_permissions": permissions,
    }


def validate_popup_handoff():
    work = own_work()
    report = json.loads((work / "evidence/popups/checks.json").read_text())
    assert report["status"] in {"PASS", "PASS_WITH_WARNINGS"}, (
        "Popup admin did not pass; downstream checks BLOCKED"
    )
    expected = [post["id"] for post in report["posts"]]
    actual = [setting.post_id for setting in eligible_popups()]
    assert len(expected) == len(actual) == len(set(expected)) == 2 and set(
        actual
    ) == set(expected), "Two current eligible synthetic popup posts required"
    return {
        "popup_admin_status": report["status"],
        "eligible_post_ids": actual,
        "count": len(actual),
    }
