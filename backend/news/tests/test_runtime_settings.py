import os
import secrets
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, SimpleTestCase, override_settings

from config.runtime import read_runtime


class RuntimeSettingsTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.base = self.root / "backend"
        self.base.mkdir()
        self.values = {
            "Y3GYM_ENV": "production",
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(48),
            "Y3GYM_DB_NAME": "y3gym_ops_boundary",
            "Y3GYM_DB_USER": "ops_boundary",
            "Y3GYM_DB_PASSWORD": secrets.token_urlsafe(32),
            "Y3GYM_DB_HOST": "localhost",
            "Y3GYM_DB_PORT": "5432",
            "Y3GYM_ALLOWED_HOSTS": "gym.example.invalid,admin.example.invalid",
            "Y3GYM_ADMIN_ORIGIN": "https://admin.example.invalid",
            "Y3GYM_MEDIA_ROOT": str(self.root / "private"),
            "Y3GYM_STATIC_ROOT": str(self.root / "collected"),
        }

    def invalid(self, **changes):
        values = {**self.values, **changes}
        with self.assertRaises(ImproperlyConfigured):
            read_runtime(self.base, values)

    def test_development_defaults_preserve_existing_contract(self):
        values = {
            k: v
            for k, v in self.values.items()
            if k.startswith("Y3GYM_DB_") or k == "DJANGO_SECRET_KEY"
        }
        values["Y3GYM_DB_NAME"] = "test_y3gym_fixture"
        actual = read_runtime(self.base, values)
        self.assertEqual(actual["Y3GYM_ENV"], "development")
        self.assertEqual(
            actual["ALLOWED_HOSTS"], ["127.0.0.1", "localhost", "testserver"]
        )
        self.assertEqual(actual["WAGTAILADMIN_BASE_URL"], "http://localhost:8768")
        self.assertEqual(actual["PROTOTYPE_URL"], "http://localhost:8767")
        self.assertEqual(actual["MEDIA_ROOT"], self.base / ".private-media")
        self.assertFalse(actual["SECURE_SSL_REDIRECT"])

    def test_production_requires_each_field_instead_of_local_defaults(self):
        for key in self.values.keys() - {"Y3GYM_ENV"}:
            with self.subTest(field=key):
                values = dict(self.values)
                values.pop(key)
                with self.assertRaisesMessage(ImproperlyConfigured, key):
                    read_runtime(self.base, values)

    def test_production_never_loads_dotenv_to_fill_a_missing_secret(self):
        values = dict(self.values)
        values.pop("DJANGO_SECRET_KEY")

        # A loader that would inject development credentials must never run.
        def inject_local(*args, **kwargs):
            os.environ.update(
                DJANGO_SECRET_KEY=self.values["DJANGO_SECRET_KEY"],
                Y3GYM_DB_NAME="y3gym_m1",
            )

        with (
            patch.dict(os.environ, values, clear=True),
            patch("config.runtime.load_dotenv", side_effect=inject_local),
        ):
            with self.assertRaisesMessage(
                ImproperlyConfigured, "DJANGO_SECRET_KEY is required"
            ):
                read_runtime(self.base)

    def test_dotenv_cannot_silently_select_production(self):
        values = dict(self.values)
        values.pop("Y3GYM_ENV")
        with (
            patch.dict(os.environ, values, clear=True),
            patch(
                "config.runtime.load_dotenv",
                side_effect=lambda *a, **kw: os.environ.update(Y3GYM_ENV="production"),
            ),
        ):
            with self.assertRaisesMessage(ImproperlyConfigured, "Choose Y3GYM_ENV"):
                read_runtime(self.base)
        self.invalid(Y3GYM_ENV="prod")

    def test_development_or_template_secrets_and_DB_names_are_rejected(self):
        for value in [
            "short",
            "x" * 64,
            "django-insecure-" + "0123456789abcdef" * 4,
            "<secret>",
        ]:
            with self.subTest(secret_kind=value[:3]):
                self.invalid(DJANGO_SECRET_KEY=value)
        for name in [
            "test_y3gym_fixture",
            "TEST_y3gym_fixture",
            "y3gym_m1",
            "y3gym_v2_m1",
            "<database>",
            "changeme",
        ]:
            with self.subTest(name=name):
                self.invalid(Y3GYM_DB_NAME=name)

    def test_explicit_loopback_DB_is_allowed_but_invalid_connection_fields_fail(self):
        self.assertEqual(
            read_runtime(self.base, self.values)["DATABASES"]["default"]["HOST"],
            "localhost",
        )
        for value in ["0", "65536", "bad", ""]:
            with self.subTest(port=value):
                self.invalid(Y3GYM_DB_PORT=value)
        self.invalid(Y3GYM_DB_HOST="postgres://localhost")
        value = " " + self.values["Y3GYM_DB_PASSWORD"] + " "
        self.assertTrue(
            read_runtime(self.base, {**self.values, "Y3GYM_DB_PASSWORD": value})[
                "DATABASES"
            ]["default"]["PASSWORD"].startswith(" ")
        )

    def test_operating_hosts_cannot_be_wildcard_or_local_preview_hosts(self):
        for host in [
            "*",
            ".example.invalid",
            "localhost",
            "127.0.0.1",
            "[::1]",
            "testserver",
            "0.0.0.0",
            "gym.example.invalid:8443",
            "https://gym.example.invalid",
            "bad..host",
            "2001:db8::1",
        ]:
            with self.subTest(host=host):
                self.invalid(Y3GYM_ALLOWED_HOSTS=host)

    def test_origins_require_https_and_explicit_matching_admin_host(self):
        for value in [
            "http://admin.example.invalid",
            "https://localhost",
            "https://other.example.invalid",
            "https://admin.example.invalid/admin/",
            "https://user:password@admin.example.invalid",
            "https://admin.example.invalid#fragment",
        ]:
            with self.subTest(origin_kind=value.split(":")[0]):
                self.invalid(Y3GYM_ADMIN_ORIGIN=value)
        self.invalid(Y3GYM_CSRF_TRUSTED_ORIGINS="http://gym.example.invalid")
        self.invalid(Y3GYM_CSRF_TRUSTED_ORIGINS="https://*.example.invalid")
        self.invalid(Y3GYM_PROTOTYPE_URL="http://localhost:8767")

    def test_production_security_defaults_do_not_invent_proxy_or_hsts_policy(self):
        actual = read_runtime(self.base, self.values)
        self.assertTrue(actual["SESSION_COOKIE_SECURE"])
        self.assertTrue(actual["CSRF_COOKIE_SECURE"])
        self.assertTrue(actual["SECURE_SSL_REDIRECT"])
        self.assertIsNone(actual["SECURE_PROXY_SSL_HEADER"])
        self.assertEqual(actual["SECURE_HSTS_SECONDS"], 0)
        self.assertFalse(actual["SECURE_HSTS_INCLUDE_SUBDOMAINS"])
        self.assertFalse(actual["SECURE_HSTS_PRELOAD"])
        self.assertEqual(actual["PROTOTYPE_URL"], "")
        proxy = read_runtime(self.base, {**self.values, "Y3GYM_TRUST_PROXY_HTTPS": "1"})
        self.assertEqual(
            proxy["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https")
        )
        for configuration, expected in [(actual, False), (proxy, True)]:
            with override_settings(
                SECURE_PROXY_SSL_HEADER=configuration["SECURE_PROXY_SSL_HEADER"]
            ):
                request = RequestFactory().get("/", HTTP_X_FORWARDED_PROTO="https")
                self.assertEqual(request.is_secure(), expected)
        self.invalid(Y3GYM_TRUST_PROXY_HTTPS="true")
        self.invalid(Y3GYM_SECURE_HSTS_SECONDS="-1")

    def test_paths_cannot_expose_private_media_sources_or_QA_runtime(self):
        for static, media in [
            ("relative", str(self.root / "private")),
            (str(self.root / "same"), str(self.root / "same")),
            (str(self.root / "static"), str(self.root / "static/media")),
            (str(self.root / "media/static"), str(self.root / "media")),
            (str(self.root), str(self.root / "private")),
            (str(self.root / ".local"), str(self.root / "private")),
            (str(self.root / ".local/qa/run/static"), str(self.root / "private")),
            (str(self.root / "static"), str(self.root / "prototype/uploads")),
            (str(self.root / "static"), str(self.base / "news/static/uploads")),
            ("/", str(self.root / "private")),
        ]:
            with self.subTest(static=static, media=media):
                self.invalid(Y3GYM_STATIC_ROOT=static, Y3GYM_MEDIA_ROOT=media)

    def test_symlink_alias_cannot_hide_static_and_media_overlap(self):
        private = self.root / "private"
        private.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(private, target_is_directory=True)
        self.invalid(Y3GYM_STATIC_ROOT=str(alias))

    def test_invalid_mode_log_level_and_non_directory_path_fail_clearly(self):
        self.invalid(Y3GYM_ENV="")
        self.invalid(Y3GYM_LOG_LEVEL="VERBOSE")
        file = self.root / "ordinary-file"
        file.write_text("fixture")
        self.invalid(Y3GYM_MEDIA_ROOT=str(file))
