"""HTTP helpers independent of Django, local settings and the production database."""
import json
import ssl
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPCookieProcessor, HTTPRedirectHandler, HTTPSHandler

PAGES = ('/', '/index.html', '/program.html', '/artists.html', '/tickets.html',
         '/cart.html', '/privacy.html', '/terms.html')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class Response:
    status: int
    headers: object
    body: bytes
    elapsed: float
    url: str

    @property
    def text(self):
        return self.body.decode('utf-8', errors='replace')

    def json(self):
        assert 'application/json' in self.headers.get('Content-Type', ''), 'Expected JSON, received another content type'
        try:
            return json.loads(self.body)
        except ValueError:
            raise AssertionError('Invalid JSON response') from None


class Site:
    def __init__(self, base, timeout=20, tls_context=None):
        self.base = base.rstrip('/')
        self.timeout = timeout
        self.cookies = CookieJar()
        self.opener = build_opener(NoRedirect(), HTTPCookieProcessor(self.cookies),
                                   HTTPSHandler(context=tls_context if tls_context is not None else ssl.create_default_context()))

    def cookie(self, name):
        return next((c for c in self.cookies if c.name == name), None)

    def request(self, path, method='GET', data=None, csrf=False, headers=None, follow=True):
        url = urljoin(self.base + '/', path)
        supplied = {'User-Agent': 'Zvukfest-Hosting-Tests/1.0', **(headers or {})}
        if csrf:
            token = self.cookie('csrftoken')
            assert token, 'CSRF cookie was not issued'
            supplied.update({'X-CSRFToken': token.value, 'Origin': self.base, 'Referer': self.base + '/'})
            supplied.update(headers or {})
        payload = None if data is None else json.dumps(data).encode()
        if payload is not None:
            supplied['Content-Type'] = 'application/json'
        start = time.perf_counter()
        for _ in range(6):
            parsed = urlsplit(url)
            assert parsed.netloc == urlsplit(self.base).netloc, 'Unexpected cross-domain redirect'
            assert parsed.scheme == 'https' or (method == 'GET' and not follow), 'HTTPS downgrade rejected'
            try:
                response = self.opener.open(Request(url, data=payload, headers=supplied, method=method), timeout=self.timeout)
            except HTTPError as error:
                response = error
            except (URLError, TimeoutError, OSError) as error:
                raise AssertionError(f'Connection failed for {parsed.path}: {type(error).__name__}') from None
            with response:
                result = Response(response.code, response.headers, response.read(4 * 1024 * 1024),
                                  time.perf_counter() - start, url)
            if not follow or result.status not in (301, 302, 303, 307, 308):
                return result
            assert method == 'GET', 'Unexpected redirect from a write endpoint'
            url = urljoin(url, result.headers.get('Location', ''))
        raise AssertionError('Redirect loop')


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.assets = []
        self.ids = set()
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag in ('script', 'img') and attrs.get('src'):
            self.assets.append(attrs['src'])
        if tag == 'link' and attrs.get('rel') == 'stylesheet' and attrs.get('href'):
            self.assets.append(attrs['href'])
