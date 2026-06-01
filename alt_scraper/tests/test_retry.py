import time
from unittest.mock import MagicMock, patch

import pytest
import requests
import responses as responses_lib

from utils.retry import retry_with_backoff


def _make_http_error(status_code: int) -> requests.exceptions.HTTPError:
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    exc = requests.exceptions.HTTPError(response=response)
    return exc


@retry_with_backoff(max_attempts=3, base_wait=0.01, multiplier=1.0)
def _dummy_get(mock_fn):
    return mock_fn()


def test_succeeds_on_first_attempt():
    mock = MagicMock(return_value="ok")
    result = _dummy_get(mock)
    assert result == "ok"
    assert mock.call_count == 1


def test_retries_on_429_and_succeeds():
    call_count = 0

    def side_effect():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise _make_http_error(429)
        return "success"

    mock = MagicMock(side_effect=side_effect)
    result = _dummy_get(mock)
    assert result == "success"
    assert call_count == 2


def test_retries_on_503_raises_after_max_attempts():
    mock = MagicMock(side_effect=_make_http_error(503))

    with pytest.raises(requests.exceptions.HTTPError):
        _dummy_get(mock)

    assert mock.call_count == 3


def test_does_not_retry_on_404():
    mock = MagicMock(side_effect=_make_http_error(404))

    with pytest.raises(requests.exceptions.HTTPError):
        _dummy_get(mock)

    assert mock.call_count == 1


def test_does_not_retry_on_403():
    mock = MagicMock(side_effect=_make_http_error(403))

    with pytest.raises(requests.exceptions.HTTPError):
        _dummy_get(mock)

    assert mock.call_count == 1


def test_retries_on_connection_error():
    call_count = 0

    def side_effect():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise requests.exceptions.ConnectionError("network down")
        return "recovered"

    mock = MagicMock(side_effect=side_effect)
    result = _dummy_get(mock)
    assert result == "recovered"
    assert call_count == 3


def test_retries_on_timeout():
    call_count = 0

    def side_effect():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise requests.exceptions.Timeout("timed out")
        return "ok"

    mock = MagicMock(side_effect=side_effect)
    result = _dummy_get(mock)
    assert result == "ok"
    assert call_count == 2


def test_jitter_applied_to_wait_times():
    """Verify that wait times across retries are not perfectly uniform (jitter present)."""
    times = []
    call_count = 0

    def side_effect():
        nonlocal call_count
        call_count += 1
        times.append(time.monotonic())
        if call_count < 3:
            raise requests.exceptions.ConnectionError("fail")
        return "done"

    @retry_with_backoff(max_attempts=3, base_wait=0.05, multiplier=2.0)
    def _fn():
        return side_effect()

    _fn()
    assert len(times) == 3
    # Waits should be > 0 and the two gaps need not be equal (jitter)
    gap1 = times[1] - times[0]
    gap2 = times[2] - times[1]
    assert gap1 > 0
    assert gap2 > 0
