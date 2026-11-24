"""Only for the isolated compose.test.yaml database, never the application DB."""
import os

from .settings_ui import *  # noqa: F403

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'zvukfest_tests',
    'USER': 'test_runner',
    'PASSWORD': 'local-test-only-password',
    'HOST': '127.0.0.1',
    'PORT': int(os.environ['TEST_POSTGRES_PORT']),
    'OPTIONS': {'connect_timeout': 3},
    'TEST': {'NAME': 'test_zvukfest_tests'},
}}
