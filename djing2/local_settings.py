"""
Custom settings for each system
"""

DEBUG = True

ALLOWED_HOSTS = '*',

DEFAULT_FROM_EMAIL = 'admin@yoursite.com'

PAGINATION_ITEMS_PER_PAGE = 20

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'apikey'


# service id for AllPay payment system
PAY_SERV_ID = '<service id>'
PAY_SECRET = '<secret>'

# path to asterisk dial records
DIALING_MEDIA = 'path/to/asterisk_records'

DEFAULT_SNMP_PASSWORD = 'public'

TELEGRAM_BOT_TOKEN = 'bot token'

# Telephone or empty
TELEPHONE_REGEXP = r'^(\+[7893]\d{10,11})?$'

ASTERISK_MANAGER_AUTH = {
    'username': 'admin',
    'password': 'password',
    'host': '127.0.0.1'
}

# Secret word for auth to api views by hash
API_AUTH_SECRET = 'your api secret'

# Allowed subnet for api
# Fox example: API_AUTH_SUBNET = ('127.0.0.0/8', '10.0.0.0/8', '192.168.0.0/16')
API_AUTH_SUBNET = '127.0.0.0/8'

# Company name
COMPANY_NAME = 'Your company name'

# Email config
EMAIL_HOST_USER = 'YOUR-EMAIL@mailserver.com'
EMAIL_HOST = 'smtp.mailserver.com'
EMAIL_PORT = 587
EMAIL_HOST_PASSWORD = 'password'
EMAIL_USE_TLS = True

# public url for Viber Bot
VIBER_BOT_PUBLIC_URL = 'https://localhost:8000'
