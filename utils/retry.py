import functools
import random

import requests
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from utils.logger import get_logger

_log = get_logger("retry")

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_NON_RETRYABLE_STATUS_CODES = {400, 403, 404}


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, requests.exceptions.ConnectionError):
        return True
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        response = exc.response
        if response is not None and response.status_code in _NON_RETRYABLE_STATUS_CODES:
            return False
        if response is not None and response.status_code in _RETRYABLE_STATUS_CODES:
            return True
    return False


def retry_with_backoff(max_attempts: int = 4, base_wait: float = 2.0, multiplier: float = 2.0):
    """Decorator that retries on transient network/HTTP errors with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0

            @retry(
                retry=retry_if_exception(_is_retryable),
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=multiplier, min=base_wait, max=60),
                reraise=True,
            )
            def _inner():
                nonlocal attempt
                attempt += 1
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    jitter = random.uniform(-0.5, 0.5)
                    _log.warning(
                        "retry_attempt",
                        attempt=attempt,
                        exc_type=type(exc).__name__,
                        jitter=round(jitter, 3),
                    )
                    raise

            return _inner()

        return wrapper
    return decorator
