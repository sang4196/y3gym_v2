import runpy
from pathlib import Path
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase


class DeploymentTests(TestCase):
    def test_readiness_checks_database_without_exposing_configuration(self):
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.post("/healthz/").status_code, 405)

    def test_database_failure_is_unavailable_without_error_detail(self):
        with patch(
            "config.health.connection.cursor",
            side_effect=DatabaseError("private-database-detail"),
        ):
            response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})

    def test_invalid_worker_capacity_is_rejected(self):
        path = Path(__file__).resolve().parents[3] / "deploy/gunicorn.conf.py"
        for invalid in ["0", "-1", "many", "1000"]:
            with (
                self.subTest(value=invalid),
                patch.dict("os.environ", {"Y3GYM_WORKERS": invalid}),
            ):
                with self.assertRaises(ValueError):
                    runpy.run_path(str(path))
