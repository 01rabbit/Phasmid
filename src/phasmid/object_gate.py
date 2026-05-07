from __future__ import annotations

import time

import cv2
import numpy as np

from .object_gate_policy import ObjectGatePolicy, ObjectGateResult
from .object_model_gate import ObjectModelGate


class ObjectGate:
    """Experimental support layer combining ORB and an optional model result."""

    def __init__(
        self,
        *,
        model_gate: ObjectModelGate | None = None,
        policy: ObjectGatePolicy | None = None,
    ) -> None:
        self.model_gate = model_gate or ObjectModelGate()
        self.policy = policy or ObjectGatePolicy()

    def evaluate_frame(
        self,
        *,
        frame: np.ndarray | None,
        orb_match: dict[str, object] | None,
    ) -> ObjectGateResult:
        started = time.perf_counter()
        quality_score = self._quality_score(frame)
        model_result = self.model_gate.evaluate_frame(frame)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return self.policy.combine(
            orb_match=orb_match,
            model_result=model_result,
            quality_score=quality_score,
            attempted_frames=1,
            elapsed_ms=elapsed_ms,
        )

    def _quality_score(self, frame: np.ndarray | None) -> float | None:
        if frame is None:
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        return min(1.0, variance / 500.0)
