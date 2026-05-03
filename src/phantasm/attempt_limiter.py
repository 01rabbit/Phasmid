"""Local access-attempt limiter for recovery flows."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .config import access_lockout_seconds, access_max_failures
from .state_store import LocalStateStore

ATTEMPT_STATE_NAME = "access_attempts.json"


@dataclass(frozen=True)
class AttemptDecision:
    allowed: bool
    wait_seconds: int = 0


class AttemptLimiter:
    def __init__(
        self,
        max_failures: int | None = None,
        lockout_seconds: int | None = None,
        clock=None,
    ):
        self.max_failures = max_failures or access_max_failures()
        self.lockout_seconds = lockout_seconds or access_lockout_seconds()
        self.clock = clock or time.time
        self._state: dict[str, dict[str, int]] = {}

    def check(self, scope: str):
        state = self._state.get(scope, {"failures": 0, "locked_until": 0})
        now = int(self.clock())
        locked_until = int(state.get("locked_until", 0))
        if locked_until > now:
            return AttemptDecision(False, locked_until - now)
        return AttemptDecision(True, 0)

    def record_failure(self, scope: str):
        state = self._state.get(scope, {"failures": 0, "locked_until": 0})
        failures = int(state.get("failures", 0)) + 1
        locked_until = 0
        if failures >= self.max_failures:
            locked_until = int(self.clock()) + self.lockout_seconds
        self._state[scope] = {
            "failures": failures,
            "locked_until": locked_until,
        }

    def record_success(self, scope: str):
        self._state.pop(scope, None)


class FileAttemptLimiter(AttemptLimiter):
    def __init__(self, store: LocalStateStore | None = None, **kwargs):
        super().__init__(**kwargs)
        self.store = store or LocalStateStore()
        self._state = self._load()

    def record_failure(self, scope: str):
        super().record_failure(scope)
        self._save()

    def record_success(self, scope: str):
        super().record_success(scope)
        self._save()

    def _load(self):
        try:
            data = self.store.read_json(ATTEMPT_STATE_NAME)
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            str(scope): {
                "failures": int(value.get("failures", 0)),
                "locked_until": int(value.get("locked_until", 0)),
            }
            for scope, value in data.items()
            if isinstance(value, dict)
        }

    def _save(self):
        self.store.write_json_atomic(ATTEMPT_STATE_NAME, self._state)
