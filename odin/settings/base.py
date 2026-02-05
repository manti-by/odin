"""
Django settings for the Odin project.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
import secrets
from decimal import Decimal
from pathlib import Path


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# Keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# Don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ("odin.local", "192.168.1.100")

# Application definition

INSTALLED_APPS = [
    "odin.apps.sensors",
    "odin.apps.relays",
    "odin.apps.core",
    "odin.apps.currency",
    "odin.apps.electricity",
    "odin.apps.music",
    "odin.apps.weather",
    "odin.apps.provider",
    "odin.api",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "command_log",
    "django_rq",
    "django_apscheduler",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "odin.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "odin.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_NAME", "odin"),
        "USER": os.getenv("POSTGRES_USER", "odin"),
        "PASSWORD": os.getenv("POSTGRES_PASS", "odin"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", 5432),
    }
}


# Cache
# https://docs.djangoproject.com/en/5.0/ref/settings/#caches

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_db = os.getenv("REDIS_DB", "0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{redis_host}:6379/{redis_db}",
        "OPTIONS": {
            "MAX_ENTRIES": 5000,
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        },
    }
}

DEFAULT_RQ_TIMEOUT = os.getenv("DEFAULT_RQ_TIMEOUT", 600)

RQ_QUEUES = {
    "default": {"USE_REDIS_CACHE": "default", "DEFAULT_TIMEOUT": DEFAULT_RQ_TIMEOUT},
}

QUEUE_SCHEDULED_TASKS = True


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/


def _(x):
    return x


LANGUAGE_CODE = "ru"

LANGUAGES = (("ru", _("Russian")),)

LOCALE_PATHS = (BASE_DIR / "locale",)

TIME_ZONE = "Europe/Minsk"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATICFILES_DIRS = [BASE_DIR / "static"]

STATIC_ROOT = os.getenv("STATIC_ROOT", BASE_DIR.parent / "static")
STATIC_URL = "static/"

MEDIA_ROOT = os.getenv("MEDIA_ROOT", BASE_DIR.parent / "media")
MEDIA_URL = "media/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# https://docs.djangoproject.com/en/5.2/ref/logging/

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
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": "/var/log/odin/django.log",
            "formatter": "simple",
        },
    },
    "loggers": {
        "": {"handlers": ["console"], "level": "INFO"},
    },
}

# Rest Framework
# https://www.django-rest-framework.org/tutorial/quickstart/

REST_FRAMEWORK = {
    "PAGE_SIZE": 15,
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
}


# Music library settings

MUSIC_PATH = os.getenv("MUSIC_PATH", "/mnt/data/Music/Library")


# Sensors and relays

DEFAULT_TEMP_HYSTERESIS = Decimal(0.5)

CHART_OPTIONS = {
    "DS18B20": {
        "y_min": 20,
        "y_max": 45,
        "y_title": f"{_('Temperature')} °C",
        "x_title": _("Time"),
        "time_unit": "minute",
        "time_tooltip_format": "ll HH:mm",
    },
    "ESP8266": {
        "y_min": 18,
        "y_max": 32,
        "y_title": f"{_('Temperature')} °C",
        "x_title": _("Time"),
        "time_unit": "minute",
        "time_tooltip_format": "ll HH:mm",
    },
}

# Kafka settings

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.1.100:9092").split(",")
KAFKA_RELAY_TOPIC = os.getenv("KAFKA_RELAY_TOPIC", "coruscant")

# Web Push settings

FIREBASE_CLOUD_MESSAGING_PUBLIC_KEY = os.getenv("FIREBASE_CLOUD_MESSAGING_PUBLIC_KEY", "")
FIREBASE_CLOUD_MESSAGING_PRIVATE_KEY = os.getenv("FIREBASE_CLOUD_MESSAGING_PRIVATE_KEY", "")
FIREBASE_CLOUD_MESSAGING_ADMIN_EMAIL = os.getenv("FIREBASE_CLOUD_MESSAGING_ADMIN_EMAIL", "")

# UNET provider credentials
UNET_USERNAME = os.getenv("UNET_USERNAME", "")
UNET_PASSWORD = os.getenv("UNET_PASSWORD", "")
