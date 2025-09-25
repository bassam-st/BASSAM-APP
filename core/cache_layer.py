# core/cache_layer.py
from __future__ import annotations
import time
from typing import Any, Optional

try:
    from diskcache import Cache  # اختياري
    _dc = Cache("./cache")
except Exception:
    _dc = None

class CacheLayer:
    def __init__(self, default_ttl: int = 60 * 60):
        self.default_ttl = default_ttl
        self._mem = {}  # استخدام ذاكرة داخلية عند عدم توفر diskcache

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl or self.default_ttl
        exp = time.time() + ttl
        if _dc:
            _dc.set(key, value, expire=ttl)
        else:
            self._mem[key] = (value, exp)

    def get(self, key: str, default: Any = None) -> Any:
        if _dc:
            val = _dc.get(key, default)
            return val
        item = self._mem.get(key)
        if not item:
            return default
        val, exp = item
        if exp and time.time() > exp:
            self._mem.pop(key, None)
            return default
        return val

    def delete(self, key: str) -> None:
        if _dc:
            _dc.delete(key)
        self._mem.pop(key, None)

cache = CacheLayer()
