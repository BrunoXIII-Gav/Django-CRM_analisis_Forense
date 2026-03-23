"""
Development settings — extends base.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ["*"]

# Use SQLite locally (no MySQL install needed)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Use console email backend in development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
