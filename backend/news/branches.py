from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache

from .publication import published_branches


def navigation_context(request, branches=None, selected=None):
    if branches is None:
        branches = published_branches()
    if selected is None:
        key = request.GET.get("branch")
        selected = next((branch for branch in branches if branch.key == key), None)
        selected = selected or (branches[0] if branches else None)
    return {
        "public_branches": branches,
        "selected_branch": selected,
        "branch": selected.key if selected else "",
        "branch_navigation": [
            {
                "id": branch.key,
                "name": str(branch),
                "phone": bool(branch.phone.strip()),
                "channel": bool(branch.channel.strip()),
            }
            for branch in branches
        ],
    }


def request_navigation(request):
    if not hasattr(request, "_branch_navigation"):
        request._branch_navigation = navigation_context(request)
    return request._branch_navigation


def branch_browser(request, branches, home=False, trainer_preview=None):
    if not home:
        from .trainers import branch_trainer_cards

        branch_trainer_cards(branches, preview=trainer_preview)
    for branch in branches:
        branch.gallery = []
        for item in branch.facilities.all():
            if item.image_id:
                item.rendition = item.image.get_rendition("max-1536x1536")
                branch.gallery.append(item)
    return render_to_string(
        "news/branch_browser.html",
        {"public_branches": branches, "home_preview": home},
        request=request,
    )


@never_cache
def branches(request):
    return render_branches(request)


def render_branches(request, preview=None, trainer_preview=None):
    rows = request_navigation(request)["public_branches"]
    if preview is not None:
        rows = [branch for branch in rows if branch.pk != preview.pk] + [preview]
        rows.sort(
            key=lambda branch: (
                branch.key != "main",
                branch.display_order,
                branch.pk or 0,
            )
        )
    selected = preview
    if trainer_preview is not None:
        selected = next(
            (branch for branch in rows if branch.pk == trainer_preview.branch_id), None
        )
    context = navigation_context(request, rows, selected=selected)
    context.update(
        title="지점 안내",
        page_kind="branches",
        is_preview=preview is not None or trainer_preview is not None,
        branch_browser=branch_browser(request, rows, trainer_preview=trainer_preview),
    )
    return HttpResponse(
        render_to_string("news/branches.html", context, request=request)
    )
