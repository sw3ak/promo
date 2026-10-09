import decimal
import logging
import pathlib
import sys

import dotenv

from config import env

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

dotenv.load_dotenv(BASE_DIR / '.env', override=False)

DEBUG = env.get_bool('DJANGO_DEBUG', default=False)

SECRET_KEY = env.get_str(
    'DJANGO_SECRET_KEY',
    default='insecure-local-development-key' if DEBUG else None,
)

ALLOWED_HOSTS = env.get_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env.get_list('DJANGO_CSRF_TRUSTED_ORIGINS', '')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'core',
    'accounts',
    'receipts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

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
                'core.context_processors.promo',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env.get_str('POSTGRES_DB', 'promo'),
        'USER': env.get_str('POSTGRES_USER', 'promo'),
        'PASSWORD': env.get_str('POSTGRES_PASSWORD', ''),
        'HOST': env.get_str('POSTGRES_HOST', 'localhost'),
        'PORT': env.get_int('POSTGRES_PORT', 5432),
        'CONN_MAX_AGE': env.get_int('POSTGRES_CONN_MAX_AGE', 60),
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'options': '-c statement_timeout={}'.format(
                env.get_int('POSTGRES_STATEMENT_TIMEOUT_MS', 15000)
            ),
        },
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REDIS_URL = env.get_str('REDIS_URL', '')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'KEY_PREFIX': 'promo',
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.'
        'UserAttributeSimilarityValidator'
    },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.'
        'NumericPasswordValidator'
    },
]

TESTING = 'test' in sys.argv[1:2]
if TESTING:
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    logging.disable(logging.CRITICAL)

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'receipts:cabinet'
LOGOUT_REDIRECT_URL = 'login'


LANGUAGE_CODE = 'ru'
LANGUAGES = [('ru', 'Русский')]
TIME_ZONE = env.get_str('TIME_ZONE', 'Europe/Moscow')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_ROOT = pathlib.Path(env.get_str('MEDIA_ROOT', str(BASE_DIR / 'media')))

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if not DEBUG
            else 'django.contrib.staticfiles.storage.StaticFilesStorage'
        ),
    },
}

FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

SECURE_COOKIES = env.get_bool('DJANGO_SECURE_COOKIES', default=False)
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
if env.get_bool('DJANGO_BEHIND_TLS_PROXY', default=False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'plain': {
            'format': '%(asctime)s %(levelname)s %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django.db.backends': {'level': 'WARNING'},
    },
}


PROMO_START_DATE = env.get_date('PROMO_START_DATE', '2026-10-01')
PROMO_END_DATE = env.get_date('PROMO_END_DATE', '2026-12-31')
PROMO_MIN_AMOUNT = decimal.Decimal(env.get_str('PROMO_MIN_AMOUNT', '1000'))
PROMO_SITE_URL = env.get_str('PROMO_SITE_URL', '/')

RECEIPT_MAX_RESUBMISSIONS = env.get_int('RECEIPT_MAX_RESUBMISSIONS', 2)
RECEIPT_PHOTO_MAX_BYTES = env.get_int('RECEIPT_PHOTO_MAX_MB', 5) * 1024 * 1024
RECEIPT_SUBMIT_RATE_LIMIT = env.get_int('RECEIPT_SUBMIT_RATE_LIMIT', 10)
RECEIPT_STATUS_POLL_SECONDS = env.get_int('RECEIPT_STATUS_POLL_SECONDS', 15)
