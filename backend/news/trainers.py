from django.shortcuts import render

from .content_images import image_attributes
from .publication import published_branches, published_trainers


def trainer_card(trainer, branch=None):
    return {
        "pk": trainer.pk or "preview",
        "name": trainer.name.strip() or "이름 미입력 · 미리보기",
        "intro": trainer.intro.strip(),
        "position": trainer.position.strip(),
        "photo": trainer.photo.get_rendition("max-1536x1536")
        if trainer.photo_id
        else None,
        "expanded": image_attributes(trainer.photo) if trainer.photo_id else None,
        "photo_alt": trainer.photo_alt.strip() or trainer.name,
        "biography": [
            item.text.strip() for item in trainer.biography.all() if item.text.strip()
        ],
        "branch": branch,
    }


def branch_trainer_cards(branches, preview=None):
    trainers = published_trainers()
    if preview is not None:
        trainers = [trainer for trainer in trainers if trainer.pk != preview.pk] + [
            preview
        ]
    for branch in branches:
        members = sorted(
            (trainer for trainer in trainers if trainer.branch_id == branch.pk),
            key=lambda trainer: (trainer.display_order, trainer.pk or 0),
        )
        branch.trainer_cards = [trainer_card(trainer, branch) for trainer in members]


def render_trainer_preview(request, trainer):
    public_branch = next(
        (branch for branch in published_branches() if branch.pk == trainer.branch_id),
        None,
    )
    if public_branch:
        from .branches import render_branches

        return render_branches(request, trainer_preview=trainer)
    # Previewing a profile does not grant access to its branch's draft facilities,
    # address or hours. Only the profile itself is rendered for a private branch.
    return render(
        request,
        "news/trainer_preview.html",
        {
            "title": "트레이너 미리보기",
            "page_kind": "branches",
            "is_preview": True,
            "trainer": trainer_card(trainer),
            "affiliation_state": "소속 지점 비공개 · 고객 화면에는 표시되지 않습니다. 지점의 초안 정보는 표시하지 않습니다."
            if trainer.branch_id
            else "소속 지점 미선택 · 공개하려면 지점을 선택해 주세요.",
        },
    )
