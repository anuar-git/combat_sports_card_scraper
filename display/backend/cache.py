from functools import wraps
from typing import Callable

from cachetools import TTLCache

_cache: TTLCache = TTLCache(maxsize=256, ttl=900)  # 15-minute TTL


def cached(key_fn: Callable) -> Callable:
    """Cache function results by a key derived from call arguments."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = key_fn(*args, **kwargs)
            if key in _cache:
                return _cache[key]
            result = fn(*args, **kwargs)
            _cache[key] = result
            return result
        return wrapper
    return decorator


def clear_cache() -> int:
    count = len(_cache)
    _cache.clear()
    return count
