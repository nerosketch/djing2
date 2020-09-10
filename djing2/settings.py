"""
Django settings for djing2 project.

Generated by 'django-admin startproject' using Django 2.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os

try:
    from . import local_settings
except ImportError:
    raise ImportError("You must create config file local_settings.py from template")

from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# from django.urls import reverse_lazy


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = local_settings.SECRET_KEY

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = getattr(local_settings, 'DEBUG', True)

ALLOWED_HOSTS = getattr(local_settings, 'ALLOWED_HOSTS', '*')

ADMINS = getattr(local_settings, 'ADMINS', ())

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'encrypted_model_fields',
    'django_filters',
    'corsheaders',
    'guardian',
    'django_cleanup.apps.CleanupConfig',
    'groupapp',
    'profiles.apps.ProfilesConfig',
    'services.apps.ServicesConfig',
    'gateways.apps.GatewaysConfig',
    'devices.apps.DevicesConfig',
    'networks',
    'customers.apps.CustomersConfig',
    'messenger',
    'tasks',
    'fin_app',
    'dials',
    'msg_app',
    'traf_stat',
]

if DEBUG:
    INSTALLED_APPS.insert(0, 'django.contrib.admin')
    INSTALLED_APPS.append('debug_toolbar')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'djing2.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # 'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = (
    'djing2.lib.auth_backends.DjingAuthBackend',
    'guardian.backends.ObjectPermissionBackend'
    # 'djing2.lib.auth_backends.LocationAuthBackend',
)

WSGI_APPLICATION = 'djing2.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = getattr(local_settings, 'DATABASES', {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
})
if not DATABASES['default'].get('CONN_MAX_AGE'):
    DATABASES['default']['CONN_MAX_AGE'] = 300


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
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'ru'

LANGUAGES = (
    ('ru', _('Russian')),
    #('en', _('English'))
)

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

LOCALE_PATHS = (
    os.path.join(PROJECT_PATH, '../locale'),
)


TIME_ZONE = 'Europe/Simferopol'

USE_I18N = True

USE_L10N = False

USE_TZ = False

# Maximum file size is 50Mb
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800

DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE

# time to session live, 1 day
SESSION_COOKIE_AGE = 60 * 60 * 24


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
if DEBUG:
    STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

# STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Example output: 16 september 2018
DATE_FORMAT = 'd E Y'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_PICTURE = '/static/img/user_ava.gif'
AUTH_USER_MODEL = 'profiles.BaseAccount'

# LOGIN_URL = reverse_lazy('acc_app:login')
# LOGIN_REDIRECT_URL = reverse_lazy('acc_app:setup_info')
# LOGOUT_URL = reverse_lazy('acc_app:logout')

TELEPHONE_REGEXP = getattr(local_settings, 'TELEPHONE_REGEXP', r'^(\+[7893]\d{10,11})?$')

# Secret word for auth to api views by hash
API_AUTH_SECRET = getattr(local_settings, 'API_AUTH_SECRET', 'secret')

# Allowed subnet for api
API_AUTH_SUBNET = getattr(local_settings, 'API_AUTH_SUBNET', ('127.0.0.0/8', '10.0.0.0/8'))

# Company name
COMPANY_NAME = getattr(local_settings, 'COMPANY_NAME', 'Company Name')

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'djing2.lib.paginator.QueryPageNumberPagination',
    # 'PAGE_SIZE': 180,
    'DEFAULT_METADATA_CLASS': 'rest_framework.metadata.SimpleMetadata',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'djing2.lib.authenticators.CustomTokenAuthentication'
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'djing2.lib.filters.CustomObjectPermissionsFilter',
        'django_filters.rest_framework.DjangoFilterBackend'
    ],
    'DATETIME_FORMAT': '%d %B %H:%M',
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'rest_framework.permissions.IsAdminUser',
        'djing2.permissions.CustomizedDjangoModelPermissions'
    ]
    # 'DEFAULT_RENDERER_CLASSES': (
    #     'rest_framework.renderers.JSONRenderer',
    # )
}

# Guardian options
GUARDIAN_RAISE_403 = True
# GUARDIAN_AUTO_PREFETCH = True

if DEBUG:
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ALLOW_CREDENTIALS = True
    CORS_ORIGIN_WHITELIST = (
        'http://0.0.0.0:8080',
    )
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'].append(
        'rest_framework.authentication.SessionAuthentication'
    )


# Encrypted fields
# https://pypi.org/project/django-encrypted-model-fields/
FIELD_ENCRYPTION_KEY = getattr(
    local_settings,
    'FIELD_ENCRYPTION_KEY',
    'vZpDlDPQyU6Ha7NyUGj9uYMuPigejtEPMOZfkYXIQRw='
)


DIAL_RECORDS_PATH = '/var/spool/asterisk/monitor/'
DIAL_RECORDS_EXTENSION = 'wav'

# DEBUG TOOLBAR
if DEBUG:
    INTERNAL_IPS = ['127.0.0.1']

# Default dhcp lease time in seconds
DHCP_DEFAULT_LEASE_TIME = 86400

# Default radius session time
RADIUS_SESSION_TIME = 3600

# Address to websocket transmitter
WS_ADDR = '127.0.0.1:3211'

# absolute path to arping command
ARPING_COMMAND = getattr(local_settings, 'ARPING_COMMAND', '/usr/sbin/arping')
