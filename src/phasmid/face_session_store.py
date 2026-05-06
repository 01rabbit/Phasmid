from __future__ import annotations

import os
import time


class FaceSessionStore:
    """Local in-memory session and failure tracking for the UI face lock."""

    def __init__(self, *, ttl_seconds: int, verify_max_failures: int) -> None:
        self.ttl_seconds = ttl_seconds
        self.verify_max_failures = verify_max_failures
        self.sessions: dict[str, dict[str, str | float]] = {}
        self.failures: dict[str, int] = {}

    def create_session(self, client_id: str, token: str) -> None:
        self.sessions[token] = {
            "client_id": client_id,
            "expires_at": time.time()
            + int(
                os.environ.get("PHASMID_UI_FACE_SESSION_SECONDS", self.ttl_seconds)
            ),
        }

    def session_valid(self, client_id: str, token: str) -> bool:
        if not token:
            return False
        session = self.sessions.get(token)
        if not session:
            return False
        if session["client_id"] != client_id:
            return False
        if float(session["expires_at"]) < time.time():
            self.sessions.pop(token, None)
            return False
        return True

    def clear_session(self, token: str) -> None:
        if token:
            self.sessions.pop(token, None)

    def failure_count(self, client_id: str) -> int:
        return self.failures.get(client_id, 0)

    def record_failure(self, client_id: str) -> None:
        self.failures[client_id] = self.failures.get(client_id, 0) + 1

    def clear_failures(self, client_id: str | None = None) -> None:
        if client_id is None:
            self.failures.clear()
            return
        self.failures.pop(client_id, None)

    def locked_out(self, client_id: str) -> bool:
        return self.failure_count(client_id) >= self.verify_max_failures

    def reset(self) -> None:
        self.sessions.clear()
        self.failures.clear()
