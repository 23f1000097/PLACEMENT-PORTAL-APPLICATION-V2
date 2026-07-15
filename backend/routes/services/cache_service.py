import redis
from flask import current_app, g, request

from extensions import cache

# Cache-key prefixes for the listing endpoints we cache. Passed to clear_cache()
# so invalidation only drops the affected keys instead of wiping the whole cache.
STUDENT_DRIVES_PREFIX = "/api/student/drives"
ADMIN_COMPANIES_PREFIX = "/api/admin/companies"
ADMIN_STUDENTS_PREFIX = "/api/admin/students"
ADMIN_JOBS_PREFIX = "/api/admin/jobs"


def make_cache_key():
    user_id = getattr(getattr(g, "current_user", None), "id", "anon")
    query_string = request.query_string.decode("utf-8")
    return f"view:{request.path}:{user_id}:{query_string}"


def cached(timeout=300):
    return cache.cached(timeout=timeout, key_prefix=make_cache_key)


def clear_cache(*prefixes):
    """Delete only the cache keys under the given path prefixes.

    Falls back to a full cache.clear() if no prefixes are given or the
    backend isn't Redis (e.g. tests running with SimpleCache).
    """
    if not prefixes:
        cache.clear()
        return

    redis_url = current_app.config.get("CACHE_REDIS_URL")
    if not redis_url:
        cache.clear()
        return

    client = redis.from_url(redis_url)
    key_prefix = current_app.config.get("CACHE_KEY_PREFIX", "")
    for prefix in prefixes:
        pattern = f"{key_prefix}view:{prefix}*"
        for key in client.scan_iter(match=pattern):
            client.delete(key)


def delete_cache_key(key):
    cache.delete(key)
