from html.parser import HTMLParser

from .models import Branch, BrandContent, Post, Trainer


class ImageReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "embed" and attrs.get("embedtype") == "image":
            try:
                self.ids.add(int(attrs["id"]))
            except (KeyError, ValueError):
                pass


def published_posts():
    """One source for public HTML and public media usage; never use latest_revision."""
    rows = (
        Post.objects.filter(live=True, live_revision__isnull=False)
        .select_related("live_revision")
        .order_by("-first_published_at", "pk")
    )
    return [row.live_revision.as_object() for row in rows]


def published_brand():
    row = (
        BrandContent.objects.filter(pk=1, live=True, live_revision__isnull=False)
        .select_related("live_revision")
        .first()
    )
    return row.live_revision.as_object() if row else None


def published_branches():
    # Restore the clustered children from the SAME public revision. Neither
    # mutable parent fields nor current child-table rows define public content.
    rows = Branch.objects.filter(live=True, live_revision__isnull=False).select_related(
        "live_revision"
    )
    branches = [row.live_revision.as_object() for row in rows]
    return sorted(
        branches,
        key=lambda branch: (branch.key != "main", branch.display_order, branch.pk),
    )


def published_trainers(branches=None):
    public_branch_ids = {
        branch.pk for branch in (published_branches() if branches is None else branches)
    }
    rows = Trainer.objects.filter(
        live=True, live_revision__isnull=False
    ).select_related("live_revision")
    trainers = [row.live_revision.as_object() for row in rows]
    return sorted(
        (trainer for trainer in trainers if trainer.branch_id in public_branch_ids),
        key=lambda trainer: (trainer.display_order, trainer.pk),
    )


def published_image_ids():
    ids = set()
    branches = published_branches()
    for branch in branches:
        ids.update(item.image_id for item in branch.facilities.all() if item.image_id)
    ids.update(
        trainer.photo_id for trainer in published_trainers(branches) if trainer.photo_id
    )
    brand = published_brand()
    if brand:
        ids.update(
            value for value in [brand.logo_image_id, brand.hero_image_id] if value
        )
    for post in published_posts():
        if post.cover_image_id:
            ids.add(post.cover_image_id)
        refs = ImageReferences()
        refs.feed(post.body.source if hasattr(post.body, "source") else post.body)
        ids.update(refs.ids)
    return ids
