from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CueFrameSignal:
    """Single-frame neutral cue signal used by policy evaluation."""

    object_state: str
    relation_ok: bool = False
    token: str = ""


@dataclass(frozen=True)
class CuePolicyResult:
    """Neutral policy outcome. Not cryptographic material."""

    sequence_state: str
    accepted: bool
    ambiguous: bool
    reason: str


class ObjectCuePolicyGate:
    """
    Experimental policy gate for multi-object and short sequence evaluation.

    This layer combines neutral per-frame signals only. It must never derive
    or modify cryptographic keys, KDF inputs, or container layout values.
    """

    VALID_STATES = {"none", "detected", "matched", "ambiguous"}

    def __init__(
        self, *, required_stable_frames: int = 3, sequence_timeout_frames: int = 8
    ):
        self.required_stable_frames = max(1, int(required_stable_frames))
        self.sequence_timeout_frames = max(
            self.required_stable_frames, int(sequence_timeout_frames)
        )

    def evaluate(
        self, frames: list[CueFrameSignal], expected_sequence: list[str] | None = None
    ) -> CuePolicyResult:
        if not frames:
            return CuePolicyResult(
                sequence_state="idle",
                accepted=False,
                ambiguous=False,
                reason="no_signal",
            )

        normalized = [self._normalize(frame) for frame in frames]
        if any(frame.object_state == "ambiguous" for frame in normalized):
            return CuePolicyResult(
                sequence_state="ambiguous",
                accepted=False,
                ambiguous=True,
                reason="ambiguous_scene",
            )

        if all(frame.object_state == "none" for frame in normalized):
            return CuePolicyResult(
                sequence_state="idle",
                accepted=False,
                ambiguous=False,
                reason="no_object",
            )

        if expected_sequence:
            return self._evaluate_sequence(normalized, expected_sequence)

        stable = self._stable_match_count(normalized)
        if stable >= self.required_stable_frames:
            return CuePolicyResult(
                sequence_state="matched",
                accepted=True,
                ambiguous=False,
                reason="stable_match",
            )

        return CuePolicyResult(
            sequence_state="collecting",
            accepted=False,
            ambiguous=False,
            reason="insufficient_stability",
        )

    def _evaluate_sequence(
        self, frames: list[CueFrameSignal], expected_sequence: list[str]
    ) -> CuePolicyResult:
        if not expected_sequence:
            return CuePolicyResult(
                sequence_state="idle",
                accepted=False,
                ambiguous=False,
                reason="empty_sequence",
            )

        idx = 0
        frame_budget = min(len(frames), self.sequence_timeout_frames)
        for frame in frames[:frame_budget]:
            if frame.object_state != "matched":
                continue
            if not frame.relation_ok:
                continue
            if frame.token == expected_sequence[idx]:
                idx += 1
                if idx == len(expected_sequence):
                    return CuePolicyResult(
                        sequence_state="matched",
                        accepted=True,
                        ambiguous=False,
                        reason="sequence_complete",
                    )

        if frame_budget >= self.sequence_timeout_frames:
            return CuePolicyResult(
                sequence_state="timeout",
                accepted=False,
                ambiguous=False,
                reason="sequence_timeout",
            )

        return CuePolicyResult(
            sequence_state="collecting",
            accepted=False,
            ambiguous=False,
            reason="sequence_incomplete",
        )

    def _stable_match_count(self, frames: list[CueFrameSignal]) -> int:
        count = 0
        for frame in frames:
            if frame.object_state == "matched":
                count += 1
        return count

    def _normalize(self, frame: CueFrameSignal) -> CueFrameSignal:
        state = (
            frame.object_state if frame.object_state in self.VALID_STATES else "none"
        )
        token = frame.token.strip()
        return CueFrameSignal(
            object_state=state, relation_ok=bool(frame.relation_ok), token=token
        )
