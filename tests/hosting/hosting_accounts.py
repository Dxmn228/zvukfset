"""Public-API account factory. Stores identifiers for cleanup, never passwords."""
from dataclasses import dataclass, field
import json
from pathlib import Path
import secrets
from uuid import uuid4

from hosting_support import Site


@dataclass
class Account:
    site: Site = field(repr=False)
    email: str
    password: str = field(repr=False)
    name: str = 'Hosting test'

    def login(self, site=None, remember=True):
        target = site if site is not None else self.site
        target.request('/tickets.html')
        return target.request('/api/login', 'POST', {
            'email': self.email, 'password': self.password, 'remember': remember,
        }, csrf=True)


def new_account(site_url):
    return Account(Site(site_url), f'hosting-test-{uuid4().hex}@example.invalid', secrets.token_urlsafe(24))


def registration(account):
    return dict(username=account.name, email=account.email, password=account.password,
                password_confirm=account.password, terms=True, privacy=True)


def record_account(account, nodeid):
    target = Path('artifacts/hosting/accounts.jsonl')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'email': account.email, 'test': nodeid}) + '\n')
