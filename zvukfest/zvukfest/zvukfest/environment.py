"""Load local configuration without embedding credentials in source files."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR.parent.parent / '.env'


def load_environment(path=ENV_FILE):
    # Docker supplies variables directly. Local commands read the root .env.
    if os.environ.get('DJANGO_LOAD_DOTENV', 'true').lower() in ('true', '1', 'yes'):
        load_dotenv(path, override=False, interpolate=False, encoding='utf-8-sig')


def required_env(name):
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise ImproperlyConfigured(f'Set the required environment variable {name}.')
    return value


load_environment()
