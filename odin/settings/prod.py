from .base import *  # noqa

DEBUG = False

ALLOWED_HOSTS = ("odin.local",)

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
