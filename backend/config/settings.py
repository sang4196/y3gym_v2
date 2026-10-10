import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROTOTYPE_DIR = BASE_DIR.parent / "prototype"
load_dotenv(BASE_DIR / ".env.local")
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
INSTALLED_APPS = [
    "news",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "news.middleware.NoStoreContentMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "news.context.site_context",
            ]
        },
    }
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["Y3GYM_DB_NAME"],
        "USER": os.environ["Y3GYM_DB_USER"],
        "PASSWORD": os.environ["Y3GYM_DB_PASSWORD"],
        "HOST": os.environ["Y3GYM_DB_HOST"],
        "PORT": os.environ["Y3GYM_DB_PORT"],
        "ATOMIC_REQUESTS": True,
    }
}
LANGUAGE_CODE = "ko"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / ".static"
STATICFILES_DIRS = [("prototype", PROTOTYPE_DIR)]
MEDIA_ROOT = BASE_DIR / ".private-media"
MEDIA_URL = "/media/"
STORAGES = {
    "default": {"BACKEND": "news.storage.PrivateImageStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
WAGTAIL_SITE_NAME = "Y3GYM 콘텐츠 관리 · 로컬 검토"
WAGTAILADMIN_BASE_URL = "http://localhost:8768"
WAGTAILIMAGES_IMAGE_MODEL = "news.ContentImage"
WAGTAILIMAGES_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
WAGTAILDOCS_EXTENSIONS = []
WAGTAIL_ENABLE_UPDATE_CHECK = False
WAGTAILADMIN_COMMENTS_ENABLED = False
WAGTAIL_AUTOSAVE_INTERVAL = 0
WAGTAILADMIN_GLOBAL_EDIT_LOCK = True
WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_NAME = "y3gym_m1_session"
CSRF_COOKIE_NAME = "y3gym_m1_csrf"
X_FRAME_OPTIONS = "SAMEORIGIN"
PROTOTYPE_URL = os.environ.get("Y3GYM_PROTOTYPE_URL", "http://localhost:8767").rstrip(
    "/"
)
