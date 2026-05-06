"""
Offline observability probe for restricted-recovery path analysis (Issue #18).

Measures timing, response-shape, and filesystem-write differences between
the three local recovery paths:

  NORMAL     — correct passphrase, correct object cue → payload returned
  FAILED     — wrong passphrase or missing cue → no payload, no state change
  RESTRICTED — restricted-recovery passphrase → local clear executed (no payload)

No camera, vault file, or network connection is required.  The probe measures
the *code-path* timing and observable characteristics using a synthetic,
isolated environment.

This is a diagnostic and analysis tool, not production code.  Its output
records what CAN be observed; it does not imply that an observer CAN distinguish
paths in practice.  Actual claims about indistinguishability require
target-hardware measurements recorded in ``docs/REVIEW_VALIDATION_RECORD.md``.

Usage
-----
::

    from phasmid.observability_probe import ObservabilityProbe, RecoveryPath

    probe = ObservabilityProbe()
    results = probe.measure_all()
    for r in results:
        print(r.path_type, r.kdf_wall_ms, r.total_wall_ms, r.outcome)
"""
from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class RecoveryPath(str, Enum):
    """The three observable local recovery paths."""

    NORMAL = "normal"
    FAILED = "failed"
    RESTRICTED = "restricted"


@dataclass
class PathObservation:
    """
    Single observation of one recovery path.

    All timing values are wall-clock milliseconds measured with
    ``time.perf_counter``.  They represent in-process code-path duration
    on the measurement host, not on Pi Zero 2 W.
    """

    path_type: RecoveryPath
    kdf_wall_ms: float
    total_wall_ms: float
    outcome: str  # "success" | "auth_failure" | "restricted_clear" | "error"
    bytes_written: int  # filesystem bytes written during the operation
    exception_raised: bool
    notes: str = ""


@dataclass
class ObservabilityReport:
    """Aggregated comparison across all three paths."""

    observations: list[PathObservation] = field(default_factory=list)

    def summary(self) -> dict[str, object]:
        """Return a dict suitable for printing or JSON serialisation."""
        rows: dict[str, object] = {}
        for obs in self.observations:
            rows[obs.path_type.value] = {
                "kdf_wall_ms": round(obs.kdf_wall_ms, 2),
                "total_wall_ms": round(obs.total_wall_ms, 2),
                "outcome": obs.outcome,
                "bytes_written": obs.bytes_written,
                "exception_raised": obs.exception_raised,
                "notes": obs.notes,
            }
        return rows

    def max_timing_delta_ms(self) -> float:
        """Largest timing gap between any two paths (total_wall_ms)."""
        times = [obs.total_wall_ms for obs in self.observations]
        return max(times) - min(times) if len(times) > 1 else 0.0

    def paths_with_filesystem_writes(self) -> list[str]:
        return [obs.path_type.value for obs in self.observations if obs.bytes_written > 0]


class ObservabilityProbe:
    """
    Synthetic in-process probe for the three local recovery code paths.

    Each path is executed against an ephemeral temporary state directory
    so that filesystem-write observations are isolated and repeatable.

    The KDF simulation uses a configurable ``kdf_fn`` (default: a minimal
    PBKDF2-HMAC-SHA-256 with a fixed iteration count chosen to be fast
    enough for unit tests yet representative of the path structure).  On
    Pi Zero 2 W, replace ``kdf_fn`` with the real Argon2id call to
    obtain hardware-accurate measurements.
    """

    # Default iteration count for the synthetic KDF (PBKDF2-HMAC-SHA256).
    # Low by design: the probe measures path structure, not KDF hardness.
    DEFAULT_PBKDF2_ITERATIONS: int = 1000

    def __init__(
        self,
        kdf_fn: Callable[[bytes, bytes], bytes] | None = None,
        pbkdf2_iterations: int = DEFAULT_PBKDF2_ITERATIONS,
    ) -> None:
        if kdf_fn is not None:
            self._kdf = kdf_fn
        else:
            import hashlib

            iters = pbkdf2_iterations

            def _default_kdf(password: bytes, salt: bytes) -> bytes:
                return hashlib.pbkdf2_hmac("sha256", password, salt, iters, dklen=32)

            self._kdf = _default_kdf

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def measure_all(self, n: int = 1) -> ObservabilityReport:
        """
        Run each path *n* times and return an :class:`ObservabilityReport`
        with the mean observation per path.
        """
        report = ObservabilityReport()
        for path in RecoveryPath:
            obs_list = [self._run_path(path) for _ in range(n)]
            report.observations.append(self._mean_observation(obs_list))
        return report

    def measure_path(self, path: RecoveryPath, n: int = 1) -> PathObservation:
        """Measure a single *path* and return the mean :class:`PathObservation`."""
        obs_list = [self._run_path(path) for _ in range(n)]
        return self._mean_observation(obs_list)

    # ------------------------------------------------------------------
    # Path implementations
    # ------------------------------------------------------------------

    def _run_path(self, path: RecoveryPath) -> PathObservation:
        if path is RecoveryPath.NORMAL:
            return self._path_normal()
        if path is RecoveryPath.FAILED:
            return self._path_failed()
        return self._path_restricted()

    def _path_normal(self) -> PathObservation:
        """
        Simulate: correct passphrase → KDF → AES-GCM verify (success) → return payload.
        No filesystem writes beyond the synthetic state setup.
        """
        with tempfile.TemporaryDirectory() as tmp:
            salt = os.urandom(16)
            password = b"correct-passphrase"
            payload = os.urandom(256)

            t_total_start = time.perf_counter()
            t_kdf_start = time.perf_counter()
            _key = self._kdf(password, salt)
            kdf_ms = (time.perf_counter() - t_kdf_start) * 1000.0

            # Simulate successful AEAD verification: write + read a small record
            record_path = os.path.join(tmp, "record.bin")
            with open(record_path, "wb") as handle:
                handle.write(payload)
            with open(record_path, "rb") as handle:
                _ = handle.read()
            bytes_written = len(payload)

            total_ms = (time.perf_counter() - t_total_start) * 1000.0

        return PathObservation(
            path_type=RecoveryPath.NORMAL,
            kdf_wall_ms=kdf_ms,
            total_wall_ms=total_ms,
            outcome="success",
            bytes_written=bytes_written,
            exception_raised=False,
            notes="payload returned; temporary record read back",
        )

    def _path_failed(self) -> PathObservation:
        """
        Simulate: wrong passphrase → KDF → AES-GCM verify (InvalidTag) → error.
        No filesystem writes; exception raised internally, caught here.
        """
        salt = os.urandom(16)
        password = b"wrong-passphrase"
        exception_raised = False

        t_total_start = time.perf_counter()
        t_kdf_start = time.perf_counter()
        _key = self._kdf(password, salt)
        kdf_ms = (time.perf_counter() - t_kdf_start) * 1000.0

        # Simulate AES-GCM tag mismatch: raise and catch ValueError
        try:
            raise ValueError("authentication tag mismatch")
        except ValueError:
            exception_raised = True

        total_ms = (time.perf_counter() - t_total_start) * 1000.0

        return PathObservation(
            path_type=RecoveryPath.FAILED,
            kdf_wall_ms=kdf_ms,
            total_wall_ms=total_ms,
            outcome="auth_failure",
            bytes_written=0,
            exception_raised=exception_raised,
            notes="no payload; exception path; no state written",
        )

    def _path_restricted(self) -> PathObservation:
        """
        Simulate: restricted-recovery passphrase → KDF → AES-GCM verify (success,
        restricted slot) → local clear executed (state directory overwrite + remove).

        Observable difference: additional filesystem writes for the local clear.
        """
        with tempfile.TemporaryDirectory() as tmp:
            salt = os.urandom(16)
            password = b"restricted-recovery-passphrase"

            t_total_start = time.perf_counter()
            t_kdf_start = time.perf_counter()
            _key = self._kdf(password, salt)
            kdf_ms = (time.perf_counter() - t_kdf_start) * 1000.0

            # Simulate local clear: create synthetic state files and overwrite them
            bytes_written = 0
            state_files = ["lock.bin", "access.bin", "store.bin"]
            for name in state_files:
                path = os.path.join(tmp, name)
                content = os.urandom(128)
                with open(path, "wb") as handle:
                    handle.write(content)
                # Overwrite (best-effort secure erase simulation)
                with open(path, "r+b") as handle:
                    handle.write(os.urandom(128))
                    handle.flush()
                os.remove(path)
                bytes_written += 128 * 2  # write + overwrite

            total_ms = (time.perf_counter() - t_total_start) * 1000.0

        return PathObservation(
            path_type=RecoveryPath.RESTRICTED,
            kdf_wall_ms=kdf_ms,
            total_wall_ms=total_ms,
            outcome="restricted_clear",
            bytes_written=bytes_written,
            exception_raised=False,
            notes="no payload; local state files overwritten and removed",
        )

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    def _mean_observation(self, obs_list: list[PathObservation]) -> PathObservation:
        if len(obs_list) == 1:
            return obs_list[0]
        n = len(obs_list)
        return PathObservation(
            path_type=obs_list[0].path_type,
            kdf_wall_ms=sum(o.kdf_wall_ms for o in obs_list) / n,
            total_wall_ms=sum(o.total_wall_ms for o in obs_list) / n,
            outcome=obs_list[0].outcome,
            bytes_written=obs_list[0].bytes_written,
            exception_raised=obs_list[0].exception_raised,
            notes=obs_list[0].notes,
        )
