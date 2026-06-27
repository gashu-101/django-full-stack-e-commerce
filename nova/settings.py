import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Force UTF-8 on Windows stdio so the console email backend can render
# unicode characters like → without choking on cp1252.
if sys.platform == 'win32':
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    v = os.environ.get(key)
    if v is None:
        return default
    return v.strip().lower() in ('1', 'true', 'yes', 'y', 'on')


SECRET_KEY = env('DJANGO_SECRET_KEY', 'django-insecure-hx6a+s@*#8n1=*j5#i$09!@53u^qxj$aj2vxqz#4e60^)w22ej')
DEBUG = env_bool('DJANGO_DEBUG', True)
ALLOWED_HOSTS = [h.strip() for h in env('DJANGO_ALLOWED_HOSTS', '*').split(',') if h.strip()]

# Site URL used to build absolute callback / webhook URLs
SITE_URL = env('SITE_URL', 'http://127.0.0.1:8000').rstrip('/')

# Allow common dev hostnames as trusted origins for CSRF (used by payment callbacks)
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in env(
        'CSRF_TRUSTED_ORIGINS',
        'http://127.0.0.1:8000,http://localhost:8000,' + SITE_URL
    ).split(',') if o.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'shop',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nova.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'shop.context_processors.cart_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'nova.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
CART_SESSION_ID = 'cart'

# ============================================================================
# Email / SMTP
# ----------------------------------------------------------------------------
# In dev with no SMTP creds we fall back to the console backend so order emails
# print to the terminal — handy for local testing.
# ============================================================================
EMAIL_HOST = env('EMAIL_HOST', '')
EMAIL_PORT = int(env('EMAIL_PORT', '587'))
EMAIL_HOST_USER = env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
EMAIL_TIMEOUT = int(env('EMAIL_TIMEOUT', '20'))

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', 'Nova Studio <hello@nova.local>')
ADMIN_EMAIL = env('ADMIN_EMAIL', EMAIL_HOST_USER or 'admin@nova.local')

if EMAIL_HOST and EMAIL_HOST_USER:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ============================================================================
# Payments — Chapa (Ethiopia) https://developer.chapa.co/
# ============================================================================
CHAPA_SECRET_KEY = env('CHAPA_SECRET_KEY', '')
CHAPA_PUBLIC_KEY = env('CHAPA_PUBLIC_KEY', '')
CHAPA_BASE_URL = env('CHAPA_BASE_URL', 'https://api.chapa.co/v1')
CHAPA_CURRENCY = env('CHAPA_CURRENCY', 'ETB')          # ETB / USD
# Optional FX: ETB amount = USD price * CHAPA_FX_RATE. Defaults to 1.0 if currency is USD.
CHAPA_FX_RATE = float(env('CHAPA_FX_RATE', '135.0'))   # USD→ETB display rate
CHAPA_WEBHOOK_SECRET = env('CHAPA_WEBHOOK_SECRET', '') # configured in Chapa dashboard

# ============================================================================
# Payments — Crypto via NOWPayments https://documenter.getpostman.com/view/7907941
# ============================================================================
NOWPAYMENTS_API_KEY = env('NOWPAYMENTS_API_KEY', '')
NOWPAYMENTS_IPN_SECRET = env('NOWPAYMENTS_IPN_SECRET', '')
NOWPAYMENTS_BASE_URL = env('NOWPAYMENTS_BASE_URL', 'https://api.nowpayments.io/v1')
NOWPAYMENTS_PRICE_CURRENCY = env('NOWPAYMENTS_PRICE_CURRENCY', 'usd')
