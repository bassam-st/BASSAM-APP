# src/memory/memory.py — ذاكرة بسيطة على diskcache

from diskcache import Cache
cache = Cache(".cache")

def _key(user_id: str, field: str) -> str:
    return f"user:{user_id}:{field}"

def remember(user_id: str, field: str, value):
    cache.set(_key(user_id, field), value, expire=None)

def recall(user_id: str, field: str, default=None):
    return cache.get(_key(user_id, field), default)
