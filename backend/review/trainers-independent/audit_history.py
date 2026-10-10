"""Read-only verification of developer baseline, stage hashes and seed ownership."""

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction

root = settings.PROTOTYPE_DIR.parent
output = root / "backend/review/trainers-independent"
archive = Path("/tmp/y3gym-m2-3-6igvt1ds")
before = json.loads((archive / "snapshot-before.json").read_text())
current = json.loads((output / "snapshot-before.json").read_text())
stages = {
    name: json.loads((archive / name / "snapshot-after.json").read_text())
    for name in ["schema", "seed", "seed-repeat", "final"]
}
changed_files = [
    name
    for name, value in before["files"].items()
    if not (root / name).is_file()
    or hashlib.sha256((root / name).read_bytes()).hexdigest() != value
]
changed_rows, removed_rows, added_rows = {}, {}, {}
for table, state in before["db"].items():
    old = state["hashes"]
    new = current["db"][table]["hashes"]
    changed_rows[table] = [
        key for key in old.keys() & new.keys() if old[key] != new[key]
    ]
    removed_rows[table] = sorted(old.keys() - new.keys())
    added_rows[table] = sorted(new.keys() - old.keys(), key=int)
added_rows = {table: keys for table, keys in added_rows.items() if keys}
expected = json.loads((root / "backend/review/trainers/changed-files.json").read_text())
common = [
    "backend/news/tests/review_fixtures.py",
    "backend/news/tests/test_brand_browser.py",
    "backend/news/tests/test_branch_browser.py",
]
report = {
    "status": "RUNNING",
    "baseline_files": len(before["files"]),
    "changed_existing_files": changed_files,
    "exactly_reported_16_changes": set(changed_files)
    == set(expected["modified_existing_files"]),
    "old_database_tables": len(before["db"]),
    "current_database_tables": len(current["db"]),
    "modified_old_rows": {k: v for k, v in changed_rows.items() if v},
    "removed_old_rows": {k: v for k, v in removed_rows.items() if v},
    "added_rows_by_table": {k: len(v) for k, v in added_rows.items()},
    "new_tables": {
        k: v["rows"] for k, v in current["db"].items() if k not in before["db"]
    },
    "seed_repeat_all_tables_equal": stages["seed"]["db"] == stages["seed-repeat"]["db"],
    "seed_final_current_all_tables_equal": stages["seed"]["db"]
    == stages["final"]["db"]
    == current["db"],
    "common_browser_fixture": {name: name not in changed_files for name in common},
    "metadata_qualification": "Developer README describes three protected fixture files; final protected.common_browser_fixture count is two. All three hashes independently match, so the two-file counter understates coverage; it does not prove only two were preserved.",
    "historical_snapshot_acquisition": "Developer-provided private archive. Current file hashes and current DB snapshot independently recalculated; historical acquisition itself cannot be re-enacted.",
}
assert connection.settings_dict["NAME"] == "y3gym_m1"
assert str(connection.settings_dict["PORT"]) == "55438"
with transaction.atomic(), connection.cursor() as cursor:
    cursor.execute("SET TRANSACTION READ ONLY")

    def rows(table, ids=None):
        sql = "SELECT row_to_json(t) FROM " + connection.ops.quote_name(table) + " t"
        if ids is not None:
            cursor.execute(sql + " WHERE id = ANY(%s)", [[int(key) for key in ids]])
        else:
            cursor.execute(sql)
        return [row[0] for row in cursor.fetchall()]

    profiles = rows("news_trainer")
    photos = {profile["photo_id"] for profile in profiles}
    profile_ids = {str(profile["id"]) for profile in profiles}
    types = {
        row["id"]: (row["app_label"], row["model"])
        for row in rows("django_content_type")
    }
    references = rows(
        "wagtailcore_referenceindex", added_rows["wagtailcore_referenceindex"]
    )
    search = rows("wagtailsearch_indexentry", added_rows["wagtailsearch_indexentry"])
    revisions = rows("wagtailcore_revision", added_rows["wagtailcore_revision"])
    log = rows("wagtailcore_modellogentry", added_rows["wagtailcore_modellogentry"])
    permissions = rows("auth_permission", added_rows["auth_permission"])
    permission_map = {row["id"]: row for row in permissions}
    groups = rows("auth_group_permissions", added_rows["auth_group_permissions"])
    association = {
        "profiles_exact_A_B_no_claims": {row["name"] for row in profiles}
        == {"트레이너 A", "트레이너 B"}
        and all(row["position"] == "" for row in profiles),
        "no_biography_rows": len(rows("news_trainerbiography")) == 0,
        "reference_index_count": len(references),
        "reference_index_ownership": all(
            (
                types[row["content_type_id"]] == ("news", "trainer")
                and str(row["object_id"]) in profile_ids
                and row["model_path"] in {"branch", "photo"}
            )
            or (
                types[row["content_type_id"]] == ("news", "contentimage")
                and int(row["object_id"]) in photos
                and row["model_path"] == "collection"
            )
            for row in references
        ),
        "search_index_count": len(search),
        "search_image_ownership": all(
            types[row["content_type_id"]] == ("news", "contentimage")
            and int(row["object_id"]) in photos
            for row in search
        ),
        "revision_and_log_ownership": all(
            types[row["content_type_id"]] == ("news", "trainer")
            and str(row["object_id"]) in profile_ids
            for row in revisions + log
        ),
        "permission_types": all(
            types[row["content_type_id"]]
            in {("news", "trainer"), ("news", "trainerbiography")}
            for row in permissions
        ),
        "group_permissions_exact_add_change_view_publish": {
            permission_map[row["permission_id"]]["codename"] for row in groups
        }
        == {"add_trainer", "change_trainer", "view_trainer", "publish_trainer"},
        "added_image_ids_equal_profile_photos": {
            int(key) for key in added_rows["news_contentimage"]
        }
        == photos,
        "renditions_owned_by_new_photos": all(
            row["image_id"] in photos
            for row in rows("news_rendition", added_rows["news_rendition"])
        ),
    }
    report["read_only_seed_association"] = association
report["status"] = (
    "PASS"
    if report["exactly_reported_16_changes"]
    and not report["modified_old_rows"]
    and not report["removed_old_rows"]
    and report["seed_repeat_all_tables_equal"]
    and report["seed_final_current_all_tables_equal"]
    and all(report["common_browser_fixture"].values())
    and all(
        value is True
        for key, value in association.items()
        if not key.endswith("_count")
    )
    and association["reference_index_count"] == 6
    and association["search_index_count"] == 2
    else "FAIL"
)
with (output / "historical-preservation.json").open("x") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False))
assert report["status"] == "PASS"
