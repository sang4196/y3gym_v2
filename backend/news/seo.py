"""Search metadata and discovery use the same live revisions as public pages."""

from urllib.parse import urlencode
from xml.etree.ElementTree import Element, SubElement, tostring

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import strip_tags
from django.views.decorators.cache import never_cache

from .publication import published_branches, published_posts


def site_origin(request):
    if settings.Y3GYM_ENV == "production":
        return settings.WAGTAILADMIN_BASE_URL.rstrip("/")
    return request.build_absolute_uri("/").rstrip("/")


def summary(value):
    return " ".join(strip_tags(str(value or "")).split())[:160]


def page_metadata(context):
    request = context["request"]
    brand = context.get("branding")
    name = brand.name if brand and brand.name else "Y3GYM"
    kind = context.get("page_kind", "news-list")
    preview = context.get("is_preview", False)
    selected = context.get("selected_branch")
    post = context.get("post")
    description = summary(f"{name}의 지점·시설과 공지·이벤트를 확인하세요.")
    title = f"{context.get('title') or '소식'} · {name}"
    params = {}
    if kind == "home":
        path = reverse("home")
        title = f"{name} | 지점과 운동 공간 안내"
        description = summary(brand.intro_text if brand else "") or description
    elif kind == "branches":
        path = reverse("branches")
        if selected:
            params["branch"] = selected.key
            title = f"{selected.name} · {name}"
            description = summary(
                f"{selected.name}. {selected.address} {selected.address_detail}. "
                f"{selected.opening_hours}"
            )
    elif post:
        path = (
            reverse("news:detail", kwargs={"pk": post.pk})
            if post.pk
            else reverse("news:list")
        )
        title = f"{post.title} · {name}"
        description = summary(post.summary or post.body) or description
    else:
        path = reverse("news:list")
        category = context.get("category", "all")
        if category in {"notices", "events"}:
            params["category"] = category
        number = getattr(context.get("page"), "number", 1)
        if number > 1:
            params["page"] = number
    canonical = "" if preview else site_origin(request) + path
    if canonical and params:
        canonical += "?" + urlencode(params)
    return {
        "title": title,
        "description": description,
        "site_name": name,
        "type": "article" if post else "website",
        "canonical": canonical,
        "noindex": preview or settings.Y3GYM_ENV != "production",
        "verification": getattr(settings, "SEARCH_ENGINE_VERIFICATION", {})
        if kind == "home" and not preview and settings.Y3GYM_ENV == "production"
        else {},
    }


@never_cache
def robots_txt(request):
    if settings.Y3GYM_ENV != "production":
        body = "User-agent: *\nDisallow: /\n"
    else:
        body = (
            "User-agent: *\nDisallow: /admin/\nDisallow: /healthz/\n"
            f"Sitemap: {site_origin(request)}{reverse('sitemap')}\n"
        )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


@never_cache
def sitemap_xml(request):
    paths = [reverse("home"), reverse("news:list")]
    paths += [
        reverse("branches") + "?" + urlencode({"branch": branch.key})
        for branch in published_branches()
    ]
    paths += [
        reverse("news:detail", kwargs={"pk": post.pk}) for post in published_posts()
    ]
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in paths:
        SubElement(SubElement(root, "url"), "loc").text = site_origin(request) + path
    response = HttpResponse(
        tostring(root, encoding="utf-8", xml_declaration=True),
        content_type="application/xml; charset=utf-8",
    )
    response["X-Robots-Tag"] = "noindex"
    return response
