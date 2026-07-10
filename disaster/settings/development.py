"""
Development settings for disaster project.
Inherits from base and enables debug mode with SQLite.
"""
from .base import *  # noqa: F401, F403


# ---------------------
# Development Overrides
# ---------------------

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use SQLite for local development
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# -------------------------
# Celery Configuration
# -------------------------
# Use local Redis on a different port to avoid conflict with other apps
CELERY_BROKER_URL = "redis://localhost:6389/0"
CELERY_RESULT_BACKEND = "redis://localhost:6389/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
