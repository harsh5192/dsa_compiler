"""
Django settings for the personal offline-first DSA platform.

Everything here is designed to work on a laptop with no internet access:
SQLite for storage, local static assets, no external auth/CDN/API calls.
"""

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

#: Placeholder used when nothing is configured; replaced below by a random key.
DEV_SECRET_KEY = "django-insecure-dev-key-change-me-for-personal-local-use"
SECRET_KEY = os.environ.get("DSA_SECRET_KEY", DEV_SECRET_KEY)

DEBUG = os.environ.get("DSA_DEBUG", "1") == "1"

# Single-user local platform: localhost plus any local/LAN address.
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DSA_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],0.0.0.0").split(",")
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("DSA_CSRF_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    if o.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.accounts",
    "apps.problems",
    "apps.sheets",
    "apps.execution",
    "apps.progress",
    "apps.submissions",
    "apps.imports",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.platform_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database - SQLite by default, PostgreSQL ready by only swapping this block
# ---------------------------------------------------------------------------

if os.environ.get("DSA_DB_ENGINE") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DSA_DB_NAME", "dsa_platform"),
            "USER": os.environ.get("DSA_DB_USER", "dsa"),
            "PASSWORD": os.environ.get("DSA_DB_PASSWORD", ""),
            "HOST": os.environ.get("DSA_DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DSA_DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("DSA_DB_PATH", str(BASE_DIR / "db.sqlite3")),
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# I18N / static / media
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DSA_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:index"
LOGOUT_REDIRECT_URL = "accounts:login"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# ---------------------------------------------------------------------------
# Transport / cookie hardening
#
# The default install runs on http://localhost, where secure-only cookies would
# simply never be sent.  Set DSA_HTTPS=1 (or run behind TLS) to turn the strict
# behaviour on for a shared or remote deployment.
# ---------------------------------------------------------------------------

DSA_HTTPS = os.environ.get("DSA_HTTPS", "0") == "1"

SECURE_SSL_REDIRECT = DSA_HTTPS
SESSION_COOKIE_SECURE = DSA_HTTPS
CSRF_COOKIE_SECURE = DSA_HTTPS
SECURE_HSTS_SECONDS = int(os.environ.get("DSA_HSTS_SECONDS", "0" if not DSA_HTTPS else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = DSA_HTTPS
SECURE_HSTS_PRELOAD = DSA_HTTPS
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # the editor reads the token from the cookie
X_FRAME_OPTIONS = "DENY"

# With no DSA_SECRET_KEY in the environment, fall back to a random per-process
# key so an install never ships a shared secret.  Sessions then end when the
# server restarts, which is the right trade-off for a local app; set
# DSA_SECRET_KEY (see .env.example) to keep people signed in.
if not os.environ.get("DSA_SECRET_KEY") and SECRET_KEY == DEV_SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(64)

# ---------------------------------------------------------------------------
# REST framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
}

# ---------------------------------------------------------------------------
# Platform / code execution
# ---------------------------------------------------------------------------

# Which sandbox backend to use: "subprocess" (default, no extra deps) or
# "docker" (stronger isolation, needs the docker CLI available).
DSA_EXECUTION_BACKEND = os.environ.get("DSA_EXECUTION_BACKEND", "subprocess")

# Per-language wall clock limits (seconds).
DSA_TIME_LIMIT = float(os.environ.get("DSA_TIME_LIMIT", "5"))
# Extra slack on top of the per-test limit for the whole submission batch.
DSA_BATCH_TIME_LIMIT = float(os.environ.get("DSA_BATCH_TIME_LIMIT", "30"))
# Address-space cap for a single test run, in megabytes.
DSA_MEMORY_LIMIT_MB = int(os.environ.get("DSA_MEMORY_LIMIT_MB", "512"))
# Cap for stdout/stderr captured from a run, in bytes.
DSA_OUTPUT_LIMIT = int(os.environ.get("DSA_OUTPUT_LIMIT", str(512 * 1024)))
# Temp build/run directory root.
DSA_WORK_DIR = os.environ.get("DSA_WORK_DIR", str(BASE_DIR / "media" / "exec"))
# Optional docker image per language is stored on the Language model; this is
# the fallback image for languages without one.
DSA_DOCKER_IMAGE = os.environ.get("DSA_DOCKER_IMAGE", "python:3.12-slim")
# Optionally drop filesystem/network isolation extras (Linux only, best effort).
DSA_DISABLE_NETWORK = os.environ.get("DSA_DISABLE_NETWORK", "0") == "1"

DATA_DIR = BASE_DIR / "data"

# Branding, shown in the header and the page titles.
DSA_PLATFORM_NAME = os.environ.get("DSA_PLATFORM_NAME", "DSA Studio")
DSA_PLATFORM_TAGLINE = os.environ.get(
    "DSA_PLATFORM_TAGLINE", "Sheets, code and progress, offline."
)

# Editors offered in the UI. Only "monaco" (bundled locally in
# static/editor/monaco) and "plain" (built-in fallback textarea) are known.
DSA_EDITORS = ["monaco", "plain"]
DSA_DEFAULT_EDITOR = os.environ.get("DSA_DEFAULT_EDITOR", "monaco")

FILE_UPLOAD_MAX_MEMORY_SIZE = 32 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 64 * 1024 * 1024

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "dsa.execution": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
