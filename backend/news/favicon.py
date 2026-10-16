"""A stable, uncropped icon made only from the currently published brand logo."""

from io import BytesIO

from django.http import Http404, HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from PIL import Image, ImageOps

from .publication import published_brand

ICON_SIZE = 96


@never_cache
@require_safe
def favicon(request):
    brand = published_brand()
    if not brand or not brand.logo_image_id:
        raise Http404
    try:
        # A non-cropped, bounded rendition keeps the original file private and
        # avoids decoding the full upload on every icon request.
        rendition = brand.logo_image.get_rendition("max-192x192|format-png")
        with rendition.file.open("rb") as handle, Image.open(handle) as source:
            logo = ImageOps.exif_transpose(source).convert("RGBA")
            logo.thumbnail((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
            canvas.paste(
                logo,
                ((ICON_SIZE - logo.width) // 2, (ICON_SIZE - logo.height) // 2),
            )
            output = BytesIO()
            canvas.save(output, format="PNG")
    except (OSError, ValueError):
        raise Http404 from None
    response = HttpResponse(output.getvalue(), content_type="image/png")
    response["X-Content-Type-Options"] = "nosniff"
    return response
