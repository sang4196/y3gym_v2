from django.utils.cache import add_never_cache_headers


class NoStoreContentMiddleware:
    """Include denied/not-found responses in the same publication cache boundary."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path == "/" or request.path.startswith(
            ("/branches/", "/news/", "/popups/", "/media/", "/admin/")
        ):
            add_never_cache_headers(response)
        return response
