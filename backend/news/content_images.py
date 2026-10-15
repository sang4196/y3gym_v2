"""Non-cropped display/expansion using the existing protected media storage."""

from django.utils.html import escape
from wagtail.images.formats import get_image_format
from wagtail.images.rich_text import ImageEmbedHandler

EXPANDED_FILTER = "max-2560x2560"


def image_attributes(image):
    rendition = image.get_rendition(EXPANDED_FILTER)
    return {
        "data-image-full": rendition.url,
        "data-image-width": str(rendition.width),
        "data-image-height": str(rendition.height),
    }


def image_tag(image, filter_spec, alt="", classname=""):
    attrs = image_attributes(image)
    attrs["alt"] = escape(alt)
    # Clones deliberately have an empty alt; keep the expansion description.
    attrs["data-image-alt"] = escape(alt)
    if classname:
        attrs["class"] = escape(classname)
    return image.get_rendition(filter_spec).img_tag(attrs)


class ContentImageEmbedHandler(ImageEmbedHandler):
    """Add expansion metadata at render time; saved embeds/editor stay intact."""

    @classmethod
    def expand_db_attributes_many(cls, attrs_list):
        tags = []
        for attrs, image in zip(attrs_list, cls.get_many(attrs_list)):
            if image is None:
                tags.append("")
                continue
            image_format = get_image_format(attrs["format"])
            # Installed fullwidth/left/right use non-cropped width-800/500.
            tags.append(
                image_tag(
                    image,
                    image_format.filter_spec,
                    attrs.get("alt", ""),
                    image_format.classname,
                )
            )
        return tags
