from django.core.management import call_command
from wagtail.models import Collection


def ensure_collection_root():
    # TransactionTestCase flush removes migration-created Wagtail tree rows.
    # Restore this dependency only in the isolated test DB, before image/seed use.
    return Collection.get_first_root_node() or Collection.add_root(name="Root")


def bootstrap_browser_review():
    ensure_collection_root()
    for command in [
        "bootstrap_review",
        "bootstrap_brand_review",
        "bootstrap_branch_review",
    ]:
        call_command(command, verbosity=0)
