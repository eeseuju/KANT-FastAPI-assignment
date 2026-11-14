import threading
import time
from typing import Any
from app.core.config import settings


# 일정 시간(초)이 지나면 사라지는 간단한 메모리 캐시
class TTLCache:

    def __init__(self, ttl_seconds: float, max_entries: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries  # 무한히 늘어나지 않도록 개수를 제한한다.
        self._data: dict[Any, tuple[float, Any]] = {}
        self._lock = threading.Lock()  # 여러 요청이 동시에 건드려도 안전하게 락


    # 있으면 값을, 없거나 만료됐으면 None을 돌려준다.
    def get(self, key: Any) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= time.monotonic():
                del self._data[key]
                return None
            return value


    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            if key not in self._data and len(self._data) >= self.max_entries:
                self._evict()
            self._data[key] = (time.monotonic() + self.ttl_seconds, value)


    # 전부 비운다. 글이 바뀔 때 부른다.
    def clear(self) -> None:
        with self._lock:
            self._data.clear()


    # (락을 잡은 상태에서 호출) 만료된 것을 먼저 지우고 가장 오래된 것을 지운다.
    def _evict(self) -> None:
        now = time.monotonic()
        for key in [k for k, (expires_at, _) in self._data.items() if expires_at <= now]:
            del self._data[key]
        if len(self._data) >= self.max_entries:
            self._data.pop(next(iter(self._data)))


# 글 목록·상세 조회 결과를 담는 캐시
post_cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds)