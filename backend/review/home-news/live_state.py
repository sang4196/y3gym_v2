"""Compare anonymous HTTP with a read-only public-revision query."""

import json
from pathlib import Path
from urllib.request import urlopen

from bs4 import BeautifulSoup
from django.db import connection, transaction
from django.utils import timezone

from news.popups import eligible_popups
from news.publication import published_posts

with transaction.atomic():
    with connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION READ ONLY")
    posts = published_posts()
    expected = [
        {
            "id": post.pk,
            "title": post.title,
            "date": timezone.localtime(post.first_published_at).strftime("%Y-%m-%d"),
            "url": post.get_absolute_url(),
        }
        for post in posts[:5]
    ]
    popup_ids = list(eligible_popups().values_list("post_id", flat=True))
with urlopen("http://localhost:8768/?branch=second") as response:
    home = BeautifulSoup(response.read(), "html.parser")
rows = home.select("#news .news-item")
actual = [
    {
        "id": int(row.select_one(".news-title-link")["href"].split("/")[2]),
        "title": row.select_one(".news-title-link").get_text(),
        "date": row.select_one("time")["datetime"],
        "url": row.select_one(".news-title-link")["href"].split("?")[0],
    }
    for row in rows
]
assert expected == actual
result = {
    "status": "PASS",
    "database": "existing local CMS; read-only transaction",
    "actual_public_count": len(posts),
    "home_maximum": 5,
    "actual_recent_news": actual,
    "active_popup_post_ids_registration_order": popup_ids,
    "test_posts_added_to_actual_database": False,
    "scenarios": {
        "actual": "existing six published posts; newest five visible; no new writes",
        "controlled": "six seeded posts with deliberate drafts and withdrawal-to-zero only in isolated test DB",
    },
}
Path("review/home-news/live-state-final.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps(result, ensure_ascii=False))
