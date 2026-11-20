import importlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured

from zvukfest.environment import load_environment, required_env


class EnvironmentTests(unittest.TestCase):
    def test_missing_or_empty_secret_fails_with_variable_name(self):
        for value in (None, '', '   '):
            env = {} if value is None else {'DJANGO_SECRET_KEY': value}
            with self.subTest(value=value), patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(ImproperlyConfigured, 'DJANGO_SECRET_KEY'):
                    required_env('DJANGO_SECRET_KEY')

    def test_env_file_preserves_dollar_signs_and_existing_environment(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text("DJANGO_SECRET_KEY='fixture-${HOME}-$c'\nDB_PASSWORD=file-value\n", encoding='utf-8')
            with patch.dict(os.environ, {'DB_PASSWORD': 'runtime-value'}, clear=True):
                load_environment(path)
                self.assertEqual(required_env('DJANGO_SECRET_KEY'), 'fixture-${HOME}-$c')
                self.assertEqual(required_env('DB_PASSWORD'), 'runtime-value')

    def test_dotenv_can_be_disabled(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('DJANGO_SECRET_KEY=fixture-value\n', encoding='utf-8')
            with patch.dict(os.environ, {'DJANGO_LOAD_DOTENV': 'false'}, clear=True):
                load_environment(path)
                self.assertNotIn('DJANGO_SECRET_KEY', os.environ)

    def test_database_accepts_local_and_docker_variables(self):
        with patch.dict(os.environ, {'POSTGRES_PASSWORD': 'local-fixture'}, clear=True):
            from zvukfest import db_config
            config = importlib.reload(db_config).DATABASE
            self.assertEqual(config['PASSWORD'], 'local-fixture')
            self.assertEqual(config['HOST'], 'localhost')
        env = {'POSTGRES_PASSWORD': 'local-fixture', 'DB_PASSWORD': 'docker-fixture',
               'DB_HOST': 'db', 'DB_NAME': 'test_catalogue', 'DB_USER': 'test_user', 'DB_PORT': '5432'}
        with patch.dict(os.environ, env, clear=True):
            config = importlib.reload(db_config).DATABASE
            self.assertEqual(config['PASSWORD'], 'docker-fixture')
            self.assertEqual(config['HOST'], 'db')
            self.assertEqual(config['NAME'], 'test_catalogue')
            self.assertEqual(config['USER'], 'test_user')

    def test_database_does_not_fall_back_to_a_hardcoded_password(self):
        with patch.dict(os.environ, {'POSTGRES_PASSWORD': 'local-fixture'}, clear=True):
            from zvukfest import db_config
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ImproperlyConfigured, 'POSTGRES_PASSWORD'):
                importlib.reload(db_config)
        with patch.dict(os.environ, {'DB_PASSWORD': '', 'POSTGRES_PASSWORD': 'local-fixture'}, clear=True):
            with self.assertRaisesRegex(ImproperlyConfigured, 'DB_PASSWORD'):
                importlib.reload(db_config)


if __name__ == '__main__':
    unittest.main()
