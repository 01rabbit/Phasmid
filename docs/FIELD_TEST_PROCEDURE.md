# Field Test Procedure

This procedure evaluates local leakage, operational clarity, recovery behavior, key separation, and user-error resistance.

Physical shock resistance and tamper-resistant casing are out of scope for the Raspberry Pi Zero 2 W prototype. This procedure evaluates local leakage, offline operation, key separation, power-loss behavior, response headers, logs, and user-error resistance.

The macOS-controlled remote SSH harness for running and collecting parts of this
procedure is tracked in GitHub issues `#89` through `#94` and implemented under
`scripts/pi_zero2w/` (for example, `run_remote_perf.sh` and `run_webui_probe.sh`).
This document remains the authoritative validation checklist for Raspberry Pi Zero
2 W field testing, and checklist completion is still required for validation claims.

## Boot and Service

- Boot without network dependency.
- Confirm WebUI binds to `127.0.0.1`.
- Confirm USB gadget access if configured.
- Confirm audit is disabled by default.
- Confirm debug is disabled by default.
- Confirm Field Mode is enabled for appliance evaluation.
- If the optional LUKS storage layer is used, confirm the encrypted volume opens and mounts before Phasmid starts.
- If the optional LUKS storage layer is used, confirm Phasmid fails closed when the encrypted volume is not mounted.

## Store and Retrieve

- Initialize an empty local container.
- Store a small text file.
- Store a binary file.
- Run metadata risk check on a file with obvious path or author text.
- Confirm unsupported metadata reduction fails safely.
- Retrieve with correct password and object cue.
- Retrieve with wrong password.
- Retrieve with object not detected.
- Test object ambiguity if two similar cues are configured.

## Restricted Behavior

- Confirm `/emergency` initially shows only restricted confirmation.
- Confirm restricted actions appear only after fresh restricted confirmation.
- Confirm typed action phrases are required.
- Confirm stale restricted sessions are rejected.
- Confirm retrieval does not show local-state side-effect messages or headers.

## Field Mode Maintenance

- Confirm Maintenance hides state path before restricted confirmation.
- Confirm audit export is hidden before restricted confirmation.
- Confirm token rotation is hidden before restricted confirmation.
- Confirm detailed diagnostics are hidden before restricted confirmation.
- Confirm Entry Management details are withheld before restricted confirmation.

## Capture-Visible Surfaces

- Review CLI output.
- Review browser console.
- Review response headers.
- Review download filenames.
- Review optional audit logs if enabled.
- Review systemd logs.
- Review shell history.
- Review temporary directories.

## Faults

- Test sudden power loss during idle.
- Test sudden power loss during Store.
- Test sudden power loss during Retrieve.
- Test sudden power loss after restricted recovery.
- Review the systemd journal after each power-loss case.
- Review temporary upload directories after each power-loss case.
- Test no network availability.
- Test no-network boot with the optional LUKS storage layer if used.
- Test camera unavailable.
- Test USB gadget-only access.

## Observability Measurements

Run the offline observability probe on the target hardware before field evaluation:

```bash
python3 - <<'EOF'
from phasmid.observability_probe import ObservabilityProbe, RecoveryPath
import argon2

def real_kdf(password: bytes, salt: bytes) -> bytes:
    return argon2.low_level.hash_secret_raw(
        password, salt, time_cost=3, memory_cost=65536,
        parallelism=1, hash_len=32, type=argon2.low_level.Type.ID,
    )

probe = ObservabilityProbe(kdf_fn=real_kdf)
report = probe.measure_all(n=5)
import json
print(json.dumps(report.summary(), indent=2))
print("max_timing_delta_ms:", report.max_timing_delta_ms())
EOF
```

Record the full JSON output and `max_timing_delta_ms` in `docs/REVIEW_VALIDATION_RECORD.md`
under "Observability Measurements".

Acceptance gate: the post-KDF timing delta between FAILED and RESTRICTED paths must be
less than 5% of Argon2id wall time, or the deviation must be documented with a risk
acceptance note.

Record failures with exact screen text, command output, and response headers.

## LUKS Calibration (Pi Zero 2 W)

When the optional LUKS layer is enabled for appliance deployment, run LUKS
calibration on the target unit and record measured values (not projections).

1. Run the remote harness including LUKS probe:
   - `./scripts/pi_zero2w/run_remote_perf.sh`
2. Confirm artifacts exist:
   - `release/pi-zero2w/luks_field_test.json`
   - `release/pi-zero2w/luks_field_test.log`
3. Validate acceptance targets:
   - `luksFormat` wall time target: approximately 2000 ms, accepted range 1500–4000 ms.
   - `luksOpen` wall time target: less than 3000 ms, accepted range less than 5000 ms.
   - AES instruction present in `/proc/cpuinfo`.
   - `dm_crypt` loadable on the target kernel.
4. Evaluate by device tier:
   - Tier-A/B may use strict setup-time acceptance directly.
   - Tier-C (Pi Zero 2 W class) must be assessed with constrained-device interpretation.
   - Tier-C uses constrained-device acceptance values with
     `acceptance_luks_format_ms_max=4300` and `acceptance_luks_open_ms_max=5000`.
   - Distinguish setup-time (`luksFormat`) from operational unlock (`luksOpen`).
5. Record `aes_acceleration_status`:
   - `confirmed`, `inferred`, `unavailable`, or `unknown`.
   - On ARM, capability flags may not expose acceleration exactly like x86 AES-NI.
   - Benchmark-backed `inferred` is acceptable when flag visibility is inconsistent.
6. If `luksFormat` exceeds 4000 ms:
   - reduce `PHASMID_LUKS_ITER_TIME_MS`,
   - record the measured trade-off in `docs/REVIEW_VALIDATION_RECORD.md`,
   - do not describe the value as "secure"; report measured timing on the tested model.
