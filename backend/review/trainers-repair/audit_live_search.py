"""Read-only live admin GETs using an existing local review session if available."""

import http.client
import json
from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import connection, transaction
from django.utils import timezone

from news.models import Branch, Trainer

output = Path("review/trainers-repair/live-admin-search.json")
assert not output.exists()
with transaction.atomic():
    with connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION READ ONLY")
    user = get_user_model().objects.get(username="cms-review-editor")
    cookie = None
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        decoded = session.get_decoded()
        if decoded.get("_auth_user_id") == str(user.pk) and not decoded.get(
            "_messages"
        ):
            cookie = session.session_key
            break
    branches = {b.key: b.pk for b in Branch.objects.all()}
    trainers = {t.name: t.pk for t in Trainer.objects.all()}
result = {
    "status": "SKIP",
    "http_methods": ["GET"],
    "created_login_or_session": False,
    "cookie_or_password_recorded": False,
    "checks": [],
}
if cookie:
    conn = http.client.HTTPConnection("localhost", 8768, timeout=10)
    for branch, query, expected in [
        ("main", "트레이너 A", [trainers["트레이너 A"]]),
        ("second", "트레이너 B", [trainers["트레이너 B"]]),
        ("main", "트레이너 B", []),
        ("second", "검색 결과 없음", []),
    ]:
        target = "/admin/snippets/news/trainer/?" + urlencode(
            {"branch": branches[branch], "q": query}
        )
        conn.request(
            "GET",
            target,
            headers={"Cookie": settings.SESSION_COOKIE_NAME + "=" + cookie},
        )
        response = conn.getresponse()
        soup = BeautifulSoup(response.read(), "html.parser")
        ids = sorted(
            {
                int(a["href"].rstrip("/").split("/")[-1])
                for a in soup.select(
                    'table a[href^="/admin/snippets/news/trainer/edit/"]'
                )
            }
        )
        hidden = soup.select_one('form[data-search-form] input[name="branch"]')
        passed = (
            response.status == 200
            and ids == expected
            and hidden is not None
            and hidden.get("value") == str(branches[branch])
        )
        result["checks"].append(
            {
                "branch": branch,
                "query": query,
                "status_code": response.status,
                "row_ids": ids,
                "expected_row_ids": expected,
                "hidden_branch_preserved": hidden is not None
                and hidden.get("value") == str(branches[branch]),
                "result": "PASS" if passed else "FAIL",
            }
        )
    conn.close()
    result["status"] = (
        "PASS" if all(c["result"] == "PASS" for c in result["checks"]) else "FAIL"
    )
else:
    result["reason"] = (
        "No existing valid local editor session without pending messages; no login POST was made. Isolated real-browser search is tested separately."
    )
with output.open("x") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
print(result["status"], "read-only live search GETs", len(result["checks"]))
assert result["status"] != "FAIL", result
