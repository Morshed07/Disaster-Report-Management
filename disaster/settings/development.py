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
