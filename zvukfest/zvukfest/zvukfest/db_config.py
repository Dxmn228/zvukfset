import os

from .environment import required_env


DATABASE = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': os.environ.get('DB_NAME', os.environ.get('POSTGRES_DB', 'zvukfest_db')),
    'USER': os.environ.get('DB_USER', os.environ.get('POSTGRES_USER', 'zvuk_user')),
    'PASSWORD': required_env('DB_PASSWORD') if 'DB_PASSWORD' in os.environ else required_env('POSTGRES_PASSWORD'),
    'HOST': os.environ.get('DB_HOST', 'localhost'),
    'PORT': os.environ.get('DB_PORT', '5432'),
}
