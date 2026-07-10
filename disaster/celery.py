"""
Celery configuration for disaster project.

This module defines the Celery application instance used by all
async tasks across the project (e.g., sending emails).
"""
import os

from celery import Celery

# Default to development settings (overridden by env var in Docker)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "disaster.settings.development")

app = Celery("disaster")

# Read Celery config from Django settings, using the CELERY_ namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """A simple debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
