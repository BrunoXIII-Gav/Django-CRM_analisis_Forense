"""
Default settings module — uses development settings.
Override with DJANGO_SETTINGS_MODULE env var for production.
"""

from .dev import *  # noqa: F401, F403
