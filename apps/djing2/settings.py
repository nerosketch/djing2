"""
Django settings for djing2 project.

Generated by 'django-admin startproject' using Django 2.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
from typing import overload, TypeVar, Union
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

_T = TypeVar("_T")

@overload
def get_secret(fname: str) -> str: ...

@overload
def get_secret(fname: str, default: _T) -> Union[str, _T]: ...

def get_secret(fname: str, default=None):
    try:
        secrets_dir_path = os.getenv("SECRETS_DIR_PATH", "/run/secrets")
        with open(os.path.join(secrets_dir_path, fname), 'r') as f:
            val = f.read().strip()
        return val
    except FileNotFoundError:
        return default


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_secret("DJANGO_SECRET_KEY")
if SECRET_KEY is None:
    raise OSError("DJANGO_SECRET_KEY secret not found")


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("APP_DEBUG", False)
DEBUG = bool(DEBUG)

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", ())
if ALLOWED_HOSTS:
    ALLOWED_HOSTS = ALLOWED_HOSTS.split('|')

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_EMAIL")

ADMINS = os.getenv("ADMINS")
if isinstance(ADMINS, str):
    import json
    ADMINS = json.loads(ADMINS)
else:
    ADMINS = [("Admin", "admin@localhost")]

# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "rest_framework",
    "rest_framework.authtoken",
    "encrypted_model_fields",
    "django_filters",
    "corsheaders",
    "guardian",
    "django_cleanup.apps.CleanupConfig",
    "webpush",
    "djing2.apps.Djing2Config",
    "groupapp.apps.GroupappConfig",
    "addresses.apps.AddressesConfig",
    "profiles.apps.ProfilesConfig",
    "services.apps.ServicesConfig",
    "gateways.apps.GatewaysConfig",
    "devices.apps.DevicesConfig",
    "networks.apps.NetworksConfig",
    "customers.apps.CustomersConfig",
    "messenger.apps.MessengerConfig",
    "tasks.apps.TasksConfig",
    "fin_app.apps.FinAppConfig",
    "traf_stat.apps.TrafStatConfig",
    "sitesapp.apps.SitesAppConfig",
    "radiusapp.apps.RadiusAppConfig",
    #"sorm_export.apps.SormExportConfig",
    "customer_comments.apps.CustomerCommentsConfig",
    "dynamicfields.apps.DynamicfieldsConfig",
    "customers_legal.apps.CustomersLegalConfig",
    "customer_contract.apps.CustomerContractConfig",

    #"webhooks.apps.WebhooksConfig",
]

if DEBUG:
    INSTALLED_APPS.insert(0, "django.contrib.admin")

MIDDLEWARE = [
    "djing2.middleware.XRealIPMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    # 'django.middleware.csrf.CsrfViewMiddleware',
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "djing2.lib.mixins.CustomCurrentSiteMiddleware",
]

ROOT_URLCONF = "djing2.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # 'DIRS': [os.path.join(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                # "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = (
    "djing2.lib.auth_backends.DjingAuthBackend",
    "guardian.backends.ObjectPermissionBackend",
    "djing2.lib.auth_backends.LocationAuthBackend",
)

WSGI_APPLICATION = "djing2.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "CONN_MAX_AGE": os.getenv('CONN_MAX_AGE', 300),
        "NAME": os.getenv("POSTGRES_DB", "djing2"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": get_secret("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "postgres"),
        "PORT": os.getenv("POSTGRES_PORT", 5432),
        "DISABLE_SERVER_SIDE_CURSORS": bool(os.getenv("DISABLE_SERVER_SIDE_CURSORS", False)),
    }
}


# if DEBUG:
#     CACHES = {
#         'default': {
#             'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
#         }
#     }
# else:
#     CACHES = {
#         'default': {
#             'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
#             'LOCATION': '127.0.0.1:11211',
#         }
#     }


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {filename} {name}: {message}',
            'style': '{',
        },
        'simple': {
            'format': '{asctime} {levelname}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        # 'file': {
        #     'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        #     'class': 'logging.FileHandler',
        #     'filename': os.getenv('DJING2_LOG_FILE', '/tmp/djing2.log'),
        #     'formatter': 'simple'
        # }
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            # 'handlers': ['file', 'console'],
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False
        },
        'djing2_logger': {
            # 'handlers': ['file', 'console'],
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False
        }
    }
}

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = "ru"

LANGUAGES = (
    ("ru", "Russian"),
    # ('en', _('English'))
)

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

LOCALE_PATHS = (os.path.join(PROJECT_PATH, "../locale"),)


TIME_ZONE = os.getenv("TIME_ZONE", "Europe/Simferopol")

USE_I18N = True

USE_L10N = False

USE_TZ = False

# Maximum file size is 50Mb
FILE_UPLOAD_MAX_MEMORY_SIZE = os.getenv("FILE_UPLOAD_MAX_MEMORY_SIZE", 52428800)

DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE

# time to session live, 1 week
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = "/static/"
if DEBUG:
    STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

# STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Example output: 2018-09-16
DATE_FORMAT = "Y-b-d"
DATETIME_FORMAT = "Y-b-d H:i"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "..", "media")

EMAIL_BACKEND = 'djing2.email_backend.Djing2EmailBackend'

DEFAULT_PICTURE = "/static/img/user_ava_min.gif"
AUTH_USER_MODEL = "profiles.BaseAccount"

# LOGIN_URL = reverse_lazy('acc_app:login')
# LOGIN_REDIRECT_URL = reverse_lazy('acc_app:setup_info')
# LOGOUT_URL = reverse_lazy('acc_app:logout')

TELEPHONE_REGEXP = os.getenv("TELEPHONE_REGEXP", r"^(\+[7893]\d{10,11})?$")

# Secret word for auth to api views by hash
API_AUTH_SECRET = get_secret("API_AUTH_SECRET")

# Allowed subnet for api
API_AUTH_SUBNET = os.getenv("API_AUTH_SUBNET", ("127.0.0.0/8", "10.0.0.0/8"))
if API_AUTH_SUBNET and isinstance(API_AUTH_SUBNET, str) and '|' in API_AUTH_SUBNET:
    API_AUTH_SUBNET = API_AUTH_SUBNET.split('|')


# public url for messenger bot
MESSENGER_BOT_PUBLIC_URL = os.getenv("MESSENGER_BOT_PUBLIC_URL")

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "djing2.lib.paginator.QueryPageNumberPagination",
    # 'PAGE_SIZE': 180,
    "DEFAULT_METADATA_CLASS": "rest_framework.metadata.SimpleMetadata",
    "DEFAULT_AUTHENTICATION_CLASSES": ["djing2.lib.authenticators.CustomTokenAuthentication"],
    "DEFAULT_FILTER_BACKENDS": [
        "djing2.lib.filters.CustomObjectPermissionsFilter",
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M",
    "DATE_FORMAT": "%Y-%m-%d",
    "DATETIME_INPUT_FORMATS": [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "rest_framework.permissions.IsAdminUser",
        # 'djing2.permissions.CustomizedDjangoObjectPermissions'
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'djing2.lib.renderer.CustomJSONRenderer',
        'rest_framework_csv.renderers.CSVRenderer',
    ]
}

# Guardian options
GUARDIAN_RAISE_403 = True
# GUARDIAN_AUTO_PREFETCH = True

if DEBUG:
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ALLOW_CREDENTIALS = True
    CORS_ORIGIN_WHITELIST = ("http://0.0.0.0:8080",)
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"].append(
        "rest_framework.authentication.SessionAuthentication",
    )
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].extend([
        "djing2.lib.renderer.BrowsableAPIRendererNoForm",
        "rest_framework.renderers.AdminRenderer",
    ])


# Encrypted fields
# https://pypi.org/project/django-encrypted-model-fields/
FIELD_ENCRYPTION_KEY = get_secret("FIELD_ENCRYPTION_KEY")
if not FIELD_ENCRYPTION_KEY:
    raise OSError("FIELD_ENCRYPTION_KEY secret not found")


# DEBUG TOOLBAR
if DEBUG:
    INTERNAL_IPS = ["127.0.0.1"]

# Default dhcp lease time in seconds
DHCP_DEFAULT_LEASE_TIME = 86400

# Default radius session time
RADIUS_SESSION_TIME = os.getenv("RADIUS_SESSION_TIME", 3600)

# Address to websocket transmitter
WS_ADDR = os.getenv("WS_ADDR", "127.0.0.1:3211")

# absolute path to arping command
ARPING_COMMAND = os.getenv("ARPING_COMMAND", "/usr/sbin/arping")
ARPING_ENABLED = os.getenv("ARPING_ENABLED", False)
ARPING_ENABLED = bool(ARPING_ENABLED)

# SITE_ID = 1

if DEBUG:
    TEST_RUNNER = "djing2.lib.fastapi.test.TestRunner"

WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": get_secret("VAPID_PUBLIC_KEY"),
    "VAPID_PRIVATE_KEY": get_secret("VAPID_PRIVATE_KEY"),
    "VAPID_ADMIN_EMAIL": os.getenv("VAPID_ADMIN_EMAIL", DEFAULT_FROM_EMAIL),
}

DEFAULT_FTP_CREDENTIALS = {
    "host": os.getenv("SORM_EXPORT_FTP_HOST"),
    "port": os.getenv("SORM_EXPORT_FTP_PORT", default=21),
    "uname": os.getenv("SORM_EXPORT_FTP_USERNAME"),
    "password": get_secret("SORM_EXPORT_FTP_PASSWORD"),
    "disabled": os.getenv("SORM_EXPORT_FTP_DISABLE", default=False)
}

RADIUSAPP_OPTIONS = {
    'server_host': os.getenv("RADIUS_APP_HOST"),
    'secret': get_secret("RADIUS_SECRET").encode()
}

SORM_REPORTING_EMAILS = []

CONTRACTS_OPTIONS = {
    'DEFAULT_TITLE': os.getenv('CONTRACT_DEFAULT_TITLE', 'Contract default title')
}

# PAYME_CREDENTIALS = base64(login:password)
PAYME_CREDENTIALS = get_secret("PAYME_CREDENTIALS")

CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'pyamqp://user:passw@djing2rabbitmq/')
CELERY_SERIALIZER = 'msgpack'

REDIS_HOST = os.getenv('REDIS_HOST', 'djing2redis')
REDIS_PORT = os.getenv('REDIS_PORT', 6379)
REDIS_AUTH_CASHE_TTL = os.getenv('REDIS_AUTH_CASHE_TTL', 3600)
