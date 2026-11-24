"""Lab 4: bounded GET-only load checks. Does not run as part of pytest."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import ssl
import sys
import time
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests' / 'hosting'))
from hosting_support import Site


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True, help='HTTPS origin of your deployment')
    parser.add_argument('--concurrency', type=int, choices=(10, 50), required=True)
    parser.add_argument('--p95-ms', type=float, default=500, help='Lab target; report failure if exceeded')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        parser.error('--url must be an HTTPS origin without credentials')
    url = args.url.rstrip('/')
    warmup = Site(url, timeout=60).request('/')
    if warmup.status != 200:
        parser.error(f'Warm-up returned HTTP {warmup.status}; load run cancelled')

    # Prepare clients before measuring: certificate store loading and Python
    # object creation are not time spent waiting for the hosting server.
    tls_context = ssl.create_default_context()
    clients = [Site(url, timeout=10, tls_context=tls_context) for _ in range(100)]

    def sample(client):
        start = time.perf_counter()
        try:
            response = client.request('/')
            return time.perf_counter() - start, response.status
        except (AssertionError, OSError):
            return time.perf_counter() - start, 'connection_error'

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(sample, clients))
    duration = time.perf_counter() - start
    times = sorted(value * 1000 for value, _ in results)
    errors = sum(status != 200 for _, status in results)
    report = dict(timestamp=datetime.now(timezone.utc).isoformat(), url=url,
                  requests=100, concurrency=args.concurrency, successes=100-errors, errors=errors,
                  rps=round(100 / duration, 2), mean_ms=round(statistics.mean(times), 2),
                  p95_ms=round(times[math.ceil(.95 * len(times)) - 1], 2),
                  warmup_seconds=round(warmup.elapsed, 3), duration_seconds=round(duration, 2),
                  status_counts=dict(Counter(str(status) for _, status in results)),
                  p95_target_ms=args.p95_ms)
    report['passed'] = errors == 0 and report['p95_ms'] <= args.p95_ms
    output = args.output or Path(f'artifacts/hosting/load-c{args.concurrency}.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
