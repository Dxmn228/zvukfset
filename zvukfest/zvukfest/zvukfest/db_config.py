import os

# Параметры подключения к PostgreSQL
DATABASE = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'zvukfest_db',
    'USER': 'zvuk_user',
    'PASSWORD': 'Mortalkombat1',
    'HOST': 'localhost',
    'PORT': '5432',
}

# В Docker хостом служит имя сервиса db; локальные настройки остаются запасными.
for key in ('NAME', 'USER', 'PASSWORD', 'HOST', 'PORT'):
    DATABASE[key] = os.environ.get(f'DB_{key}', DATABASE[key])
