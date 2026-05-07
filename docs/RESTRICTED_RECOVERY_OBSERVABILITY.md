# Restricted Recovery Observability Analysis

## Purpose

This document records what a local observer can and cannot distinguish across the three
local recovery paths in Phasmid.  It is a companion to `docs/THREAT_MODEL.md` and
`docs/REVIEW_VALIDATION_RECORD.md`, and references the offline measurement harness
in `src/phasmid/observability_probe.py`.

"Observable" here means measurable by an adversary with local access to the device
running Phasmid — without access to its secrets or source code — while a recovery
operation executes.

---

## The Three Recovery Paths

| Path | Trigger condition | Outcome |
|---|---|---|
| NORMAL | Correct access passphrase + matching object cue | Payload returned |
| FAILED | Wrong passphrase or missing/mismatched cue | No payload, no state change |
| RESTRICTED | Correct restricted-recovery passphrase | Local clear executed, no payload |

---

## Observable Channels

### 1. Timing

**What is observable:** Wall-clock duration of each path's code execution, as measured
by `time.perf_counter`.  An adversary with high-resolution access to the process (e.g.
side-channel instrumentation) could record this.

**Probe finding (synthetic, development host):**

The `ObservabilityProbe` records `kdf_wall_ms` and `total_wall_ms` for each path.
The KDF is the dominant time component on all three paths when the real Argon2id is
used.  After the KDF, the per-path overhead is:

- NORMAL: one file write + one file read.
- FAILED: one raise-and-catch of a `ValueError`.
- RESTRICTED: write + overwrite + remove of three synthetic state files.

The restricted path therefore has higher post-KDF wall time than the failed path.
The magnitude of this difference depends on storage speed and cache state.

**Mitigation:** The KDF cost (Argon2id on Pi Zero 2 W) is expected to dominate
post-KDF differences by two or more orders of magnitude.  This does not eliminate
the difference; it narrows the signal-to-noise ratio available to a passive observer.
Hardware-accurate measurements must be recorded in `REVIEW_VALIDATION_RECORD.md` to
confirm this claim on the target platform.

### 2. Filesystem Writes

**What is observable:** A process-level filesystem monitor (e.g. `strace`, `/proc/fd`
inspection, or eBPF) could record the number and size of file writes during recovery.

**Probe finding:**

| Path | `bytes_written` (synthetic) |
|---|---|
| NORMAL | 256 bytes (payload write) |
| FAILED | 0 bytes |
| RESTRICTED | 768 bytes (3 × 128-byte write + 128-byte overwrite per file) |

The failed path is structurally distinct from both the normal and restricted paths in
that it performs no filesystem writes.  An observer with filesystem monitoring can
distinguish the failed path from either success case.

The normal and restricted paths both write bytes, but the restricted path writes
significantly more due to the overwrite-before-remove pattern of the local clear.

**Mitigation:** The local clear is inherently write-heavy.  Reducing write count would
weaken the clear's erasure guarantee.  The trade-off is: stronger local clear →
more observable write activity.  This is an accepted design constraint.  The restricted
path is not intended to be indistinguishable from the normal path at the filesystem
level; it is intended to be indistinguishable from the operator's perspective in terms
of what the WebUI presents.

### 3. Exception Propagation

**What is observable:** An observer running under the same process (or with access to
Python tracebacks, system crash handlers, or audit logs) could detect whether an
exception was raised during recovery.

**Probe finding:**

- NORMAL: no exception raised.
- FAILED: `ValueError` raised and caught internally; `exception_raised = True`.
- RESTRICTED: no exception raised.

**Mitigation:** The exception is caught internally and converted to a neutral HTTP
response.  No exception detail is emitted to the WebUI or response headers.  The
FAILED and RESTRICTED paths are therefore indistinguishable to the WebUI client.

### 4. Response Shape and Headers

This channel is not exercised by the offline probe but is covered by `test_web_server.py`
and `tests/scenarios/restricted_flows.json`.

The WebUI returns the same HTTP status code and neutral message body for FAILED and
RESTRICTED outcomes.  No custom headers expose path-specific state.

---

## Summary of Indistinguishability Properties

| Observer type | NORMAL vs FAILED | NORMAL vs RESTRICTED | FAILED vs RESTRICTED |
|---|---|---|---|
| WebUI client | Payload present vs absent | Payload present vs absent | Indistinguishable |
| Filesystem monitor | Writes vs no writes | Both write; RESTRICTED writes more | Writes vs no writes |
| Timing side-channel | KDF-dominated; minor post-KDF delta | KDF-dominated; minor post-KDF delta | Small delta; filesystem overhead |
| Exception observer | No exception vs exception | No exception vs no exception | Exception vs no exception |

---

## Pi Zero 2 W Measurement Plan

The synthetic probe results above are recorded on a development host.  They measure
code-path structure, not hardware timing.  The following steps must be completed
on the target platform before claiming hardware-accurate values:

1. Install Phasmid on a Pi Zero 2 W in appliance configuration.
2. Replace the synthetic `kdf_fn` with the real Argon2id call:
   ```python
   import argon2
   def real_kdf(password: bytes, salt: bytes) -> bytes:
       return argon2.low_level.hash_secret_raw(
           password, salt, time_cost=3, memory_cost=65536,
           parallelism=1, hash_len=32, type=argon2.low_level.Type.ID,
       )
   probe = ObservabilityProbe(kdf_fn=real_kdf)
   ```
3. Run `probe.measure_all(n=10)` and record `report.summary()` and
   `report.max_timing_delta_ms()`.
4. Record results in `docs/REVIEW_VALIDATION_RECORD.md` under
   "Observability Measurements".
5. Compare KDF wall time to post-KDF delta for each path pair.  If the delta
   exceeds 5% of KDF time, investigate and document the source.

---

## Acceptance Criteria

- [ ] Offline probe tests pass on development host (`tests/test_observability_probe.py`).
- [ ] Hardware-accurate timing recorded in `REVIEW_VALIDATION_RECORD.md`.
- [ ] Post-KDF timing delta between FAILED and RESTRICTED is less than 5% of Argon2id
  wall time on Pi Zero 2 W (or the deviation is documented with a risk acceptance note).
- [ ] WebUI response parity confirmed: FAILED and RESTRICTED return the same HTTP status
  and body text (covered by existing scenario tests).
