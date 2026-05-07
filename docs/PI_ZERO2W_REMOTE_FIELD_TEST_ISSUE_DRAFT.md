# Title

Add Raspberry Pi Zero 2 W Remote Field Test Harness

## Background

Phasmid must be validated on actual constrained target hardware before stronger operational claims are made. Raspberry Pi Zero 2 W is an important target because it reflects the project's expected low-power appliance class, but it has limited CPU throughput, memory capacity, storage I/O, and thermal headroom.

The current development workflow runs on macOS with Codex and editor tooling available locally. That workflow does not translate directly to Raspberry Pi Zero 2 W. The target device should be treated as a remote SSH execution target, not as a full development workstation. Heavy interactive tooling, editor-dependent workflows, container-first workflows, and GUI assumptions are not appropriate for this target.

The correct design for this work is therefore a Mac-controlled remote SSH field-test harness that can prepare the target, run bounded validation tasks, collect structured measurements, and copy results back to the Mac for review. This issue exists to define that harness and its documentation, not to change Phasmid security semantics.

## Objective

Add scripts and documentation that allow a developer on macOS to run a repeatable remote field-evaluation workflow against a Raspberry Pi Zero 2 W over SSH.

The implementation should allow a developer on macOS to:

- synchronize the repository to the Raspberry Pi Zero 2 W;
- prepare a Python virtual environment on the Raspberry Pi;
- install dependencies;
- run install viability checks;
- run CLI, crypto, vault, object-cue, WebUI, and field workflow tests;
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

## Target Environment

Host:

- macOS
- Git repository checked out locally
- SSH client available
- `rsync` available, or a documented fallback path if `rsync` is missing

Target:

- Raspberry Pi Zero 2 W
- Raspberry Pi OS Lite
- Python 3 available on the device
- SSH enabled
- limited CPU and memory capacity
- limited storage I/O and thermal headroom
- optional camera and object-cue test assets if available

## Required Environment Variables

The top-level harness must require these variables:

- `PHASMID_PI_HOST`
- `PHASMID_PI_USER`
- `PHASMID_PI_REMOTE_DIR`
- `PHASMID_PI_SSH_PORT`

Requirements:

- all required variables must be validated before remote work begins;
- missing variables must fail safely with clear, single-purpose error messages;
- empty values must be treated as invalid;
- the harness must print the exact variable names that are missing;
- the harness must not continue with guessed defaults for host, user, or remote directory.

## Required Files to Add

Add the following files:

- `scripts/pi_zero2w/run_remote_perf.sh`
- `scripts/pi_zero2w/prepare_remote_env.sh`
- `scripts/pi_zero2w/collect_system_info.sh`
- `scripts/pi_zero2w/run_local_perf.py`
- `scripts/pi_zero2w/run_webui_probe.sh`
- `scripts/pi_zero2w/README.md`
- `docs/PI_ZERO2W_FIELD_TEST.md`

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
- import times for required dependencies and selected Phasmid modules are measured;
- partial results are preserved when some imports fail.

### Phase 4: Runtime Viability and Performance Checks

Deliver CLI baseline, vault-path benchmarks, KDF timing, WebUI probe, and TUI viability checks.

Required outcomes:

- CLI baseline commands run and are timed;
- at least one bounded vault workflow runs successfully;
- KDF-path timing is measured through existing code paths where possible;
- WebUI startup and shutdown are probed locally on the Pi;
- TUI viability is checked conservatively without requiring full automation.

### Phase 5: Field Workflow Smoke Tests and Monitoring

Deliver bounded workflow testing and thermal/resource capture around major phases.

Required outcomes:

- non-destructive field workflow smoke tests run under a dedicated test directory;
- temperature, memory, disk, and load measurements are captured before and after major phases;
- orphan process detection is included for WebUI-related phases.

### Phase 6: Reports, Documentation, and Reviewability

Deliver final structured artifacts and operator documentation.

Required outcomes:

- `perf-results.json` is written with complete schema coverage where possible;
- `perf-report.md` summarizes viability, bottlenecks, warnings, and next actions;
- documentation explains setup, execution, cleanup, and limitations;
- report language remains conservative and avoids security overclaiming.

## Test Categories

The implementation must cover the following categories.

### A. SSH and Remote Sanity Checks

- verify SSH connectivity;
- verify hostname;
- verify OS release;
- verify CPU architecture;
- verify Python version;
- verify disk space;
- verify memory and swap;
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

Use small benchmark-only test files.

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

Measure:

- Argon2id or configured KDF runtime through existing Phasmid code paths where possible;
- AES-GCM operation time if accessible through existing code paths;
- memory pressure during KDF operations.

Requirements:

- do not change cryptographic defaults for normal operation;
- if a benchmark-only override is necessary, it must be explicit, documented, opt-in, and not the default path.

### H. Object-Cue / ORB Performance

If existing APIs or fixtures are available, measure:

- image load time;
- ORB feature extraction time;
- matching time;
- memory usage;
- success or failure behavior with known sample images.

If no fixture exists, require the implementation to provide a minimal synthetic or documented test path without claiming real biometric or object-recognition validation.

### I. WebUI Viability

Measure:

- WebUI startup time;
- first HTTP response time;
- repeated local HTTP response latency;
- memory usage while WebUI is running;
- shutdown behavior;
- whether the WebUI can be started and stopped without leaving orphan processes.

Requirements:

- the WebUI should bind only to localhost on the Raspberry Pi unless project documentation already defines a different bounded appliance path;
- the harness must not make the WebUI network-facing by default.

### J. TUI Viability

Because automated TUI testing may be difficult, require:

- import or startup viability check;
- non-interactive smoke test where possible;
- documentation of limitations if full TUI automation is not practical.

### K. Field Workflow Smoke Tests

Run a minimal non-destructive workflow:

- create test container;
- add small test entry;
- retrieve test entry;
- run doctor or equivalent check commands;
- run metadata review workflow if available;
- run restricted or recovery behavior only if it can be tested safely and reversibly.

### L. Thermal and Resource Monitoring

Collect:

- CPU temperature before and after major phases;
- memory before and after major phases;
- disk usage;
- load average;
- optional throttling status if `vcgencmd get_throttled` is available.

### M. Failure Mode Tests

Verify:

- missing SSH variables fail safely;
- unreachable host fails clearly;
- missing Python fails clearly;
- dependency install failure is reported;
- WebUI startup failure is reported;
- result files are still created with partial-failure status where possible.

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
- `failures`
- `warnings`
- `overall_status`

`perf-report.md` must include:

- executive technical summary;
- target hardware summary;
- dependency installation result;
- performance table;
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
- generated test containers and temporary files must be placed under a dedicated test directory;
- no remote delete behavior that could remove unrelated files;
- no change to WebUI default binding semantics.

## Documentation Requirements

The implementation must include documentation explaining:

- how to prepare Raspberry Pi Zero 2 W;
- how to enable SSH;
- required OS packages;
- how to set environment variables;
- how to run the remote test;
- how to read the results;
- known limitations;
- troubleshooting dependency installation failures;
- troubleshooting `opencv` and `numpy` installation problems;
- how to clean up only the dedicated test directory.

Documentation must also:

- distinguish development-host responsibilities from target-device responsibilities;
- state clearly that target-hardware measurements are hardware-specific;
- state clearly that successful benchmarks do not prove security;
- keep network posture language aligned with local-only defaults and localhost binding expectations.

## Suggested Command Shape

```bash
export PHASMID_PI_HOST=phasmid-pi.local
export PHASMID_PI_USER=pi
export PHASMID_PI_REMOTE_DIR=/home/pi/Phasmid
export PHASMID_PI_SSH_PORT=22

./scripts/pi_zero2w/run_remote_perf.sh
```

## Acceptance Criteria

- A Mac user can run one top-level command to start the remote test.
- Missing configuration fails with clear error messages.
- The script can prepare the remote Python environment.
- The script can run at least install viability, system info, CLI baseline, and one vault operation test.
- Results are copied back to the Mac.
- JSON and Markdown reports are generated.
- Partial failures are represented in the report rather than silently ignored.
- Local unit tests still pass where practical.
- The implementation does not change Phasmid's security semantics.
- The implementation does not require Codex, VS Code Remote SSH, Docker, or a GUI on the Pi.
- The implementation keeps WebUI behavior local-only by default.

## Reviewer Checklist

- Does this avoid running heavy tooling on the Pi?
- Does this avoid destructive remote operations?
- Does it measure the actual bottlenecks on Raspberry Pi Zero 2 W class hardware?
- Does it distinguish benchmark viability from security validation?
- Does it keep Phasmid's claims conservative?
- Does it preserve local-only and localhost-default behavior?
- Does the report help decide whether Pi Zero 2 W is acceptable as target hardware?

## Implementation Notes for the Coding AI

- Prefer existing supported Phasmid entry points and code paths over one-off benchmark code.
- Keep the harness reviewable: simple shell entry points, explicit logging, explicit exit statuses, explicit JSON schema.
- Use conservative remote shell practices: quote paths, fail early, and avoid assumptions about optional packages.
- If some categories cannot be automated on the first pass, mark them clearly as `skipped` or `not_automated` and document why.
- Do not combine this work with unrelated cryptographic, UI wording, or deployment-semantics changes.
