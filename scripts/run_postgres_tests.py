"""Run backend tests against disposable PostgreSQL, including a restart test.

Only the uniquely named test Compose project and its volume are removed.
The application's compose.yaml, .env, containers and database are never used.
"""
import os
import socket
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    project = 'zvukfest-test-' + uuid4().hex
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = str(listener.getsockname()[1])
    # An explicit mapping keeps the host port unchanged across docker restart.
    compose_env = {**os.environ, 'TEST_POSTGRES_PORT': port}
    command = ['docker', 'compose', '--env-file', os.devnull, '-f', str(ROOT / 'compose.test.yaml'), '-p', project]
    def run(*args, capture=False):
        return subprocess.run([*command, *args], cwd=ROOT, check=True, text=True, encoding='utf-8',
                              capture_output=capture, env=compose_env)
    try:
        run('up', '-d', '--wait', '--wait-timeout', '60', '--pull', 'never')
        container = run('ps', '-q', 'db', capture=True).stdout.strip()
        port = run('port', 'db', '5432', capture=True).stdout.strip().rsplit(':', 1)[1]
        env = {**os.environ, 'TEST_POSTGRES_PORT': port, 'TEST_POSTGRES_CONTAINER': container,
               'TEST_POSTGRES_PROJECT': project, 'PYTHONIOENCODING': 'utf-8'}
        result = subprocess.run([sys.executable, '-m', 'pytest', '-c', 'pytest.ini',
                                 '--ds=zvukfest.settings_test_postgres', '-p', 'no:cacheprovider', '-q',
                                 '--tb=short', '-o', 'faulthandler_timeout=45', *sys.argv[1:]], cwd=ROOT, env=env)
        return result.returncode
    finally:
        run('down', '--volumes', '--remove-orphans')


if __name__ == '__main__':
    raise SystemExit(main())
