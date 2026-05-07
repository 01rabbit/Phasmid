# Title

Add Raspberry Pi Zero 2 W Remote Field Test Harness

> **Tracking**: This issue is the parent specification for the implementation track
> documented in `AGENTS.md` as issues #89–#94. The phased implementation issues
> (`#90` through `#94`) each correspond to one Phase defined in this document.

## Background

Phasmid must be validated on actual constrained target hardware before stronger operational claims are made. Raspberry Pi Zero 2 W is an important target because it reflects the project's expected low-power appliance class, but it has limited CPU throughput, memory capacity, storage I/O, and thermal headroom.

The current development workflow runs on macOS with Codex and editor tooling available locally. That workflow does not translate directly to Raspberry Pi Zero 2 W. The target device should be treated as a remote SSH execution target, not as a full development workstation. Heavy interactive tooling, editor-dependent workflows, container-first workflows, and GUI assumptions are not appropriate for this target.

The correct design for this work is therefore a Mac-controlled remote SSH field-test harness that can prepare the target, run bounded validation tasks, collect structured measurements, and copy results back to the Mac for review. This issue exists to define that harness and its documentation, not to change Phasmid security semantics.

Phasmid's central security property is timing-path consistency: the NORMAL, FAILED, and RESTRICTED code paths must not be distinguishable by timing observation. This property must be measured on real Pi Zero 2 W hardware, not only on x86 development hosts, because ARM Cortex-A53 scheduling, memory controller latency, and SD card I/O patterns can introduce timing variance that does not appear on a Mac.

## Objective

Add scripts and documentation that allow a developer on macOS to run a repeatable remote field-evaluation workflow against a Raspberry Pi Zero 2 W over SSH.

The implementation should allow a developer on macOS to:

- synchronize the repository to the Raspberry Pi Zero 2 W;
- prepare a Python virtual environment on the Raspberry Pi;
- install dependencies;
- run install viability checks;
- run CLI, crypto, vault, object-cue, WebUI, and field workflow tests;
- run coercion-path timing consistency measurements on the target hardware;
- collect performance and system telemetry;
- collect partial-failure diagnostics when a phase cannot complete;
- copy structured results back to the Mac.

This issue is implementation work for target-hardware validation support. It is not the target-hardware validation result itself.

## Non-Goals

- Do not run Codex on the Raspberry Pi.
- Do not require VS Code Remote SSH on the Raspberry Pi.
- Do not require Docker.
- Do not require a GUI.
- Do not weaken cryptographic defaults.
- Do not change Phasmid security semantics.
- Do not introduce remote unlock, remote wipe, covert communication, or network-facing security-sensitive behavior.
- Do not expose the WebUI to untrusted networks by default.
- Do not delete unrelated files on the Raspberry Pi.
- Do not require root unless absolutely necessary and explicitly documented.
- Do not silently tune benchmarks by changing production defaults.
- Do not present benchmark success as proof of field-proven security.
- Do not claim that timing-gate passage on one hardware unit proves security for all deployments.

## Target Environment

Host:

- macOS
- Git repository checked out locally
- SSH client available
- `rsync` available, or a documented fallback path if `rsync` is missing

Target:

- Raspberry Pi Zero 2 W (ARM Cortex-A53 quad-core, 512 MB RAM)
- Raspberry Pi OS Lite **64-bit (aarch64) required** — 32-bit armv7l is not supported because key dependency wheels are not available for that platform
- Python 3 available on the device
- SSH enabled during test; may be disabled in production appliance use
- limited CPU and memory capacity
- limited storage I/O and thermal headroom
- SD card storage (wear leveling applies; overwrite-based destruction is best-effort only)
- optional camera and object-cue test assets if available

Camera hardware note (if camera testing is in scope):

- Raspberry Pi Camera Module 3 NoIR Wide is the documented reference camera for Pi Zero 2 W appliance deployments.
- Pi Zero 2 W uses a 22-pin camera connector. The standard 15-pin camera cable is **not** compatible. A 22-pin-to-15-pin Raspberry Pi Zero camera adapter cable is required. This is a common field mistake that will silently prevent camera-based tests from running.
- Document this requirement in `docs/PI_ZERO2W_FIELD_TEST.md` prominently.

## Required Environment Variables

The top-level harness must require these variables:

- `PHASMID_PI_HOST` — hostname or IP address of the Raspberry Pi
- `PHASMID_PI_USER` — SSH username on the Raspberry Pi
- `PHASMID_PI_REMOTE_DIR` — absolute path to the working directory on the Raspberry Pi
- `PHASMID_PI_SSH_PORT` — SSH port (typically `22`)
- `PHASMID_PI_SSH_KEY` — path to the SSH private key on the Mac (optional but recommended; if unset, default SSH agent behavior applies; document both cases)

Requirements:

- all required variables must be validated before remote work begins;
- missing variables must fail safely with clear, single-purpose error messages;
- empty values must be treated as invalid;
- the harness must print the exact variable names that are missing;
- the harness must not continue with guessed defaults for host, user, or remote directory.

## Known Blockers That the Implementation Must Resolve

The following issues are confirmed by pre-implementation inspection of the repository and PyPI. The implementation must address each one explicitly.

### Blocker 1: `numpy==2.2.6` requires 64-bit Raspberry Pi OS (aarch64) — 32-bit will fail

Verified: `numpy==2.2.6` has a `manylinux_2_17_aarch64` (manylinux2014) wheel on PyPI (14.3 MB). This wheel installs correctly on 64-bit Raspberry Pi OS (Bookworm, glibc 2.36, aarch64). It does NOT exist for 32-bit ARM (`armv7l`), so installing from source would be required on 32-bit OS.

Consequence: **64-bit Raspberry Pi OS Lite is required, not merely recommended.** The target environment section says "64-bit recommended" but this must be strengthened to "64-bit required" for standard pip wheel installation to work without source compilation.

The harness must:

- check that `uname -m` returns `aarch64` on the Pi before attempting installation;
- if `armv7l` is returned, fail with a clear error message explaining that 32-bit Raspberry Pi OS is not supported and that 64-bit must be flashed;
- not silently attempt a multi-hour source compilation on a 32-bit image.

If no option works within a reasonable time budget, the implementation must record `numpy_install_failed` in the JSON output and skip categories that require numpy, rather than blocking the entire test run.

### Blocker 2: `pip install -r requirements.txt` does not install the `phasmid` CLI entry point

The `phasmid` command is defined in `pyproject.toml` under `[project.scripts]`. Installing only `requirements.txt` installs the dependencies but does not create the `phasmid` executable. The correct install command is:

```bash
pip install -e .
```

or

```bash
pip install .
```

The implementation must use one of these forms. Using `pip install -r requirements.txt` alone will cause all `phasmid <subcommand>` invocations to fail with `command not found`, and the test categories in sections E and K will not run.

### Blocker 3: CLI `store` and `retrieve` commands require a physical camera and cannot run headlessly

Verified: both `phasmid store` and `phasmid retrieve` unconditionally call `gate.start()` followed by `_wait_for_camera_frame()` (see `cli.py` lines 450–453). If a camera frame is not available within the configured timeout, the command exits with "Camera feed did not become available." There is no `--no-camera` or `--dry-run` flag.

Consequence: **Category K ("Field Workflow Smoke Tests") cannot use the CLI `store`/`retrieve` commands in a headless SSH session.** Attempting to do so will always fail, even if the vault is otherwise configured correctly.

The correct approach for headless vault smoke tests is the programmatic API, as used in `scripts/bench_kdf.py`:

```python
from phasmid.vault_core import PhasmidVault
vault = PhasmidVault("/path/to/test/vault.bin", size_mb=1, state_dir="/path/to/test/.state")
vault.format_container()
vault.store("test-password", b"test-data", ["reference_dummy_matched"], filename="test.bin", mode="dummy")
result, _ = vault.retrieve("test-password", ["reference_dummy_matched"], mode="dummy")
assert result == b"test-data"
```

The `mode="dummy"` path in `PhasmidVault.store()` and `.retrieve()` bypasses the camera gate entirely. This is the only supported headless vault path.

The implementation must:
- not attempt to call `phasmid store` or `phasmid retrieve` in the harness;
- use the `PhasmidVault` API directly for all headless vault smoke tests;
- document that camera-required CLI flows are excluded from the automated harness;
- document that manual camera-attached testing follows the separate `docs/FIELD_TEST_PROCEDURE.md` checklist.

### Blocker 4: All CLI commands depend on the current working directory

Verified: `PhasmidVault("vault.bin")` in `cli.py` uses a relative path. `state_dir()` defaults to `".state"` (relative). `verify_state()` checks for `.state` relative to CWD.

Consequence: every `phasmid` CLI command must be run from `PHASMID_PI_REMOTE_DIR` on the Pi, or the commands will look for vault and state in the wrong location and produce misleading results.

The harness must prepend `cd "$PHASMID_PI_REMOTE_DIR" &&` to every remote CLI invocation, or configure `PHASMID_STATE_DIR` to an absolute path. Document which approach is used and ensure it is consistent across all test categories.

### Blocker 5: `PHASMID_TMPFS_STATE` must not be set in the test environment unless a tmpfs mount exists

The CLI (`phasmid.cli:main`) and WebUI (`web_server.py`) both call `require_volatile_state()` at startup. If `PHASMID_TMPFS_STATE` is set in the test environment but the directory does not exist on the Pi, every CLI and WebUI startup will raise `RuntimeError` immediately and all test categories will fail.

The harness must:

- not set `PHASMID_TMPFS_STATE` unless a tmpfs mount has been explicitly created;
- document that this variable must remain unset during field test runs unless the operator has provisioned the tmpfs mount;
- include a pre-flight check that warns if `PHASMID_TMPFS_STATE` is set and the path does not exist on the Pi before any test starts.

### Blocker 4: `phasmid doctor` behavior in non-interactive SSH sessions

The `doctor` command routes to non-TUI mode automatically when `sys.stdout.isatty()` returns `False`. This is correct behavior in SSH contexts and means `phasmid doctor` should print to stdout without a TUI when called non-interactively. However, to guarantee non-TUI output regardless of how the session is set up, use the explicit flag:

```bash
phasmid doctor --no-tui
```

The implementation must use `--no-tui` in all harness invocations of `doctor` to avoid any ambiguity about TTY detection.

## Required Files to Add

Add the following files:

- `scripts/pi_zero2w/run_remote_perf.sh` — top-level entry point; run from Mac
- `scripts/pi_zero2w/prepare_remote_env.sh` — syncs repository and creates remote `.venv`
- `scripts/pi_zero2w/collect_system_info.sh` — collects target hardware and OS metadata
- `scripts/pi_zero2w/run_local_perf.py` — runs on the Pi via SSH; measures timings and resource use
- `scripts/pi_zero2w/run_webui_probe.sh` — starts and probes the WebUI locally on the Pi
- `scripts/pi_zero2w/README.md` — quickstart guide for the harness
- `docs/PI_ZERO2W_FIELD_TEST.md` — full operator documentation

Note: `scripts/bench_kdf.py` and `scripts/bench_object_gate.py` already exist in the repository and provide useful baseline implementations for KDF and object-cue benchmarking. The new harness should call or adapt these scripts where appropriate rather than duplicating their logic. If the harness requires modified invocation paths, document the divergence.

If a different file layout is materially better, the implementation may adjust the layout, but it must explain the reason in the pull request and preserve the same top-level capabilities.

## Implementation Plan

The work should be implemented in staged order so another coding AI can deliver it incrementally and reviewably.

### Phase 1: Remote Harness Skeleton

Deliver the top-level command shape, environment validation, SSH wrapper behavior, log directory creation, and safe remote path handling.

Required outcomes:

- top-level command starts from macOS;
- required environment variables are validated before any remote mutation;
- remote commands are scoped to `PHASMID_PI_REMOTE_DIR`;
- local artifact directory is created under `release/pi-zero2w/`;
- failure reporting works even before full benchmarking exists.

### Phase 2: Repository Sync and Remote Environment Preparation

Deliver safe repository synchronization and remote Python environment creation.

Required outcomes:

- repository sync from Mac to Pi works via `rsync` or documented fallback;
- runtime artifacts are excluded from sync;
- remote `.venv` is created or reused safely;
- dependency installation logs are captured;
- clear failure diagnostics are emitted when dependency installation is not viable.

### Phase 3: Baseline System and Import Measurements

Deliver system inventory capture and import-time benchmarks.

Required outcomes:

- host and target metadata are captured in structured form;
- swap state is detected and recorded (warn if swap is enabled, since it affects KDF memory measurements);
- import times for required dependencies and selected Phasmid modules are measured;
- partial results are preserved when some imports fail.

### Phase 4: Runtime Viability, Performance Checks, and Coercion-Path Timing

Deliver CLI baseline, vault-path benchmarks, KDF timing, coercion-path timing consistency measurement, WebUI probe, and TUI viability checks.

Required outcomes:

- CLI baseline commands run and are timed;
- at least one bounded vault workflow runs successfully;
- KDF-path timing is measured through existing code paths where possible;
- coercion-path timing consistency is measured using `phasmid.observability_probe.ObservabilityProbe` on the Pi hardware (see Category N);
- the timing delta result and acceptance gate outcome are recorded in structured output;
- WebUI startup and shutdown are probed locally on the Pi;
- TUI viability is checked conservatively without requiring full automation.

### Phase 5: Field Workflow Smoke Tests, Observable Surface Review, and Monitoring

Deliver bounded workflow testing, observable information surface checks, and thermal/resource capture around major phases.

Required outcomes:

- non-destructive field workflow smoke tests run under a dedicated test directory;
- observable surfaces (CLI output, response headers, temporary directories) are reviewed for unintended leakage;
- temperature, memory, disk, and load measurements are captured before and after major phases;
- orphan process detection is included for WebUI-related phases;
- swap and storage configuration state is recorded.

### Phase 6: Reports, Documentation, and Reviewability

Deliver final structured artifacts and operator documentation.

Required outcomes:

- `perf-results.json` is written with complete schema coverage where possible;
- `perf-report.md` summarizes viability, bottlenecks, warnings, and next actions;
- timing-delta acceptance gate outcome is prominently reported;
- documentation explains setup, execution, cleanup, and limitations;
- camera cable hardware requirement is documented;
- report language remains conservative and avoids security overclaiming.

## Test Categories

The implementation must cover the following categories.

### A. SSH and Remote Sanity Checks

- verify SSH connectivity;
- verify hostname;
- verify OS release;
- verify CPU architecture (must be `aarch64` or `armv7l`);
- verify Python version;
- verify disk space;
- verify memory and swap;
- record whether swap is enabled (warn; swap affects KDF memory pressure measurements);
- verify current temperature if `vcgencmd` is available.

### B. Repository Synchronization

- sync current repository from Mac to Pi using `rsync` or `git`;
- exclude `.git` if `rsync` is used unless explicitly required;
- exclude local runtime artifacts such as `vault.bin`, `.state`, release output, caches, and virtual environments;
- avoid deleting unrelated remote files;
- keep remote operations scoped to the configured remote directory.

### C. Python Environment Viability

- create or reuse `.venv`;
- upgrade `pip` only if safe;
- install `requirements.txt`;
- capture installation time;
- capture install failure logs;
- detect whether heavy packages such as `opencv-python-headless` and `numpy` install from wheels or trigger local builds;
- record whether installation required compilation and estimate compilation time if so;
- fail with a clear diagnostic if dependency installation is not viable.

### D. Import-Time Baseline

Measure import time for important dependencies and Phasmid modules:

- `cryptography`
- `argon2`
- `numpy`
- `cv2`
- `fastapi`
- `uvicorn`
- `textual`
- selected `phasmid` package modules where applicable

### E. CLI Baseline

Measure:

- `phasmid --help` startup time;
- `phasmid doctor` runtime;
- `phasmid verify-state` if applicable;
- `phasmid audit` or non-TUI audit commands if available.

### F. Vault Operation Performance

Use small benchmark-only test files. The existing `scripts/bench_kdf.py` provides a reference implementation that can be adapted.

Measure:

- vault or container initialization time;
- store time;
- retrieve time;
- verification time if available;
- output size;
- maximum resident memory if `/usr/bin/time -v` is available.

Requirements:

- the benchmark must not weaken production defaults unless it is using an explicit opt-in benchmark-only profile;
- the benchmark path must prefer existing CLI or supported code paths over ad hoc crypto calls;
- generated containers must live under a dedicated remote test directory.

### G. Crypto/KDF Performance

Measure Argon2id KDF runtime on Pi hardware. The existing `scripts/bench_kdf.py` already exercises this path and should be called or adapted by the harness.

Measure:

- Argon2id or configured KDF runtime through existing Phasmid code paths where possible;
- AES-GCM operation time if accessible through existing code paths;
- memory pressure during KDF operations;
- wall time and CPU time separately (to detect SD card I/O effects).

Requirements:

- do not change cryptographic defaults for normal operation;
- if a benchmark-only override is necessary, it must be explicit, documented, opt-in, and not the default path.

### H. Object-Cue / ORB Performance

The existing `scripts/bench_object_gate.py` provides a reference implementation using `RecognitionBenchmark` and `ObjectGate`. The harness should call or adapt this script.

If existing APIs or fixtures are available, measure:

- image load time;
- ORB feature extraction time;
- matching time;
- memory usage;
- success or failure behavior with known sample images.

If no real fixture exists, the synthetic image path in `bench_object_gate.py` (procedurally generated textured frames) is acceptable for measuring compute cost. The implementation must not claim real recognition accuracy from synthetic image results.

### I. WebUI Viability

Measure:

- WebUI startup time;
- first HTTP response time to `http://127.0.0.1:<port>/`;
- repeated local HTTP response latency (at least 5 requests);
- memory usage while WebUI is running;
- shutdown behavior (graceful vs. forced);
- whether the WebUI can be started and stopped without leaving orphan processes (check with `pgrep uvicorn` or equivalent after shutdown).

Requirements:

- the WebUI must bind only to `127.0.0.1` on the Raspberry Pi;
- the harness must not make the WebUI network-facing by default;
- if the WebUI process does not exit cleanly within a reasonable timeout, kill it and record this as a warning.

### J. TUI Viability

Because automated TUI testing may be difficult, require:

- import or startup viability check;
- non-interactive smoke test where possible;
- documentation of limitations if full TUI automation is not practical.

### K. Field Workflow Smoke Tests

Run a minimal non-destructive workflow under a dedicated test directory (e.g., `PHASMID_PI_REMOTE_DIR/_pi_field_test/`).

**Important**: the CLI `phasmid store` and `phasmid retrieve` commands require a physical camera feed and cannot run in a headless SSH session. All store and retrieve operations in this category must use the `PhasmidVault` Python API directly with `mode="dummy"`, as `scripts/bench_kdf.py` demonstrates. Do not attempt to call `phasmid store` or `phasmid retrieve` from the harness.

Steps:

- initialize a test container using `PhasmidVault.format_container()`;
- store a small synthetic byte payload using `PhasmidVault.store(..., mode="dummy")`;
- retrieve it using `PhasmidVault.retrieve(..., mode="dummy")` and verify the round-trip;
- run `phasmid doctor --no-tui` from `PHASMID_PI_REMOTE_DIR` (CWD matters);
- run `phasmid verify-state` from `PHASMID_PI_REMOTE_DIR` (CWD matters);
- run metadata review workflow if available;
- do not attempt restricted or recovery CLI flows in the automated harness.

All test artifacts must remain inside the dedicated test directory and must not modify production state.

### L. Thermal and Resource Monitoring

Collect before and after each major phase:

- CPU temperature via `/sys/class/thermal/thermal_zone0/temp` or `vcgencmd measure_temp`;
- memory usage (`free -m`);
- disk usage of the remote working directory;
- system load average;
- optional throttling status via `vcgencmd get_throttled` if available (non-zero value indicates voltage or thermal throttling; record the raw hex value and decode the flags in the report).

### M. Failure Mode Tests

Verify:

- missing SSH variables fail safely and print the missing variable names;
- unreachable host fails clearly within a defined timeout;
- missing Python fails clearly;
- dependency install failure is reported with the failing package and log excerpt;
- WebUI startup failure is reported;
- result files are still created with partial-failure status where possible.

### N. Coercion-Path Timing Consistency (Required)

This category is required. It tests Phasmid's central security property on actual Pi hardware.

The `phasmid.observability_probe.ObservabilityProbe` class exists in the codebase and measures timing across `RecoveryPath.NORMAL`, `RecoveryPath.FAILED`, and `RecoveryPath.RESTRICTED` code paths. Run it on the Pi via the remote harness.

Invocation reference (adapt as needed for the harness):

```python
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
```

**Acceptance gate**: the post-KDF timing delta between the FAILED and RESTRICTED paths must be less than 5% of Argon2id wall time. If the delta exceeds this threshold, the test must record a `FAIL` in the JSON output and include a prominent warning in the Markdown report. The issue must not be closed if this gate fails without a documented risk-acceptance note.

Record:

- `max_timing_delta_ms` for FAILED vs. RESTRICTED;
- wall time for the full Argon2id KDF round;
- whether the acceptance gate passed or failed;
- any paths with filesystem writes as identified by `report.paths_with_filesystem_writes()`.

If the gate passes on Pi hardware, record the result in `perf-results.json` under `coercion_path_timing`. Do not interpret gate passage as proof of security; record it as a measurement outcome.

### O. Observable Information Surface Review

Because Phasmid is coercion-aware storage, observable side channels must be reviewed as part of field testing. This category defines a structured checklist that the harness should automate where possible and document as manual steps where full automation is not practical.

Review the following surfaces during or after workflow smoke tests:

- **CLI output**: verify that failure responses do not emit state-path details, key material hints, or distinguish FAILED from RESTRICTED in a message-text-observable way;
- **HTTP response headers**: verify that the WebUI does not include server fingerprinting, session-state headers, or verbose error details in normal and failed responses;
- **Temporary directories**: verify that `/tmp` and the upload directory do not retain files after workflow operations complete;
- **Systemd journal** (if applicable): verify that journal output does not include passphrase fragments, key derivation inputs, or path-revealing debug messages;
- **Shell history**: note that `~/.bash_history` or `~/.zsh_history` may capture passphrase arguments if the user invokes commands interactively; document this as a limitation and recommend `HISTFILE=/dev/null` during sensitive sessions.

The harness must emit a checklist section in the Markdown report listing each surface and its automated or manual review result.

### P. Storage and Swap Configuration Verification

These checks verify that the Pi's storage configuration matches deployment requirements.

Verify and record:

- whether swap is enabled or disabled (`swapon --show` or `cat /proc/swaps`);
- swap size if enabled;
- whether `/tmp` or upload directories are backed by `tmpfs` (`findmnt -T /tmp`);
- available disk space on the storage partition;
- SD card media type if detectable.

If swap is enabled, emit a warning in the report. Swap increases the risk that Argon2id working memory is paged to SD card, which affects both KDF timing measurements and potential data-remanence properties. Do not fail the test run solely because swap is enabled, but ensure the warning is prominent.

## Required Output Artifacts

The implementation must write results to:

- `release/pi-zero2w/perf-results.json`
- `release/pi-zero2w/perf-report.md`
- `release/pi-zero2w/install.log`
- `release/pi-zero2w/run.log`

`perf-results.json` must include structured fields for:

- `timestamp`
- `host_info`
- `target_info`
- `git_commit`
- `test_phase_results`
- `timings`
- `memory`
- `temperature`
- `swap_enabled`
- `coercion_path_timing` (required; include `max_timing_delta_ms`, `kdf_wall_time_ms`, `gate_passed`, `n_rounds`)
- `observable_surface_review`
- `failures`
- `warnings`
- `overall_status`

`perf-report.md` must include:

- executive technical summary;
- target hardware summary including swap state and storage configuration;
- dependency installation result;
- performance table;
- coercion-path timing consistency result and acceptance gate outcome (prominent section);
- observable surface review checklist;
- failure and warning section;
- recommended next actions;
- clear statement that results are hardware-specific and do not prove security.

Partial failure handling requirements:

- if a phase fails, prior completed results must still be preserved;
- report files must indicate which phases were skipped, failed, or incomplete;
- missing metrics must be explicit rather than omitted silently.

## Safety Requirements

The implementation must require:

- no destructive commands outside `PHASMID_PI_REMOTE_DIR`;
- no `sudo` unless explicitly documented and justified;
- no secrets written to repository files;
- no weakening of production cryptographic settings;
- no claims of field-proven security from benchmark success;
- benchmark-only shortcuts must be opt-in and clearly labeled;
- generated test containers and temporary files must be placed under a dedicated test directory (e.g., `PHASMID_PI_REMOTE_DIR/_pi_field_test/`);
- no remote delete behavior that could remove unrelated files;
- no change to WebUI default binding semantics;
- the coercion-path timing test must use production KDF parameters and must not substitute reduced parameters to make the gate pass faster.

## Documentation Requirements

The implementation must include documentation explaining:

- how to prepare Raspberry Pi Zero 2 W;
- how to enable SSH for testing (and that SSH may be disabled after provisioning in appliance use);
- required OS packages;
- camera hardware requirements including the 22-pin-to-15-pin cable requirement for Pi Zero 2 W;
- how to set environment variables;
- how to set `PHASMID_PI_SSH_KEY` if key-based authentication is required;
- how to run the remote test;
- how to read the results;
- how to interpret the coercion-path timing acceptance gate result;
- known limitations;
- troubleshooting dependency installation failures;
- troubleshooting `opencv` and `numpy` installation problems;
- troubleshooting camera not detected or wrong cable type;
- how to clean up only the dedicated test directory;
- SD card and flash media limitations for overwrite-based key destruction.

Documentation must also:

- distinguish development-host responsibilities from target-device responsibilities;
- state clearly that target-hardware measurements are hardware-specific;
- state clearly that successful benchmarks do not prove security;
- state clearly that timing-gate passage on one unit does not generalize to all deployments;
- keep network posture language aligned with local-only defaults and localhost binding expectations.

## Suggested Command Shape

```bash
export PHASMID_PI_HOST=phasmid-pi.local
export PHASMID_PI_USER=pi
export PHASMID_PI_REMOTE_DIR=/home/pi/Phasmid
export PHASMID_PI_SSH_PORT=22
export PHASMID_PI_SSH_KEY=~/.ssh/id_ed25519_pi  # optional; uses ssh-agent if unset

./scripts/pi_zero2w/run_remote_perf.sh
```

## Acceptance Criteria

- A Mac user can run one top-level command to start the remote test.
- Missing configuration fails with clear error messages.
- The harness checks that `uname -m` returns `aarch64` on the Pi and fails with a clear message if 32-bit OS is detected.
- The script can prepare the remote Python environment without source compilation on 64-bit Raspberry Pi OS.
- The script installs Phasmid with `pip install -e .` so that the `phasmid` CLI entry point exists.
- `PHASMID_TMPFS_STATE` is not set in the test environment unless explicitly required, and a pre-flight check warns if it is set without the directory existing.
- All `phasmid doctor` and `phasmid verify-state` invocations prepend `cd "$PHASMID_PI_REMOTE_DIR" &&` or set an absolute `PHASMID_STATE_DIR`.
- All `phasmid doctor` invocations use `--no-tui`.
- The harness does not call `phasmid store` or `phasmid retrieve`; vault smoke tests use the `PhasmidVault` Python API with `mode="dummy"`.
- The script can run at least install viability, system info, CLI baseline, and one vault operation test.
- The coercion-path timing consistency test runs and records a structured result.
- Results are copied back to the Mac.
- JSON and Markdown reports are generated.
- Partial failures are represented in the report rather than silently ignored.
- Local unit tests still pass where practical.
- The implementation does not change Phasmid's security semantics.
- The implementation does not require Codex, VS Code Remote SSH, Docker, or a GUI on the Pi.
- The implementation keeps WebUI behavior local-only by default.
- The report clearly states whether the coercion-path timing acceptance gate passed or failed.
- Swap state and storage configuration are recorded.

## Reviewer Checklist

- Does this avoid running heavy tooling on the Pi?
- Does this avoid destructive remote operations?
- Does it measure the actual bottlenecks on Raspberry Pi Zero 2 W class hardware?
- Does it check `uname -m` and refuse to run on 32-bit Raspberry Pi OS?
- Does it install with `pip install -e .` so the `phasmid` CLI entry point exists?
- Does it guard against `PHASMID_TMPFS_STATE` being set without a matching mount?
- Does it use `--no-tui` for `phasmid doctor` in all harness calls?
- Does all remote CLI execution prepend `cd "$PHASMID_PI_REMOTE_DIR"` or set an absolute `PHASMID_STATE_DIR`?
- Does it avoid `phasmid store` and `phasmid retrieve` entirely, using `PhasmidVault` with `mode="dummy"` instead?
- Does it run the coercion-path timing consistency test on Pi hardware using production KDF parameters?
- Does the report clearly state the timing delta and acceptance gate result?
- Does it distinguish benchmark viability from security validation?
- Does it keep Phasmid's claims conservative?
- Does it preserve local-only and localhost-default behavior?
- Does the report help decide whether Pi Zero 2 W is acceptable as target hardware?
- Does it record swap state and warn appropriately?
- Does it review observable information surfaces?
- Does it document the camera cable hardware requirement?

## Implementation Notes for the Coding AI

- Check `uname -m` on the Pi first. If it returns `armv7l`, fail immediately with a clear message that 64-bit Raspberry Pi OS is required.
- On 64-bit aarch64, `numpy==2.2.6` installs via `manylinux_2_17_aarch64` wheel without source compilation. Do not attempt workarounds on 64-bit unless the install actually fails.
- Do not call `phasmid store` or `phasmid retrieve` in the harness. Use `PhasmidVault` with `mode="dummy"` for all headless vault operations.
- Install Phasmid with `pip install -e .`, not `pip install -r requirements.txt`. The latter does not create the `phasmid` CLI entry point.
- Do not set `PHASMID_TMPFS_STATE` in the test harness environment unless a tmpfs mount is provisioned. Check for this variable in the pre-flight step and warn if it is set without the path existing.
- Use `phasmid doctor --no-tui` in all non-interactive contexts.
- Prefer existing supported Phasmid entry points and code paths over one-off benchmark code.
- The existing `scripts/bench_kdf.py` and `scripts/bench_object_gate.py` already implement KDF and ORB benchmarking. Adapt or call them rather than rewriting the same logic.
- The `phasmid.observability_probe.ObservabilityProbe` class is the canonical tool for coercion-path timing measurement. Use it directly.
- Keep the harness reviewable: simple shell entry points, explicit logging, explicit exit statuses, explicit JSON schema.
- Use conservative remote shell practices: quote paths, fail early, and avoid assumptions about optional packages.
- If some categories cannot be automated on the first pass, mark them clearly as `skipped` or `not_automated` and document why.
- Do not combine this work with unrelated cryptographic, UI wording, or deployment-semantics changes.
- The timing-delta acceptance gate is not a performance optimization target. Do not tune KDF parameters to make the gate pass.
