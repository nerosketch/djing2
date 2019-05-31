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
SECRET_KEY = '27o%+57bayjug7b8qew%9n6dh$+v_ul%7o89$nm0k!%)fq@6!)'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = local_settings.DEBUG

ALLOWED_HOSTS = local_settings.ALLOWED_HOSTS

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
    'groupapp',
    'profiles',
    'services',
    'gateways',
    'devices',
    'customers',
]

if DEBUG:
    INSTALLED_APPS.insert(0, 'django.contrib.admin')

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

ROOT_URLCONF = 'djing2.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'djing2.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


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

# Maximum file size is 3.90625M
FILE_UPLOAD_MAX_MEMORY_SIZE = 4096000

# time to session live, 1 day
SESSION_COOKIE_AGE = 60 * 60 * 24


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
if DEBUG:
    STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

# Example output: 16 september 2018
DATE_FORMAT = 'd E Y'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_PICTURE = '/static/img/user_ava.gif'
AUTH_USER_MODEL = 'profiles.UserProfile'

# LOGIN_URL = reverse_lazy('acc_app:login')
# LOGIN_REDIRECT_URL = reverse_lazy('acc_app:setup_info')
# LOGOUT_URL = reverse_lazy('acc_app:logout')

TELEPHONE_REGEXP = local_settings.TELEPHONE_REGEXP

# Secret word for auth to api views by hash
API_AUTH_SECRET = local_settings.API_AUTH_SECRET

# Company name
COMPANY_NAME = local_settings.COMPANY_NAME


# Email config
EMAIL_HOST_USER = local_settings.EMAIL_HOST_USER
EMAIL_HOST = local_settings.EMAIL_HOST
EMAIL_PORT = local_settings.EMAIL_PORT
EMAIL_HOST_PASSWORD = local_settings.EMAIL_HOST_PASSWORD
EMAIL_USE_TLS = getattr(local_settings, 'EMAIL_USE_TLS', True)

SERVER_EMAIL = getattr(local_settings, 'SERVER_EMAIL', EMAIL_HOST_USER)


# REDIS related settings
REDIS_HOST = 'localhost'
REDIS_PORT = '6379'
BROKER_URL = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
CELERY_RESULT_BACKEND = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_METADATA_CLASS': 'rest_framework.metadata.SimpleMetadata',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',)
}

if DEBUG:
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ALLOW_CREDENTIALS = True
    CORS_ORIGIN_WHITELIST = (
        'http://localhost:8080',
    )
    CORS_ORIGIN_REGEX_WHITELIST = (
        'http://localhost:8080',
    )


# Encrypted fields
# https://pypi.org/project/django-encrypted-model-fields/
FIELD_ENCRYPTION_KEY = getattr(
    local_settings,
    'FIELD_ENCRYPTION_KEY',
    'vZpDlDPQyU6Ha7NyUGj9uYMuPigejtEPMOZfkYXIQRw='
)
