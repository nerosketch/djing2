"""
Custom settings for each system
"""
import os

DEBUG = os.environ.get("APP_DEBUG", False)
DEBUG = bool(DEBUG)

ALLOWED_HOST = os.environ.get("ALLOWED_HOST")
ALLOWED_HOSTS = [ALLOWED_HOST] if ALLOWED_HOST else ["*"]

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_EMAIL", "admin@yoursite.com")


def get_secret(fname: str) -> str:
    with open(os.path.join("/run/secrets", fname)) as f:
        return f.read()


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_secret("DJANGO_SECRET_KEY")
if SECRET_KEY is None:
    raise OSError("DJANGO_SECRET_KEY env not found")


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "CONN_MAX_AGE": 300,
        "NAME": os.environ.get("POSTGRES_DB", "djing2"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": get_secret("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": 5432,
    }
}

DEFAULT_SNMP_PASSWORD = os.environ.get("DEFAULT_SNMP_PASSWORD", "public")

# Telephone or empty
TELEPHONE_REGEXP = r"^(\+[7893]\d{10,11})?$"

# Secret word for auth to api views by hash
API_AUTH_SECRET = get_secret("API_AUTH_SECRET")

# Allowed subnet for api
# Fox example: API_AUTH_SUBNET = ('127.0.0.0/8', '10.0.0.0/8', '192.168.0.0/16')
API_AUTH_SUBNET = os.environ.get("API_AUTH_SUBNET", "127.0.0.0/8")

# Company name
COMPANY_NAME = os.environ.get("COMPANY_NAME", "Your company name")

# Email config
# EMAIL_HOST_USER = 'YOUR-EMAIL@mailserver.com'
# EMAIL_HOST = 'smtp.mailserver.com'
# EMAIL_PORT = 587
# EMAIL_HOST_PASSWORD = 'password'
# EMAIL_USE_TLS = True

# public url for Viber Bot
VIBER_BOT_PUBLIC_URL = "https://your_domain.name"

# Encrypted fields
# This is example, change key for your own secret key
FIELD_ENCRYPTION_KEY = get_secret("FIELD_ENCRYPTION_KEY")

# arping command
ARPING_COMMAND = "/usr/sbin/arping"

WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": get_secret("VAPID_PUBLIC_KEY"),
    "VAPID_PRIVATE_KEY": get_secret("VAPID_PRIVATE_KEY"),
    "VAPID_ADMIN_EMAIL": os.environ.get("VAPID_ADMIN_EMAIL", DEFAULT_FROM_EMAIL),
}

RADIUS_FINISH_SESSION_CMD_LIST = ["/usr/bin/echo", "-sx", "127.0.0.1:3799", "disconnect", "passwordexample"]
