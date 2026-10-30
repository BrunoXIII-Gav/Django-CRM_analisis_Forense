"""Local HTTP laboratory with explicit MySQL, never dev.py's SQLite override."""
import os
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F401,F403

DEBUG = False
if not os.environ.get("SECRET_KEY") or not os.environ.get("DB_PASSWORD"):
    raise ImproperlyConfigured("Lab requires explicit SECRET_KEY and DB_PASSWORD")
DATABASES = {"default": {
    "ENGINE": "django.db.backends.mysql",
    "NAME": os.environ.get("DB_NAME", "crm_lab"),
    "USER": os.environ.get("DB_USER", "crm_runtime"),
    "PASSWORD": os.environ["DB_PASSWORD"],
    "HOST": os.environ.get("DB_HOST", "db"),
    "PORT": os.environ.get("DB_PORT", "3306"),
    "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES', default_storage_engine=INNODB"},
}}
ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h]
SECURE_SSL_REDIRECT = False  # loopback HTTP only, Compose binds 127.0.0.1
STATIC_ROOT = BASE_DIR / "staticfiles"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
