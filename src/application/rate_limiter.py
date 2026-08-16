import time
from collections import deque
from collections.abc import Callable

from application.errors import DownloadCancelled


class RequestRateLimiter:
    def __init__(self, limit: int = 100, window_seconds: float = 300):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: deque[float] = deque()

    @property
    def count(self) -> int:
        self._discard_expired(time.monotonic())
        return len(self._requests)

    @property
    def retry_after(self) -> float:
        now = time.monotonic()
        self._discard_expired(now)
        if not self._requests:
            return 0
        return max(0, self.window_seconds - (now - self._requests[0]))

    def try_acquire(self) -> bool:
        now = time.monotonic()
        self._discard_expired(now)
        if len(self._requests) >= self.limit:
            return False
        self._requests.append(now)
        return True

    def acquire(
        self,
        is_cancelled: Callable[[], bool],
        waiting: Callable[[float], None] = lambda _seconds: None,
    ) -> None:
        waiting_reported = False
        while True:
            if is_cancelled():
                raise DownloadCancelled
            now = time.monotonic()
            self._discard_expired(now)
            if len(self._requests) < self.limit:
                self._requests.append(now)
                return

            wait_seconds = self.window_seconds - (now - self._requests[0])
            if not waiting_reported:
                waiting(max(0, wait_seconds))
                waiting_reported = True
            time.sleep(min(0.1, max(0, wait_seconds)))

    def _discard_expired(self, now: float) -> None:
        threshold = now - self.window_seconds
        while self._requests and self._requests[0] <= threshold:
            self._requests.popleft()
