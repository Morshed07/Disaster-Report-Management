"""
Production settings for disaster project.
Inherits from base and configures PostgreSQL, static files, and security.
"""
import os

from .base import *  # noqa: F401, F403


# ---------------------
# Production Overrides
# ---------------------

DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost").split(",")

# PostgreSQL for production / Docker
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "disaster_db"),
        "USER": os.environ.get("POSTGRES_USER", "disaster_user"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "disaster_pass"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Static files — served by whitenoise or nginx in production
STATIC_ROOT = BASE_DIR / "staticfiles"

# Security settings for production
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
