"""Isolated browser-test configuration. Never use this module for deployment."""

import os

# Avoid reading real credentials even when a local .env is present.
os.environ['DJANGO_LOAD_DOTENV'] = 'false'
os.environ['DJANGO_SECRET_KEY'] = 'browser-test-key-not-for-deployment'
os.environ['DB_PASSWORD'] = 'unused-browser-test-placeholder'
# Playwright's sync API owns an event loop in the test thread. This suite runs
# sequentially; permit synchronous test fixtures/ORM only in this test process.
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

from .settings import *  # noqa: F403, E402

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
DEBUG = True
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
