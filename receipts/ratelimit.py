import time

from django.core.cache import cache


def is_allowed(key: str, limit: int, window_seconds: int = 60) -> bool:
    if limit <= 0:
        return True
    window = int(time.time()) // window_seconds
    cache_key = f'ratelimit:{key}:{window}'
    if cache.add(cache_key, 1, timeout=window_seconds):
        return True
    try:
        hits = cache.incr(cache_key)
    except ValueError:
        cache.add(cache_key, 1, timeout=window_seconds)
        return True
    return hits <= limit
