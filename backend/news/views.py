import mimetypes

from django.core.paginator import Paginator
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from wagtail.images.permissions import permission_policy

from .models import ContentImage, Rendition
from .popups import eligible_popups, popup_content
from .publication import published_image_ids, published_posts


@never_cache
def popup_detail(request, pk):
    setting = eligible_popups().filter(post_id=pk).first()
    if not setting:
        raise Http404
    return render(
        request,
        "news/popup.html",
        {"popup": popup_content(setting), "branch": branch_context(request)},
    )


@never_cache
def popup_data(request, pk):
    setting = eligible_popups().filter(post_id=pk).first()
    if not setting:
        raise Http404
    return JsonResponse(popup_content(setting))


def branch_context(request):
    from .branches import request_navigation

    return request_navigation(request)["branch"]


@never_cache
def news_list(request):
    category = request.GET.get("category", "all")
    if category not in {"all", "notices", "events"}:
        category = "all"
    posts = [
        post
        for post in published_posts()
        if category == "all" or post.category == category
    ]
    page = Paginator(posts, 10).get_page(request.GET.get("page", 1))
    return render(
        request,
        "news/list.html",
        {
            "page_kind": "news-list",
            "page": page,
            "category": category,
            "category_label": {"all": "전체", "notices": "공지", "events": "이벤트"}[
                category
            ],
            "categories": [("all", "전체"), ("notices", "공지"), ("events", "이벤트")],
            "branch": branch_context(request),
            "title": "소식",
        },
    )


@never_cache
def news_detail(request, pk):
    post = next((post for post in published_posts() if post.pk == pk), None)
    if post is None:
        raise Http404
    category = request.GET.get("category", "all")
    if category not in {"all", "notices", "events"}:
        category = "all"
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1
    return render(
        request,
        "news/detail.html",
        {
            "post": post,
            "title": post.title,
            "page_kind": "news-post",
            "category": category,
            "return_page": page,
            "branch": branch_context(request),
        },
    )


@never_cache
def protected_media(request, name):
    rendition = Rendition.objects.select_related("image").filter(file=name).first()
    image = (
        rendition.image if rendition else ContentImage.objects.filter(file=name).first()
    )
    if image is None:
        raise Http404
    editor = request.user.has_perm(
        "wagtailadmin.access_admin"
    ) and permission_policy.user_has_permission_for_instance(
        request.user, "choose", image
    )
    # Originals remain private even when a rendition has a public use.
    if not editor and not (rendition and image.pk in published_image_ids()):
        raise Http404
    file = rendition.file if rendition else image.file
    try:
        handle = file.open("rb")
    except FileNotFoundError:
        raise Http404 from None
    response = FileResponse(
        handle, content_type=mimetypes.guess_type(name)[0] or "application/octet-stream"
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response
