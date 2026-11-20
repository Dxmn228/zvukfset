import os
from pathlib import Path

from .db_config import DATABASE

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / 'frontend'      # папка с вашим сайтом

SECRET_KEY = '-006#qmcq!=srksyg*#)5!gp*xy$c*fjatboo3rfbf3hhhr%)'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', SECRET_KEY)
DEBUG = os.environ.get('DJANGO_DEBUG', 'true').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',                               # наше приложение
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

ROOT_URLCONF = 'zvukfest.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'zvukfest.wsgi.application'

DATABASES = {'default': DATABASE}

AUTH_USER_MODEL = 'main.User'             # своя модель пользователя (таблица users)

# Пароли хэшируются bcrypt
PASSWORD_HASHERS = ['django.contrib.auth.hashers.BCryptSHA256PasswordHasher']

# Сессии хранятся в БД (таблица django_session)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14    # 14 дней

LANGUAGE_CODE = 'ru'                      # ошибки валидации будут на русском
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
