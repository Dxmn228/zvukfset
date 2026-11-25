"""Run published-site tests without Django, Docker or a local database."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=os.environ.get('HOSTING_BASE_URL', 'https://zvukfest.de3.netrun.io'))
    parser.add_argument('--suite', choices=('all', 'api', 'ui', 'checks'), default='all')
    parser.add_argument('--no-writes', action='store_true', help='Exclude account/cart/order write scenarios')
    args, extra = parser.parse_known_args()
    if extra and extra[0] == '--':
        extra = extra[1:]
    expression = {'all': '', 'api': 'functional and not browser', 'ui': 'browser',
                  'checks': 'not functional and not browser and not writes'}[args.suite]
    if args.no_writes:
        expression = f'({expression}) and not writes' if expression else 'not writes'
    command = [sys.executable, '-m', 'pytest', '-c', str(ROOT / 'pytest.hosting.ini'),
               str(ROOT / 'tests' / 'hosting'), '--hosting-url=' + args.url, '-v', '-rs']
    if '--collect-only' not in extra and '--co' not in extra:
        command.append('--junitxml=' + str(ROOT / 'artifacts' / 'hosting' / f'{args.suite}-results.xml'))
    if not args.no_writes:
        command.append('--hosting-writes')
    if args.suite in ('all', 'ui'):
        command.append('--hosting-browser')
        if not any(item == '--browser' or item.startswith('--browser=') for item in extra):
            command.extend(['--browser', 'chromium', '--browser', 'firefox'])
    if expression:
        command.extend(['-m', expression])
    return subprocess.run([*command, *extra], cwd=ROOT).returncode


if __name__ == '__main__':
    raise SystemExit(main())
