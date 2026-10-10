"""Independent public manifest from read-only DB rows, then anonymous HTTP."""

import json
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from django.conf import settings
from django.db import connection, transaction

from news.models import PopupSetting, Post

assert connection.settings_dict["NAME"] == "y3gym_m1"
assert str(connection.settings_dict["PORT"]) == "55438"
now = datetime.now(timezone.utc)
with transaction.atomic():
    with connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION READ ONLY")
    records = list(
        Post.objects.filter(live=True, live_revision__isnull=False).values(
            "id", "first_published_at", "live_revision__content"
        )
    )
    records.sort(key=lambda r: (-r["first_published_at"].timestamp(), r["id"]))
    expected = [
        {
            "id": row["id"],
            "title": row["live_revision__content"]["title"],
            "summary": row["live_revision__content"]["summary"],
            "category": {"notices": "공지", "events": "이벤트"}[
                row["live_revision__content"]["category"]
            ],
            "date": row["first_published_at"]
            .astimezone(ZoneInfo("Asia/Seoul"))
            .strftime("%Y-%m-%d"),
            "url": f"/news/{row['id']}/",
        }
        for row in records
    ]
    settings = list(
        PopupSetting.objects.filter(
            enabled=True,
            starts_at__lte=now,
            ends_at__gt=now,
            post__live=True,
            post__live_revision__isnull=False,
        ).select_related("post")
    )
    settings.sort(
        key=lambda s: (
            s.post.revisions.order_by("created_at").first().created_at,
            s.post_id,
        )
    )
    expected_popup = [s.post_id for s in settings]


def read(route):
    with urlopen("http://localhost:8768" + route, timeout=15) as response:
        assert response.status == 200
        return BeautifulSoup(response.read(), "html.parser")


home = read("/?branch=second")
listing = read("/news/?branch=second")
actual = []
for row in home.select("#news .news-item"):
    anchor = row.select_one(".news-title-link")
    summary = row.select_one(".news-copy p")
    actual.append(
        {
            "id": int(urlsplit(anchor["href"]).path.strip("/").split("/")[-1]),
            "title": anchor.get_text(),
            "summary": summary.get_text() if summary else "",
            "category": row.select_one(".news-category").get_text(),
            "date": row.select_one("time")["datetime"],
            "url": urlsplit(anchor["href"]).path,
        }
    )
list_ids = [
    int(urlsplit(a["href"]).path.strip("/").split("/")[-1])
    for a in listing.select(".news-title-link")
]
popup = json.loads(home.select_one("#home-popup-data").string)
assert actual == expected[:5], (actual, expected[:5])
assert list_ids == [p["id"] for p in expected]
assert [int(p["postId"]) for p in popup] == expected_popup
for item in actual:
    detail = read(item["url"] + "?branch=second")
    assert detail.select_one("#post-title").get_text() == item["title"]
result = {
    "status": "PASS",
    "read_only_transaction": True,
    "anonymous_GET_only": True,
    "expected_source": "DB first_published_at and live_revision.content, sorted independently in Python; no public helper used",
    "public_count": len(expected),
    "expected_public_manifest": expected,
    "actual_home": actual,
    "actual_list_ids": list_ids,
    "popup_post_ids": expected_popup,
}
output = (
    settings.PROTOTYPE_DIR.parent
    / "backend/review/home-news-independent/live-state.json"
)
with output.open("x") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
print(
    "PASS",
    len(expected),
    "public posts; home",
    [p["id"] for p in actual],
    "popup",
    expected_popup,
)
