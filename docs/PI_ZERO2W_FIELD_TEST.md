# Phasmid Pi Zero 2W Field Test — Operator Guide

This document covers the full automated remote field test harness for
Raspberry Pi Zero 2 W. For manual field evaluation (coercion scenarios,
power-loss fault testing, capture-visible surface review), see
`docs/FIELD_TEST_PROCEDURE.md`.

## Overview

The harness runs from macOS and controls the Pi via SSH. It does not require
VS Code Remote SSH, Docker, a GUI, or Codex on the Pi. All test phases
that are safe to automate are automated. Phases that require physical
hardware interaction (camera-based store/retrieve, power-loss tests) are
documented as manual steps in `docs/FIELD_TEST_PROCEDURE.md`.

## Hardware Requirements

| Item | Requirement |
|---|---|
| Board | Raspberry Pi Zero 2 W |
| OS | Raspberry Pi OS Lite **64-bit (aarch64) — mandatory** |
| RAM | 512 MB (built-in) |
| Storage | microSD, class 10 or better |
| Network | SSH reachable from Mac (Wi-Fi or USB Ethernet gadget) |
| Camera | Optional — only needed for manual store/retrieve tests |

**Camera cable note**: Pi Zero 2 W uses a 22-pin camera connector.
The standard 15-pin camera cable is physically incompatible. A
22-pin-to-15-pin Pi Zero camera adapter cable is required. This is the
most common field mistake that prevents camera tests from running.

## Pi Preparation

### 1. Flash 64-bit OS

Use Raspberry Pi Imager. Select:
- OS: Raspberry Pi OS Lite (64-bit)
- Enable SSH in the imager settings
- Set hostname, username, and password

Verify after boot: `uname -m` must return `aarch64`.

### 2. Install required OS packages

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip libopenblas-dev
```

`libopenblas-dev` is required for numpy's BLAS routines. Without it,
numpy may import but produce warnings or fail on matrix operations.

### 3. Configure SSH key access (recommended)

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub pi@phasmid-pi.local
```

Test: `ssh pi@phasmid-pi.local "echo ok"`

### 4. Swap recommendation

For production appliance use, swap should be disabled:

```bash
sudo systemctl disable dphys-swapfile
sudo systemctl stop dphys-swapfile
```

The test harness warns if swap is enabled but does not fail because of it.
KDF timing measurements are more meaningful with swap disabled.

## Environment Variables

Set on the Mac before running the harness:

| Variable | Required | Description |
|---|---|---|
| `PHASMID_PI_HOST` | Yes | Hostname or IP of the Pi |
| `PHASMID_PI_USER` | Yes | SSH username on the Pi |
| `PHASMID_PI_REMOTE_DIR` | Yes | Absolute path on the Pi (e.g. `/home/pi/Phasmid`) |
| `PHASMID_PI_SSH_PORT` | Yes | SSH port (typically `22`) |
| `PHASMID_PI_SSH_KEY` | No | Path to SSH private key; uses ssh-agent if unset |

**`PHASMID_TMPFS_STATE` must NOT be set** during test runs.
If it is set in the shell but the corresponding directory does not exist on
the Pi, both the CLI and the WebUI will exit immediately with `RuntimeError`.
The harness warns if it detects this variable and strips it from all remote
commands.

## Running the Test

```bash
export PHASMID_PI_HOST=phasmid-pi.local
export PHASMID_PI_USER=pi
export PHASMID_PI_REMOTE_DIR=/home/pi/Phasmid
export PHASMID_PI_SSH_PORT=22

./scripts/pi_zero2w/run_remote_perf.sh
```

Typical run time: 10–30 minutes depending on install time and KDF rounds.

## Test Phases

| Phase | Description | Automated |
|---|---|---|
| A | SSH sanity + architecture check | Yes |
| B | System info (CPU, memory, swap, temp) | Yes |
| C | Repository sync + `pip install -e .` | Yes |
| D | Import-time baseline | Yes |
| E | CLI baseline (`--help`, `doctor --no-tui`, `verify-state`) | Yes |
| F | Vault round-trip (`PhasmidVault` API, headless) | Yes |
| G | KDF timing (Argon2id wall time) | Yes |
| H | Object-gate / ORB (synthetic frames) | Yes |
| I | WebUI startup, latency, shutdown | Yes |
| N | Coercion-path timing consistency (acceptance gate) | Yes |
| K* | Store/retrieve with camera | Manual — see FIELD_TEST_PROCEDURE.md |
| P* | Power-loss fault testing | Manual — see FIELD_TEST_PROCEDURE.md |

*Phases K and P require physical hardware interaction and are not automated.

## Implementation Constraints (do not change without Issue review)

These constraints are enforced in the scripts and must not be removed:

1. **`pip install -e .` is required** — not `pip install -r requirements.txt`.
   Only `pip install -e .` creates the `phasmid` CLI entry point.

2. **`phasmid store` and `phasmid retrieve` are never called** in the harness.
   Both commands require a live camera feed and fail immediately in headless SSH
   sessions. All vault smoke tests use `PhasmidVault` with `mode="dummy"`.

3. **All CLI commands run with `cd $PHASMID_PI_REMOTE_DIR`** as CWD.
   `vault.bin` and `.state/` are relative paths in the CLI; running from the
   wrong directory produces misleading results.

4. **`phasmid doctor` always uses `--no-tui`** in harness invocations.

5. **`PHASMID_TMPFS_STATE` is stripped from all remote commands** by the
   harness to prevent startup failures.

6. **64-bit OS is required.** The harness checks `uname -m` and fails
   immediately if it returns `armv7l`.

## Reading the Results

Results are written to `release/pi-zero2w/` on the Mac after the run.

### `perf-results.json`

Key fields to review:

```
overall_status              "pass" or "fail"
swap_enabled                true = warn; KDF measurements may be affected
coercion_path_timing
  gate_passed               true = delta < 5% of Argon2id wall time
  max_timing_delta_ms       actual measured delta between FAILED/RESTRICTED paths
  kdf_wall_time_ms          Argon2id wall time on this hardware
vault_operations.roundtrip_ok  true = store → retrieve produced identical bytes
failures[]                  list of phases that failed with error messages
warnings[]                  non-fatal issues (swap, temperature, etc.)
```

### Coercion-Path Timing Acceptance Gate

Phasmid's central security property is that the FAILED and RESTRICTED code
paths are not distinguishable by timing observation.

**Gate**: `max_timing_delta_ms < 5% of kdf_wall_time_ms`

If `gate_passed` is `false`:
- The FAILED and RESTRICTED paths had timing differences that may be
  observable by a coercion attacker.
- This finding must be documented before field use.
- Do not close the related issue without a risk-acceptance note.

Gate passage on one unit does not generalize to all hardware units,
OS versions, or load conditions. It is a measurement, not a proof.

### `run.log`

Full chronological log of the run including SSH output, timing, and
any errors. Review this first when a phase fails.

### `install.log`

Output of `pip install -e .` on the Pi. Review this if:
- install time was unexpectedly long (possible source build)
- a dependency failed to install
- `overall_status` is `fail` and `prepare_env` phase is listed as `fail`

## Known Limitations

- **Camera-based flows are not automated.** `phasmid store` and
  `phasmid retrieve` require a camera. Manual testing follows
  `docs/FIELD_TEST_PROCEDURE.md`.

- **Power-loss fault testing is manual.** SD card write behavior under
  sudden power loss cannot be tested safely by remote SSH commands.

- **SD card wear leveling.** Overwrite-based key destruction on SD cards
  is best-effort only. Wear leveling may retain copies of overwritten data.
  This is documented in `docs/RPI_ZERO_APPLIANCE_DEPLOYMENT.md`.

- **Timing measurements are hardware-specific.** Results from one Pi Zero 2W
  unit may not generalize to other units, SD card brands, or ambient
  temperatures.

- **Benchmark success does not prove security.** A passing timing gate
  indicates that on this hardware, under test conditions, the timing delta
  was below the threshold. It does not constitute a security proof.

## Cleanup

Remove only the dedicated test directory on the Pi:

```bash
ssh $PHASMID_PI_USER@$PHASMID_PI_HOST \
    "rm -rf $PHASMID_PI_REMOTE_DIR/_pi_field_test"
```

This removes test containers, state files, and result JSON from the Pi.
It does not affect the synced repository or `.venv`.

## Troubleshooting

### "Target reports architecture 'armv7l'"

Flash 64-bit Raspberry Pi OS Lite. 32-bit (armv7l) lacks pre-built wheels
for `numpy` and other dependencies. Source compilation on Pi Zero 2W is
impractical (30–60+ minutes, possible OOM).

### "phasmid CLI not found after install"

Check `release/pi-zero2w/install.log`. A dependency may have failed to
build. Common fixes:

```bash
# On the Pi:
sudo apt-get install -y python3-dev build-essential libffi-dev libssl-dev
```

Then re-run the harness.

### opencv / numpy build triggered (slow install)

If a source build is triggered on 64-bit Pi OS, it may indicate that pip
could not find a `manylinux_2_17_aarch64` wheel. Possible causes:
- Network issue reaching PyPI during install
- Version pinned in `requirements.txt` has no wheel for the detected Python

Check the Python version on the Pi: `python3 --version`. Wheels for
`numpy==2.2.6` require Python 3.10–3.13 on aarch64.

### WebUI probe fails immediately

Check `release/pi-zero2w/webui.log`. Common causes:
- Port 8001 already in use: `sudo lsof -i :8001` on the Pi
- Missing `_pi_field_test/.state` directory (the harness creates this; check
  if prepare_env phase ran successfully)

### Timing gate fails (`gate_passed: false`)

Record the `max_timing_delta_ms` and `kdf_wall_time_ms` values. Factors
that can cause gate failure:
- SD card I/O spikes during Argon2id
- Background system processes on the Pi during measurement
- Swap activity if swap is enabled

Run the harness again with fewer background processes and swap disabled.
If the gate consistently fails, document it as a hardware-specific finding
and open a follow-up issue.
