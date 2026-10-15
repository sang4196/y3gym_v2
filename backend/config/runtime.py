"""Small development/production boundary; errors name fields, never their values."""

import ipaddress
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


def read_runtime(base_dir, environ=None):
    values = os.environ if environ is None else dict(environ)
    mode = values.get("Y3GYM_ENV", "development").strip()
    if mode not in {"development", "production"}:
        raise ImproperlyConfigured("Y3GYM_ENV must be development or production")
    if mode == "development" and environ is None:
        load_dotenv(base_dir / ".env.local", override=False)
        if values.get("Y3GYM_ENV", "development").strip() != mode:
            raise ImproperlyConfigured("Choose Y3GYM_ENV before loading .env.local")
    production = mode == "production"

    def required(name):
        raw = values.get(name, "")
        value = raw.strip()
        if not value:
            raise ImproperlyConfigured(f"{name} is required")
        if production and (
            value.lower() in {"changeme", "change-me", "replace-me", "todo"}
            or (value.startswith("<") and value.endswith(">"))
        ):
            raise ImproperlyConfigured(f"{name} cannot be a template placeholder")
        return raw if name in {"DJANGO_SECRET_KEY", "Y3GYM_DB_PASSWORD"} else value

    def integer(name, default, minimum=0, maximum=None):
        raw = values.get(name, str(default)).strip()
        if not raw.isdecimal():
            raise ImproperlyConfigured(f"{name} must be an integer")
        result = int(raw)
        if result < minimum or (maximum is not None and result > maximum):
            raise ImproperlyConfigured(f"{name} is out of range")
        return result

    def flag(name):
        raw = values.get(name, "0").strip()
        if raw not in {"0", "1"}:
            raise ImproperlyConfigured(f"{name} must be 0 or 1")
        return raw == "1"

    def host(name, value, public=False):
        bare = value.removeprefix("[").removesuffix("]")
        try:
            address = ipaddress.ip_address(bare)
        except ValueError:
            valid = re.fullmatch(
                r"(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", value
            ) and all(
                label
                and len(label) <= 63
                and not label.startswith("-")
                and not label.endswith("-")
                for label in value.split(".")
            )
            local = value.lower() in {
                "localhost",
                "testserver",
            } or value.lower().endswith(".localhost")
        else:
            valid = True
            local = address.is_loopback or address.is_unspecified
        if not valid or (public and local):
            raise ImproperlyConfigured(f"{name} contains an invalid/local host")
        return value

    def origin(name, value, allowed=None):
        try:
            parsed = urlsplit(value)
            valid = (
                parsed.scheme in ({"https"} if production else {"http", "https"})
                and parsed.hostname
                and not parsed.username
                and not parsed.password
                and parsed.path in {"", "/"}
                and not parsed.query
                and not parsed.fragment
                and (parsed.port is None or 1 <= parsed.port <= 65535)
            )
        except ValueError:
            valid = False
        if not valid:
            raise ImproperlyConfigured(
                f"{name} must be an explicit {'HTTPS' if production else 'HTTP(S)'} origin"
            )
        host(name, parsed.hostname, public=production)
        if allowed is not None and parsed.hostname not in [
            h.strip("[]").lower() for h in allowed
        ]:
            raise ImproperlyConfigured(f"{name} host must be in Y3GYM_ALLOWED_HOSTS")
        return value.rstrip("/")

    secret = required("DJANGO_SECRET_KEY")
    if production and (
        len(secret) < 50
        or len(set(secret)) < 5
        or secret.startswith("django-insecure-")
        or re.search(
            r"change.?me|replace.?me|dev.?secret|test.?secret|local.?secret",
            secret,
            re.I,
        )
    ):
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be a new strong production secret"
        )
    database = {
        key: required("Y3GYM_DB_" + key)
        for key in ["NAME", "USER", "PASSWORD", "HOST", "PORT"]
    }
    integer("Y3GYM_DB_PORT", 0, 1, 65535)
    if not database["HOST"].startswith("/"):
        host("Y3GYM_DB_HOST", database["HOST"])
    if production and (
        database["NAME"].lower().startswith("test_")
        or database["NAME"] in {"y3gym_m1", "y3gym_v2_m1"}
    ):
        raise ImproperlyConfigured(
            "Y3GYM_DB_NAME cannot be a test/development database in production"
        )

    hosts = [
        v.strip()
        for v in (
            required("Y3GYM_ALLOWED_HOSTS")
            if production
            else values.get("Y3GYM_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")
        ).split(",")
    ]
    for value in hosts:
        if ":" in value and not (value.startswith("[") and value.endswith("]")):
            raise ImproperlyConfigured("Y3GYM_ALLOWED_HOSTS IPv6 must use brackets")
        host("Y3GYM_ALLOWED_HOSTS", value, public=production)
    admin = origin(
        "Y3GYM_ADMIN_ORIGIN",
        required("Y3GYM_ADMIN_ORIGIN")
        if production
        else values.get("Y3GYM_ADMIN_ORIGIN", "http://localhost:8768"),
        hosts,
    )
    prototype_url = values.get(
        "Y3GYM_PROTOTYPE_URL", "" if production else "http://localhost:8767"
    ).strip()
    if prototype_url:
        prototype_url = origin(
            "Y3GYM_PROTOTYPE_URL", prototype_url, hosts if production else None
        )
    trusted = [
        origin("Y3GYM_CSRF_TRUSTED_ORIGINS", v.strip())
        for v in values.get("Y3GYM_CSRF_TRUSTED_ORIGINS", "").split(",")
        if v.strip()
    ]

    def directory(name, default):
        value = required(name) if production else values.get(name, str(default))
        path = Path(value)
        if not path.is_absolute():
            raise ImproperlyConfigured(f"{name} must be an absolute directory")
        resolved = path.resolve()
        if resolved == Path(resolved.anchor) or (
            resolved.exists() and not resolved.is_dir()
        ):
            raise ImproperlyConfigured(f"{name} must be a dedicated directory")
        return resolved

    media = directory("Y3GYM_MEDIA_ROOT", base_dir / ".private-media")
    static = directory("Y3GYM_STATIC_ROOT", base_dir / ".static")
    prototype = base_dir.parent / "prototype"
    source_roots = [
        base_dir.resolve(),
        prototype.resolve(),
        (base_dir.parent / ".local/qa").resolve(),
    ]
    if production and any(
        path.is_relative_to(source_roots[2]) for path in [static, media]
    ):
        raise ImproperlyConfigured("Production static/media roots cannot be QA runtime")
    if media.is_relative_to(static) or static.is_relative_to(media):
        raise ImproperlyConfigured(
            "Y3GYM_STATIC_ROOT and Y3GYM_MEDIA_ROOT must be separate"
        )
    if any(
        root.is_relative_to(static) or root.is_relative_to(media)
        for root in source_roots
    ):
        raise ImproperlyConfigured(
            "Static/media roots cannot contain application sources or QA runtime"
        )
    if any(
        media.is_relative_to(root)
        for root in [prototype.resolve(), (base_dir / "news/static").resolve()]
    ):
        raise ImproperlyConfigured(
            "Private media cannot be inside a static source directory"
        )
    level = values.get("Y3GYM_LOG_LEVEL", "INFO").strip().upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ImproperlyConfigured("Y3GYM_LOG_LEVEL is invalid")
    database.update(ENGINE="django.db.backends.postgresql", ATOMIC_REQUESTS=True)
    return {
        "Y3GYM_ENV": mode,
        "SECRET_KEY": secret,
        "DATABASES": {"default": database},
        "ALLOWED_HOSTS": hosts,
        "WAGTAILADMIN_BASE_URL": admin,
        "PROTOTYPE_URL": prototype_url,
        "MEDIA_ROOT": media,
        "STATIC_ROOT": static,
        "KAKAO_MAP_JS_KEY": values.get("Y3GYM_KAKAO_MAP_JS_KEY", "").strip(),
        "CSRF_TRUSTED_ORIGINS": trusted,
        "SESSION_COOKIE_SECURE": production,
        "CSRF_COOKIE_SECURE": production,
        "SECURE_SSL_REDIRECT": production,
        "SECURE_PROXY_SSL_HEADER": ("HTTP_X_FORWARDED_PROTO", "https")
        if flag("Y3GYM_TRUST_PROXY_HTTPS")
        else None,
        "SECURE_HSTS_SECONDS": integer("Y3GYM_SECURE_HSTS_SECONDS", 0),
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
        "SECURE_HSTS_PRELOAD": False,
        "LOGGING": {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {"console": {"class": "logging.StreamHandler"}},
            "loggers": {
                name: {"handlers": ["console"], "level": level, "propagate": False}
                for name in ["django", "django.server"]
            },
        },
    }
