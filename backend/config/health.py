"""Small readiness response without configuration or database detail."""

import os
from urllib.request import Request, urlopen

from django.db import DatabaseError, connection, transaction
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@transaction.non_atomic_requests
@never_cache
@require_GET
def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


if __name__ == "__main__":
    # This probe runs inside the private app container, never through a public port.
    host = os.environ["Y3GYM_ALLOWED_HOSTS"].split(",")[0].strip()
    req = Request(
        "http://127.0.0.1:8000/healthz/",
        headers={"Host": host, "X-Forwarded-Proto": "https"},
    )
    with urlopen(req, timeout=5) as response:
        assert response.status == 200
