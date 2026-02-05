from .base import *  # noqa

DEBUG = True

ALLOWED_HOSTS = ("*",)

SECRET_KEY = "test-secret-key-for-testing-only"

MEDIA_ROOT = "/tmp/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(levelname)s %(asctime)s %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "": {"handlers": ["console"], "level": "ERROR"},
    },
}
