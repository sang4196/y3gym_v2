import json
import unittest
from unittest.mock import patch

import qa_docker as q
import qa_lifecycle as lifecycle


class DockerOwnershipTests(unittest.TestCase):
    value = {"id": "qa-20261015T000000Z-123456abcdef", "owner_hash": "a" * 64}

    def test_foreign_owner_resource_is_refused_before_any_deletion(self):
        responses = [
            b"container-id\n",
            b"",
            b"",
            json.dumps(
                [
                    {
                        "Id": "container-id",
                        "Config": {
                            "Labels": {
                                q.RUN_LABEL: self.value["id"],
                                q.OWNER_LABEL: "foreign",
                            }
                        },
                    }
                ]
            ).encode(),
        ]
        with (
            patch.object(q.subprocess, "check_output", side_effect=responses),
            patch.object(q.subprocess, "run") as deletion,
        ):
            with self.assertRaisesRegex(ValueError, "owner"):
                q.inspect_resources(self.value)
            deletion.assert_not_called()

    def test_resource_change_after_plan_refuses_deletion(self):
        with (
            patch.object(
                q, "inspect_resources", return_value=[{"kind": "volume", "id": "new"}]
            ),
            patch.object(q.subprocess, "run") as deletion,
        ):
            with self.assertRaisesRegex(ValueError, "changed"):
                q.remove_resources(self.value, [])
            deletion.assert_not_called()

    def test_docker_cleanup_plan_never_contacts_original_postgresql(self):
        value = {
            **self.value,
            "state": "READY",
            "resource_backend": "docker",
            "inode": [1, 2],
        }
        with (
            patch.object(lifecycle, "driver_live", return_value=False),
            patch.object(lifecycle, "owned_processes", return_value=[]),
            patch.object(lifecycle, "tree_plan", return_value=[]),
            patch.object(q, "inspect_resources", return_value=[]),
            patch.object(lifecycle, "db_connect") as original_database,
        ):
            plan = lifecycle.cleanup_plan("owned-run", value, "owned-token")
            self.assertEqual(plan["databases"], [])
            original_database.assert_not_called()


if __name__ == "__main__":
    unittest.main()
