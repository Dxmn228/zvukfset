"""Offline checks of the test runner's bounded startup wait, not of the website."""
from types import SimpleNamespace

import pytest

from hosting_support import wait_until_ready


def run_wait(statuses, budget=6):
    state = {'now': 0, 'attempts': 0}

    def factory(base, timeout):
        assert 0 < timeout <= budget

        def request(path):
            index = min(state['attempts'], len(statuses) - 1)
            state['attempts'] += 1
            return SimpleNamespace(status=statuses[index])

        return SimpleNamespace(request=request)

    def sleep(seconds):
        state['now'] += seconds

    result = wait_until_ready('https://example.invalid', budget=budget, interval=2,
                             clock=lambda: state['now'], sleep=sleep, site_factory=factory)
    return result


def test_ready_site_does_not_wait():
    assert run_wait([200]) == {'attempts': 1, 'seconds': 0}


def test_starting_site_retries_then_reports_startup_time():
    assert run_wait([503, 502, 200]) == {'attempts': 3, 'seconds': 4}


def test_persistent_unavailability_fails_within_budget():
    with pytest.raises(AssertionError, match='within 6s; last HTTP 503, attempts: 3'):
        run_wait([503])


@pytest.mark.parametrize('status', [400, 403, 404, 500])
def test_application_errors_are_not_hidden_by_retry(status):
    with pytest.raises(AssertionError, match=f'HTTP {status}; startup wait stopped'):
        run_wait([status, 200])
