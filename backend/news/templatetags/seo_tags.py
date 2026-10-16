from django import template
from django.urls import reverse
from django.utils.html import format_html

from news.publication import published_brand
from news.seo import page_metadata

register = template.Library()


@register.inclusion_tag("news/search_metadata.html", takes_context=True)
def search_metadata(context):
    return {"seo": page_metadata(context)}


@register.simple_tag
def site_favicon():
    # Previews must not advertise their unpublished logo through a public URL.
    brand = published_brand()
    if not brand or not brand.logo_image_id:
        return ""
    return format_html(
        '<link rel="icon" type="image/png" sizes="96x96" href="{}">',
        reverse("favicon"),
    )
