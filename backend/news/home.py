from bs4 import BeautifulSoup
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import never_cache

from .branches import branch_browser, request_navigation
from .content_images import image_attributes
from .popups import eligible_popups, popup_content
from .publication import published_brand, published_posts


@never_cache
def home(request):
    return render_home(request, branding=published_brand())


def set_lines(document, element, value, desktop_break=False):
    element.clear()
    for number, line in enumerate(value.splitlines()):
        if number:
            br = document.new_tag("br")
            if desktop_break:
                br["class"] = "desktop-break"
            element.append(br)
            if desktop_break:
                element.append(" ")
        element.append(line)


def apply_brand(document, branding, request, is_preview):
    name = branding.name if branding and branding.name else "Y3GYM"
    document.title.string = f"{name} | 지점과 운동 공간 안내"
    title = document.select_one("#intro-title")
    description = document.select_one(".hero-description")
    set_lines(
        document,
        title,
        branding.intro_title or name if branding else "브랜드 소개를 준비 중입니다.",
    )
    text = (
        branding.intro_text if branding else "지점 정보와 소식은 아래에서 확인하세요."
    )
    if text:
        set_lines(document, description, text, desktop_break=True)
    else:
        description.decompose()
    document.select_one(".hero-copy .eyebrow").string = f"{name} · 브랜드 공통 안내"
    document.select_one('meta[name="description"]')["content"] = text.replace("\n", " ")
    for wordmark in document.select(".wordmark"):
        wordmark["aria-label"] = f"{name} 홈"
        wordmark.clear()
        wordmark.append(
            BeautifulSoup(
                render_to_string(
                    "news/brand_wordmark.html",
                    {
                        "branding": branding,
                        "header_brand": wordmark.find_parent(
                            "header", class_="site-header"
                        )
                        is not None,
                    },
                    request=request,
                ),
                "html.parser",
            )
        )
    figure = document.select_one(".hero-figure")
    if branding and branding.hero_image_id:
        image = figure.select_one("img")
        rendition = branding.hero_image.get_rendition("max-1536x1536")
        image["src"] = rendition.url
        image["width"], image["height"] = str(rendition.width), str(rendition.height)
        image["alt"] = branding.hero_alt or f"{name} 소개 이미지"
        image.attrs.update(image_attributes(branding.hero_image))
        image["data-image-alt"] = image["alt"]
        image.attrs.pop("style", None)
        caption = figure.select(".photo-caption span")
        caption[0].string = "브랜드 소개 이미지"
        caption[1].string = "로컬 CMS 검토 자료"
    else:
        figure.decompose()
        document.select_one(".hero-layout")["class"].append("hero-layout--text-only")
    stylesheet = document.new_tag(
        "link", rel="stylesheet", href=static("news/brand.css")
    )
    document.head.append(stylesheet)
    if is_preview:
        document.select_one(
            ".prototype-notice"
        ).string = "미리보기 · 저장·공개 전 내용입니다. 지점 정보는 임시 자료입니다."


def render_home(request, branding, is_preview=False):
    # Read the approved generated home; do not regenerate or edit prototype
    # sources/evidence. Adapt assets, brand, news navigation and popup entry.
    # The brand uses a live revision (or protected preview).
    # Branch/gallery and recent news use their current public revisions.
    document = BeautifulSoup(
        (settings.PROTOTYPE_DIR / "index.html").read_text(), "html.parser"
    )
    document.body["data-common-home"] = reverse("home")
    for wordmark in document.select(".site-header .wordmark"):
        wordmark["href"] = reverse("home")
        wordmark.attrs.pop("data-branch-page", None)
    navigation = request_navigation(request)
    recent_news = document.select_one("#news")
    recent_news.select_one(".news-list").replace_with(
        BeautifulSoup(
            render_to_string(
                "news/home_news.html",
                {"posts": published_posts()[:5], "branch": navigation["branch"]},
                request=request,
            ),
            "html.parser",
        )
    )
    recent_news.select_one(
        ".content-example"
    ).string = "로컬 CMS 검토용 · 등록된 제목·내용·사진은 테스트 자료입니다."
    document.select_one("[data-branch-browser]").replace_with(
        BeautifulSoup(
            branch_browser(request, navigation["public_branches"], home=True),
            "html.parser",
        )
    )
    for tag in document.select("[src], link[href]"):
        attribute = "src" if tag.has_attr("src") else "href"
        value = tag[attribute]
        if value == "popup-launcher.js":
            if is_preview:
                tag.decompose()
            else:
                tag[attribute] = static("news/home-popups.js")
        elif not value.startswith(("http:", "https:", "/", "data:")):
            tag[attribute] = static(f"prototype/{value}")
    for anchor in document.select("a[href]"):
        value = anchor["href"]
        if value.startswith("branches.html"):
            anchor["href"] = "/branches/" + ("#contact" if "#contact" in value else "")
        elif value.startswith("news/"):
            anchor["href"] = "/news/"
        elif value == "news.html":
            anchor["href"] = "/news/"
        elif value == "index.html":
            anchor["href"] = "/"
    selected = navigation["selected_branch"]
    for control in document.select(
        ".header-contact, .mobile-contact-bar, .hero-actions .contact-note"
    ):
        control["data-inquiry"] = "any"
    for control in document.select(
        ".hero-actions .contact-buttons a, .mobile-contact-bar a"
    ):
        control["data-inquiry"] = "phone" if "전화" in control.get_text() else "channel"
    for control in document.select("[data-inquiry]"):
        kind = control["data-inquiry"]
        allowed = selected and (
            bool(selected.has_phone_contact or selected.kakao_chat_href)
            if kind == "any"
            else bool(
                selected.kakao_chat_href
                if kind == "channel"
                else selected.has_phone_contact
            )
        )
        if not allowed:
            control["hidden"] = ""
    for anchor in document.select("[data-branch-page]"):
        url = anchor["href"]
        path, _, fragment = url.partition("#")
        anchor["href"] = (
            path
            + (f"?branch={selected.key}" if selected else "")
            + (
                f"#contact-{selected.key}"
                if fragment == "contact" and selected
                else ("#" + fragment if fragment else "")
            )
        )
    for element in document.select("[data-selected-branch-name]"):
        element.string = str(selected) if selected else "준비 중인 지점"
    document.body.append(
        BeautifulSoup(
            render_to_string("news/branch_navigation.html", navigation), "html.parser"
        )
    )
    document.head.append(
        document.new_tag("script", src=static("news/context.js"), type="module")
    )
    document.head.append(
        document.new_tag("link", rel="stylesheet", href=static("news/branches.css"))
    )
    apply_brand(document, branding, request, is_preview)
    document.head.append(
        document.new_tag(
            "link", rel="stylesheet", href=static("news/content-images.css")
        )
    )
    document.head.append(
        document.new_tag("script", src=static("news/content-images.js"), type="module")
    )
    payloads = (
        [] if is_preview else [popup_content(setting) for setting in eligible_popups()]
    )
    entry = document.select_one("[data-popup-entry]")
    fragment = BeautifulSoup(
        render_to_string(
            "news/popup_entry.html",
            {"popups": payloads, "branch": navigation["branch"]},
        ),
        "html.parser",
    )
    entry.replace_with(fragment)
    return HttpResponse(str(document))
