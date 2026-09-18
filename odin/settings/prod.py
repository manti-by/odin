from .base import *  # noqa

DEBUG = False

ALLOWED_HOSTS = ("odin.manti.by", "192.168.1.100")

# HTTPS cookie hardening for production
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = ("https://odin.manti.by", "http://192.168.1.100")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(levelname)s %(asctime)s %(message)s"},
        "verbose": {"format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "WARNING",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": "/var/log/odin/django.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "": {"handlers": ["console", "file"], "level": "WARNING"},
    },
}
