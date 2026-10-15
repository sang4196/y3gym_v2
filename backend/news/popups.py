from django.db.models import Min
from django.utils import timezone

from .content_images import image_attributes
from .models import PopupSetting


def eligible_popups(now=None):
    now = now or timezone.now()
    return (
        PopupSetting.objects.filter(
            enabled=True,
            starts_at__lte=now,
            ends_at__gt=now,
            post__live=True,
            post__live_revision__isnull=False,
        )
        .select_related("post", "post__live_revision")
        .annotate(registered_at=Min("post___revisions__created_at"))
        .order_by("registered_at", "post_id")
    )


def popup_content(setting):
    # Never use the editable/latest revision, including for title and image.
    post = setting.post.live_revision.as_object()
    return {
        "id": f"post-{post.pk}",
        "postId": str(post.pk),
        "enabled": True,
        "title": post.title,
        "description": post.summary,
        "category": post.get_category_display(),
        "image": post.cover_image.get_rendition("width-800").url
        if post.cover_image
        else None,
        "imageFull": image_attributes(post.cover_image) if post.cover_image else None,
        "url": f"/popups/{post.pk}/",
        "dataUrl": f"/popups/{post.pk}/data/",
        "post": {"id": str(post.pk), "published": True, "url": post.get_absolute_url()},
    }
