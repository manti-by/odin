from .base import *  # noqa

os.environ.setdefault("DJANGO_RUNSERVER_HIDE_WARNING", "true")

DEBUG = True

ALLOWED_HOSTS = ("*",)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(levelname)s %(asctime)s %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "": {"handlers": ["console"], "level": "INFO"},
    },
}
