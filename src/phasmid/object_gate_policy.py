from __future__ import annotations

from dataclasses import dataclass, replace

from .object_model_gate import ObjectModelGateResult


@dataclass(frozen=True)
class ObjectGateResult:
    state: str  # "accepted" | "rejected" | "ambiguous" | "no_signal" | "error"
    orb_score: float | None
    model_score: float | None
    quality_score: float | None
    stable_frames: int
    attempted_frames: int
    elapsed_ms: int
    reason_code: str

    def with_stable_frames(self, stable_frames: int) -> "ObjectGateResult":
        return replace(self, stable_frames=stable_frames)


class ObjectGatePolicy:
    """Combines ORB and model outputs into a neutral operational result."""

    def __init__(self, *, min_quality_score: float = 0.08) -> None:
        self.min_quality_score = min_quality_score

    def combine(
        self,
        *,
        orb_match: dict[str, object] | None,
        model_result: ObjectModelGateResult,
        quality_score: float | None,
        attempted_frames: int,
        elapsed_ms: int,
    ) -> ObjectGateResult:
        if quality_score is None:
            return self._result(
                state="no_signal",
                orb_score=None,
                model_score=model_result.score,
                quality_score=None,
                attempted_frames=attempted_frames,
                elapsed_ms=elapsed_ms,
                reason_code="no_frame",
            )
        if quality_score < self.min_quality_score:
            return self._result(
                state="no_signal",
                orb_score=None,
                model_score=model_result.score,
                quality_score=quality_score,
                attempted_frames=attempted_frames,
                elapsed_ms=elapsed_ms,
                reason_code="low_quality",
            )

        orb_accepted = orb_match is not None
        orb_score = self._orb_score(orb_match)

        if orb_accepted and model_result.state == "accepted":
            return self._result(
                state="accepted",
                orb_score=orb_score,
                model_score=model_result.score,
                quality_score=quality_score,
                attempted_frames=attempted_frames,
                elapsed_ms=elapsed_ms,
                reason_code="combined_match",
            )
        if orb_accepted and model_result.state == "unavailable":
            return self._result(
                state="accepted",
                orb_score=orb_score,
                model_score=None,
                quality_score=quality_score,
                attempted_frames=attempted_frames,
                elapsed_ms=elapsed_ms,
                reason_code="orb_match",
            )
        if orb_accepted and model_result.state == "rejected":
            return self._result(
                state="ambiguous",
                orb_score=orb_score,
                model_score=model_result.score,
                quality_score=quality_score,
                attempted_frames=attempted_frames,
                elapsed_ms=elapsed_ms,
                reason_code="ambiguous_match",
            )
        if not orb_accepted and model_result.state == "accepted":
            return self._result(
                state="ambiguous",
                orb_score=orb_score,
                model_score=model_result.score,
                quality_score=quality_score,
                attempted_frames=attempted_frames,
                elapsed_ms=elapsed_ms,
                reason_code="ambiguous_match",
            )
        if model_result.state == "error":
            return self._result(
                state="error",
                orb_score=orb_score,
                model_score=None,
                quality_score=quality_score,
                attempted_frames=attempted_frames,
                elapsed_ms=elapsed_ms,
                reason_code="model_error",
            )
        return self._result(
            state="rejected",
            orb_score=orb_score,
            model_score=model_result.score,
            quality_score=quality_score,
            attempted_frames=attempted_frames,
            elapsed_ms=elapsed_ms,
            reason_code=(
                "model_reject" if model_result.state == "rejected" else "unstable_match"
            ),
        )

    def _orb_score(self, orb_match: dict[str, object] | None) -> float | None:
        if orb_match is None:
            return None
        raw_inliers = orb_match.get("inliers", 0)
        if not isinstance(raw_inliers, (int, float)):
            return None
        inliers = int(raw_inliers)
        return float(inliers)

    def _result(
        self,
        *,
        state: str,
        orb_score: float | None,
        model_score: float | None,
        quality_score: float | None,
        attempted_frames: int,
        elapsed_ms: int,
        reason_code: str,
    ) -> ObjectGateResult:
        return ObjectGateResult(
            state=state,
            orb_score=orb_score,
            model_score=model_score,
            quality_score=quality_score,
            stable_frames=1 if state == "accepted" else 0,
            attempted_frames=attempted_frames,
            elapsed_ms=elapsed_ms,
            reason_code=reason_code,
        )
