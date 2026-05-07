from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

import numpy as np


class ObjectModelBackend(Protocol):
    def score_frame(self, frame: np.ndarray) -> float | None:
        """Return a neutral similarity score in the range 0.0-1.0."""


@dataclass(frozen=True)
class ObjectModelGateResult:
    state: str  # "accepted" | "rejected" | "unavailable" | "error"
    score: float | None
    elapsed_ms: int
    reason_code: str


class ObjectModelGate:
    """Experimental local-only object model gate.

    The default backend is absent. This keeps the model path disabled in
    practice until a tiny offline backend is validated on target hardware.
    """

    def __init__(
        self,
        *,
        backend: ObjectModelBackend | None = None,
        accept_threshold: float = 0.75,
    ) -> None:
        self.backend = backend
        self.accept_threshold = accept_threshold

    def evaluate_frame(self, frame: np.ndarray | None) -> ObjectModelGateResult:
        started = time.perf_counter()
        if frame is None:
            return ObjectModelGateResult(
                state="unavailable",
                score=None,
                elapsed_ms=self._elapsed_ms(started),
                reason_code="no_frame",
            )
        if self.backend is None:
            return ObjectModelGateResult(
                state="unavailable",
                score=None,
                elapsed_ms=self._elapsed_ms(started),
                reason_code="model_unavailable",
            )
        try:
            score = self.backend.score_frame(frame)
        except Exception:
            return ObjectModelGateResult(
                state="error",
                score=None,
                elapsed_ms=self._elapsed_ms(started),
                reason_code="model_error",
            )
        if score is None:
            return ObjectModelGateResult(
                state="unavailable",
                score=None,
                elapsed_ms=self._elapsed_ms(started),
                reason_code="model_unavailable",
            )
        state = "accepted" if score >= self.accept_threshold else "rejected"
        return ObjectModelGateResult(
            state=state,
            score=float(score),
            elapsed_ms=self._elapsed_ms(started),
            reason_code="model_match" if state == "accepted" else "model_reject",
        )

    def _elapsed_ms(self, started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
