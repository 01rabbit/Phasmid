# LUKS Layer

## Overview

Phasmid can operate on top of an optional LUKS2-backed storage layer.
This layer is intended to reduce offline filesystem exposure of the local container
and local state paths by encrypting the underlying block storage.
It does not replace Phasmid's application-layer controls, and it does not replace
full-disk encryption or trusted-platform controls.
LUKS is an additional storage boundary, not a complete host-compromise defense.

## Threat Model Delta

| Threat Surface | Without LUKS Layer | With LUKS Layer |
|---|---|---|
| Offline image of medium | `vault.bin` and local state paths are visible as files | Underlying contents are encrypted until mapped and mounted |
| Access-key residue risk | Depends on state location and host posture | Still depends on host posture; encrypted-at-rest block layer adds friction |
| Brick / restricted clear effect | Key-path invalidation + best-effort overwrite | Key-path invalidation + optional LUKS key-slot erase path (best-effort) |
| Host compromise while running | Out of scope | Out of scope (unchanged) |

## Known Limits

- Live memory capture while the container is mounted bypasses LUKS protection.
- The LUKS header proves that encrypted storage was used. This differs from VeraCrypt hidden volumes; LUKS does not provide plausible deniability about the container's existence.
- Restricted clear (`luksErase`) is best-effort. Physical recovery of erased NAND cells is outside the scope of this software.
- Disabling swap reduces residue risk but does not eliminate it from RAM while the system is running.
- This layer has not been independently audited.

Additional operational limits:

- Malware, keyloggers, and compromised kernels are not mitigated by this layer.
- Storage-controller behavior, snapshots, and wear leveling can preserve older blocks.
- Results are hardware-specific; validation on one Pi setup does not generalize automatically.

## Deployment Modes

### Mode A: File Container

- LUKS device stored as a regular file (for example `luks.img`).
- Suitable for prototype and evaluation workflows where repartitioning is undesirable.
- Additional loopback overhead may affect throughput and startup timing.

### Mode B: Partition

- LUKS mapped directly on a dedicated block partition.
- Better fit for appliance-style deployment with clearer storage boundaries.
- Requires partition planning and provisioning discipline.

## Setup Procedure

Reference setup script: `scripts/setup_luks_appliance.sh` (when provided in deployment workflow).

Minimum setup expectations:

1. provision LUKS device or partition;
2. configure wrapper path and mount point;
3. configure restricted sudoers entry;
4. validate mount/unmount status path before operator use;
5. run Pi field-test harness and record artifacts.

## Sudoers Configuration

Minimum-privilege sudoers entry:

```text
phasmid ALL=(root) NOPASSWD: /usr/local/bin/phasmid-luks-mount
```

Do not use wildcard sudo rules for this path.

## Operating Procedure

### Mount

1. prepare key material in `/run/phasmid/luks.key` (tmpfs-backed path preferred);
2. invoke wrapper mount command via restricted sudo path;
3. verify mapped device and mount point;
4. set runtime state path to the mounted location for operator flows.

User-facing status should remain neutral:
- `local container opened`

### Unmount

1. terminate dependent operations;
2. unmount filesystem and close mapper;
3. clear runtime state path overrides where applicable.

User-facing status:
- `local container closed`

### Restricted Clear

1. wipe local key-store artifact (best-effort);
2. invoke wrapper `brick` path to trigger LUKS erase behavior (best-effort);
3. report only neutral local-access-path language.

User-facing status:
- `local access path cleared (best-effort)`

## Iter-Time Calibration

`PHASMID_LUKS_ITER_TIME_MS=2000` is a Pi Zero 2 W target value for evaluation,
not a universal default guarantee. Field calibration on target hardware is required
before freezing deployment recommendations.
