from django import template

from news.content_images import image_tag

register = template.Library()


@register.simple_tag
def content_image(image, filter_spec="width-1200", alt=""):
    return image_tag(image, filter_spec, alt or image.title) if image else ""
