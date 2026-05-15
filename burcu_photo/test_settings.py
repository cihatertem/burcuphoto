import os
import secrets
import shutil

from django.db import models
from django.db.models.expressions import Expression
from django.test.runner import DiscoverRunner

from burcu_photo.settings import (
    AUTH_PASSWORD_VALIDATORS,
    BASE_DIR,
    DB_KEEPALIVES_COUNT,
    DB_KEEPALIVES_IDLE,
    DB_KEEPALIVES_INTERVAL,
    DEBUG,
    DEFAULT_AUTO_FIELD,
    EMAIL_HOST,
    EMAIL_HOST_PASSWORD,
    EMAIL_HOST_USER,
    EMAIL_PORT,
    EMAIL_USE_TLS,
    INSTALLED_APPS,
    LANGUAGE_CODE,
    MEDIA_URL,
    MIDDLEWARE,
    RATELIMIT_USE_CACHE,
    ROOT_URLCONF,
    SECURE_CSP,
    SITE_ID,
    STATIC_ROOT,
    STATIC_URL,
    STATICFILES_DIRS,
    TEMPLATES,
    TIME_ZONE,
    USE_PGBOUNCER,
    USE_TZ,
    WSGI_APPLICATION,
)

SECRET_KEY = secrets.token_urlsafe(50)

# Custom Test Settings
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
RATELIMIT_ENABLE = False
os.environ["EMAIL_RECEIVER_ONE"] = "receiver1@example.com"
os.environ["EMAIL_RECEIVER_TWO"] = "receiver2@example.com"
os.environ["ADMIN_ADDRESS"] = "test-admin/"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Bypass migrations that use PostgreSQL-specific features
MIGRATION_MODULES = {
    "base": None,
}

# Monkeypatch GinIndex and SearchVector for SQLite tests


class MockGinIndex(models.Index):
    def __init__(self, *args, **kwargs):
        kwargs.pop("config", None)
        super().__init__(*args, **kwargs)

    def create_sql(self, model, schema_editor, using=""):  # pyright: ignore[reportIncompatibleMethodOverride]
        return ""


try:
    import django.contrib.postgres.indexes

    django.contrib.postgres.indexes.GinIndex = MockGinIndex
except ImportError:
    pass


class MockSearchVector(Expression):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def resolve_expression(self, *args, **kwargs):
        return self


try:
    import django.contrib.postgres.search

    django.contrib.postgres.search.SearchVector = MockSearchVector
except ImportError:
    pass

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1", "[::1]"]
SECURE_SSL_REDIRECT = False

USE_S3 = False
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
MEDIA_ROOT = BASE_DIR / "test_media/"


class MediaCleanupTestRunner(DiscoverRunner):
    def teardown_test_environment(self, **kwargs):
        super().teardown_test_environment(**kwargs)
        if MEDIA_ROOT.exists():
            shutil.rmtree(MEDIA_ROOT)


TEST_RUNNER = "burcu_photo.test_settings.MediaCleanupTestRunner"

__all__ = [
    "BASE_DIR",
    "DEBUG",
    "INSTALLED_APPS",
    "SITE_ID",
    "MIDDLEWARE",
    "ROOT_URLCONF",
    "TEMPLATES",
    "WSGI_APPLICATION",
    "AUTH_PASSWORD_VALIDATORS",
    "LANGUAGE_CODE",
    "TIME_ZONE",
    "USE_TZ",
    "STATIC_URL",
    "STATIC_ROOT",
    "STATICFILES_DIRS",
    "MEDIA_URL",
    "DEFAULT_AUTO_FIELD",
    "EMAIL_HOST",
    "EMAIL_PORT",
    "EMAIL_USE_TLS",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "USE_PGBOUNCER",
    "DB_KEEPALIVES_IDLE",
    "DB_KEEPALIVES_INTERVAL",
    "DB_KEEPALIVES_COUNT",
    "RATELIMIT_USE_CACHE",
    "SECURE_CSP",
    "SECRET_KEY",
    "EMAIL_BACKEND",
    "DATABASES",
    "CACHES",
    "ALLOWED_HOSTS",
    "SECURE_SSL_REDIRECT",
    "USE_S3",
    "STORAGES",
    "MEDIA_ROOT",
    "TEST_RUNNER",
    "MIGRATION_MODULES",
    "RATELIMIT_ENABLE",
]
