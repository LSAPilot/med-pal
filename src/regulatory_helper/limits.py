"""Budget protection, all in memory.

Three small pieces, each testable on its own (they take an injectable clock):
  DailyLimit      global number of API-backed questions per UTC day
  VisitorLimit    questions per visitor within a sliding window
  AnswerCache     identical requests are answered from memory and cost nothing

Nothing here is persisted. A restart of the server resets counters and cache, which is accepted
(the spend limit in the Anthropic Console stays as the last safety net).
Visitors are identified by a salted hash of their address that exists only in memory and is never logged.
"""
from __future__ import annotations

import hashlib
import os
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

Clock = Callable[[], float]


@dataclass
class LimitConfig:
    daily_limit: int = 100  # global API-backed questions per UTC day
    visitor_limit: int = 10  # per visitor within the window
    visitor_window_s: int = 3600
    cache_size: int = 500
    max_question_chars: int = 500

    @classmethod
    def from_env(cls) -> LimitConfig:
        """Every number can be overridden by an environment variable (Space variables), e.g. DAILY_LIMIT=50."""
        d = cls()
        return cls(
            daily_limit=int(os.environ.get("DAILY_LIMIT", d.daily_limit)),
            visitor_limit=int(os.environ.get("VISITOR_LIMIT", d.visitor_limit)),
            visitor_window_s=int(os.environ.get("VISITOR_WINDOW_S", d.visitor_window_s)),
            cache_size=int(os.environ.get("CACHE_SIZE", d.cache_size)),
            max_question_chars=int(os.environ.get("MAX_QUESTION_CHARS", d.max_question_chars)),
        )


class DailyLimit:
    def __init__(self, limit: int, clock: Clock = time.time):
        self.limit = limit
        self.clock = clock
        self._day = self._today()
        self.count = 0

    def _today(self) -> str:
        return datetime.fromtimestamp(self.clock(), tz=timezone.utc).strftime("%Y-%m-%d")

    def _roll(self) -> None:
        today = self._today()
        if today != self._day:
            self._day, self.count = today, 0

    def allowed(self) -> bool:
        self._roll()
        return self.count < self.limit

    def record(self) -> None:
        self._roll()
        self.count += 1


class VisitorLimit:
    def __init__(self, limit: int, window_s: int, clock: Clock = time.time):
        self.limit, self.window_s, self.clock = limit, window_s, clock
        self._salt = os.urandom(16)  # per process, never stored: a hash cannot be traced back after a restart
        self._events: dict[str, deque[float]] = {}

    def key(self, raw: str) -> str:
        return hashlib.sha256(self._salt + raw.encode()).hexdigest()[:16]

    def _recent(self, key: str) -> deque[float]:
        """Events of one visitor inside the window. Visitors without recent events are forgotten."""
        q = self._events.get(key)
        if q is None:
            return deque()
        cutoff = self.clock() - self.window_s
        while q and q[0] <= cutoff:
            q.popleft()
        if not q:
            del self._events[key]
        return q

    def _prune(self) -> None:
        """Drop every visitor whose window has expired, so the map does not grow with one-time visitors."""
        for key in list(self._events):
            self._recent(key)

    def allowed(self, raw: str) -> bool:
        return len(self._recent(self.key(raw))) < self.limit

    def record(self, raw: str) -> None:
        self._prune()
        self._events.setdefault(self.key(raw), deque()).append(self.clock())

    def retry_after_s(self, raw: str) -> int:
        q = self._recent(self.key(raw))
        return max(1, int(q[0] + self.window_s - self.clock())) if q else 0


class AnswerCache:
    """LRU cache. Keys are hashes, so the cache holds no readable question text."""

    def __init__(self, size: int):
        self.size = size
        self._data: OrderedDict[str, object] = OrderedDict()

    @staticmethod
    def make_key(question: str, lang: str, mode: str, history: Iterable) -> str:
        h = hashlib.sha256()
        parts = [" ".join(question.lower().split()), lang, mode, *(f"{t.question}\x00{t.answer}" for t in history)]
        for part in parts:
            h.update(part.encode())
            h.update(b"\x01")
        return h.hexdigest()

    def get(self, key: str):
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key: str, value) -> None:
        if self.size <= 0:
            return
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.size:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)
