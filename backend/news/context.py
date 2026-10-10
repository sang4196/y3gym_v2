from django.conf import settings


def site_context(request):
    from .branches import request_navigation
    from .publication import published_brand

    return {
        "prototype_url": settings.PROTOTYPE_URL,
        "branding": published_brand(),
        **request_navigation(request),
    }
