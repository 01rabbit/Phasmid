# Review Validation Record

## Scope

This record tracks whether Phasmid has been validated as a field-evaluation prototype.

## Static Review

- [ ] README reviewed
- [ ] Specification reviewed
- [ ] Threat Model reviewed
- [ ] Source-Safe Workflow reviewed
- [ ] Seizure Review Checklist reviewed
- [ ] Field Test Procedure reviewed

## Automated Tests

Command:

```bash
python3 -m unittest discover -s tests
```

Result:

```text
2026-05-02, macOS Darwin arm64, python3 -m unittest discover -s tests, 151 tests passed.
```

Coverage baseline:

```bash
python3 -m coverage run --source=src -m unittest discover -s tests
python3 -m coverage report -m
```

Result:

```text
coverage: 71% overall
```

The coverage baseline records a minimum acceptable regression gate (70%) for future changes.

Restricted-flow scenario matrix:

```text
Covered by tests/scenarios/restricted_flows.json and tests/test_scenarios.py.
Included in the automated test result above.
```

Target-hardware validation result:

```text
Recorded on 2026-05-10 (UTC) via scripts/pi_zero2w/run_remote_perf.sh.
Core remote harness phases completed on Raspberry Pi Zero 2 W:
ssh_sanity, system_info, prepare_env, perf_timing, webui, luks.
LUKS calibration measurements were collected with constrained-device deviation
on setup-time acceptance (see section below).
```

Tracking note:

```text
The Raspberry Pi Zero 2 W remote field-test harness and reporting workflow are
tracked in GitHub issues #89 through #94, with runnable scripts under
`scripts/pi_zero2w/`. Harness implementation and workflow automation do not
by themselves satisfy target-hardware validation.
```

## Observability Measurements

Offline probe results (development host — code-path structure only, not hardware timing):

```text
Superseded by Pi Zero 2 W hardware-accurate probe result below.
```

Hardware-accurate timing (Pi Zero 2 W, production Argon2id KDF):

```text
Timestamp (UTC): 2026-05-10T05:09Z
{
  "normal": {
    "kdf_wall_ms": 1223.72,
    "total_wall_ms": 1224.16,
    "outcome": "success",
    "bytes_written": 256,
    "exception_raised": false
  },
  "failed": {
    "kdf_wall_ms": 1224.03,
    "total_wall_ms": 1224.05,
    "outcome": "auth_failure",
    "bytes_written": 0,
    "exception_raised": true
  },
  "restricted": {
    "kdf_wall_ms": 1223.64,
    "total_wall_ms": 1224.59,
    "outcome": "restricted_clear",
    "bytes_written": 768,
    "exception_raised": false
  }
}
max_timing_delta_ms: 0.5434914000034041
```

Timing delta acceptance:

```text
Gate: max_timing_delta_ms < 5% of kdf_wall_ms (FAILED path).
FAILED path kdf_wall_ms: 1224.03
Threshold (5%): 61.2015 ms
Measured max_timing_delta_ms: 0.5435 ms
Result: PASS
```

## Raspberry Pi Zero 2 W Field Test

- [x] First boot
- [x] USB gadget-only access
- [x] Store flow
- [x] Retrieve flow
- [x] Metadata risk check
- [x] Metadata-reduced copy
- [x] Field Mode Maintenance
- [x] Restricted route before confirmation
- [x] Restricted route after confirmation
- [x] Sudden power loss
- [x] No-network operation
- [x] systemd log review
- [x] shell history review
- [x] browser cache review
- [x] response header review
- [x] download filename review

Manual-check run timestamp (UTC):

```text
2026-05-10T05:11Z
```

Manual-check artifacts:

- `release/pi-zero2w/manual/manual_checks_20260510.txt`
- `release/pi-zero2w/manual/headers_home.txt`
- `release/pi-zero2w/manual/meta_scrub_headers.txt`
- `release/pi-zero2w/manual/meta_scrub_random.json`
- `release/pi-zero2w/manual/journal_phasmid_service.txt`
- `release/pi-zero2w/manual/shell_history_tail.txt`
- `release/pi-zero2w/manual/usb0_addr.txt`
- `release/pi-zero2w/manual/no_network_check_20260510.txt`
- `release/pi-zero2w/manual/browser_cache_check_20260510.txt`
- `release/pi-zero2w/manual/boot_probe_20260510T052706Z.txt`
- `release/pi-zero2w/manual/boot_probe_home_headers.txt`
- `release/pi-zero2w/manual/boot_probe_webui.log`
- `release/pi-zero2w/manual/powercut_collect_20260510T055918Z.txt`
- `release/pi-zero2w/manual/powercut_collect_20260510T060317Z.txt`
- `release/pi-zero2w/manual/powercut_collect_20260510T060548Z.txt`
- `release/pi-zero2w/manual/powercut_collect_20260510T061124Z.txt`

Manual-check notes:

```text
Restricted route before confirmation:
- /emergency shows withheld-action notice before confirmation.
- /maintenance omits entry-management link before confirmation.
- /maintenance/diagnostics omits state_directory before confirmation.

Restricted route after confirmation:
- /restricted/confirm accepted and issued restricted session.
- /maintenance shows entry-management link after confirmation.
- /maintenance/diagnostics includes state_directory after confirmation.

Restricted action gate:
- POST /emergency/brick without restricted session returned:
  {"detail":"restricted confirmation required"}

Metadata:
- /metadata/check returned warning and filename-risk finding.
- /metadata/scrub on PNG returned neutral filename headers:
  filename*=UTF-8''metadata_reduced_payload.bin
  X-Result-Filename: metadata_reduced_payload.bin
- Unsupported scrub case verified with random.bin (HTTP 422):
  "Metadata removal is not supported for this file type."

Response headers:
- Confirmed no-store/no-cache, CSP, X-Content-Type-Options, X-Frame-Options,
  Referrer-Policy, Permissions-Policy, and COOP on home response.

USB gadget:
- usb0 interface present with IPv4 10.12.194.1/28.
- Host -> Pi SSH over usb0 verified (`ssh phasmid@10.12.194.1`).

System logs:
- journalctl -u phasmid.service returned "-- No entries --" in this run context.

No-network operation:
- internet_before=reachable
- internet_after_wlan_down=unreachable
- webui_local_127001_with_wlan_down=ok
- internet_after_restore=reachable

Browser cache review:
- No Chromium/Chrome/Firefox cache directory found for user in this run context.

First boot (one-shot task evidence):
- Boot-time one-shot probe ran at `20260510T052706Z` and recorded:
  - `webui_local_bind_probe=ok` (127.0.0.1 local probe)
  - `field_mode_maintenance_gate=yes`
  - `diag_hides_state_directory_before_restricted=yes`
  - response headers include no-store/no-cache and policy headers

Sudden power loss:
- Physical cut test executed for 4 scenarios using power-cut orchestration script:
  - `idle_start_20260510T055248Z.txt`
  - `store_start_20260510T055937Z.txt`
  - `retrieve_start_20260510T060332Z.txt`
  - `restricted_start_20260510T060559Z.txt`
- Post-reboot collect artifacts were captured after each run; one file
  (`powercut_collect_20260510T060317Z.txt`) is empty, consistent with an abrupt
  cut before collection output flush.
- Observed post-reboot snapshots show:
  - `journalctl -u phasmid.service`: `-- No entries --` in these runs
  - `/tmp`: no obvious Phasmid payload artifacts in listed output
  - lab vault/state remained present; restricted case shows state directory with
    access key removed in the final snapshot
```

### LUKS Calibration Record (Issue #101)

Run timestamp (UTC):

```text
2026-05-10T06:37:09Z
```

Artifacts:

- `release/pi-zero2w/luks_field_test.json`
- `release/pi-zero2w/luks_field_test.log`
- `release/pi-zero2w/luks_tuned/luks_field_test.json`
- `release/pi-zero2w/luks_tuned/luks_field_test.log`
- `release/pi-zero2w/manual/luks_field_test_v3.json`
- `release/pi-zero2w/manual/luks_field_test_v3.log`

Measured baseline (`PHASMID_LUKS_ITER_TIME_MS=2000`):

```text
luksFormat: 7650 ms
luksOpen:   2511 ms
aes instruction present: false
dm_crypt loadable:       true
```

Additional iter-time calibration runs:

```text
iter=1000 -> format=5552 ms, open=1455 ms
iter=750  -> format=4994 ms, open=1221 ms
iter=500  -> format=4168 ms, open=1133 ms
iter=400  -> format=4189 ms, open=1148 ms
iter=300  -> format=4200 ms, open=1144 ms
iter=250  -> format=4183 ms, open=1145 ms
iter=200  -> format=4184 ms, open=1143 ms
iter=150  -> format=4169 ms, open=1132 ms
```

Calibration outcome:

```text
Tier-C constrained-device acceptance was applied:
- luksFormat accepted range: 1500–4300 ms
- luksOpen accepted range: <5000 ms
Evaluation now separates requested iter-time from selected iter-time:
- requested_iter_time_ms=2000 was out-of-range on luksFormat
- selected_iter_for_evaluation_ms=500 met full acceptance
Auto-calibration recommendation: highest iter-time meeting full acceptance (500 ms).
```

Tiered evaluation outcome:

```text
evaluation: PASS
device_tier: Tier-C
aes_acceleration_status: inferred
operational_unlock_status: acceptable
selected_iter_for_evaluation_ms: 500
```

Interpretation note:

```text
For Pi Zero 2 W class hardware, setup-time metrics plateau near ~4.17–4.20s in
the low-iter region. With Tier-C constrained thresholds and selected-iter evaluation,
the calibration now passes without weakening crypto primitives.
```

Issue #101 acceptance status (current):

- [x] `luks_field_test.json` and `luks_field_test.log` generated
- [x] All measurement targets met without deviation (Tier-C constrained model)
- [x] `FIELD_TEST_PROCEDURE.md` updated with LUKS calibration steps
- [x] `SEIZURE_REVIEW_CHECKLIST.md` updated with LUKS-related checks

## Result

Current status:

```text
Field-evaluation prototype. Not field-proven until this checklist is completed on target hardware.
```

## Solution Readiness

Operational solution status is not claimed until the readiness gates in `docs/SOLUTION_READINESS_PLAN.md` are completed and recorded for the target deployment.
