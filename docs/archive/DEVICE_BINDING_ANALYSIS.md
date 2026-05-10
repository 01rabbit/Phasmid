# Device Binding Input Evaluation

## Purpose

This document evaluates whether device-specific inputs — such as the Raspberry Pi CPU
serial, machine-id, or SD card CID — should be mixed into Phasmid's key derivation
pipeline.

Device binding reduces portability: a container bound to a specific board cannot be
recovered on a different board without explicit migration steps.  This is a tradeoff,
not a free hardening upgrade.

**Device binding inputs are not high-entropy cryptographic material.**  The CPU serial
and hardware revision are semi-public values: they appear in `/proc/cpuinfo` and may
be recoverable by an attacker with physical access to the board.  Their value lies in
*device-tying*, not in providing additional entropy.

---

## Current State

`HardwareBindingProvider` in `src/phasmid/kdf_providers.py` already reads
`/proc/cpuinfo` for `Serial`, `Hardware`, and `Revision` lines on Linux.  These are
concatenated and passed as the Argon2id key-material input alongside any configured
`PHASMID_HARDWARE_SECRET`, `PHASMID_HARDWARE_SECRET_FILE`, or prompted value.

The binding is **active by default on Raspberry Pi** (where `/proc/cpuinfo` includes
`Serial`) and silently absent on platforms that do not expose it (macOS, x86 Linux
without board serial).

`hardware_binding_status()` reports whether device binding is available and whether
external binding is also configured; this appears in the Doctor page.

---

## Evaluated Binding Inputs

### 1. Raspberry Pi CPU Serial (`/proc/cpuinfo` — `Serial` field)

| Property | Value |
|---|---|
| Stability | Stable across reboots and OS reinstalls on the same board |
| Attacker visibility | Visible to any process with `/proc/cpuinfo` access; recoverable with physical board access |
| Failure modes | Board replacement → binding lost; recovery requires explicit migration |
| Entropy | Low (predictable range for a given board revision) |
| Recommendation | Use as implemented: opt-in via `HardwareBindingProvider` presence |

### 2. Linux machine-id (`/etc/machine-id`)

| Property | Value |
|---|---|
| Stability | Stable within one OS install; regenerated on OS reinstall, container migration, or SD clone |
| Attacker visibility | Readable by any local user |
| Failure modes | OS reinstall breaks binding; SD card cloning copies machine-id, reducing differentiation |
| Entropy | 128-bit random value; high entropy but not a privately-held value |
| Recommendation | Not currently used; lower value than CPU serial for Pi appliance because cloning copies it |

### 3. SD Card CID (Card IDentification Register)

| Property | Value |
|---|---|
| Stability | Stable for the physical SD card; tied to storage medium, not the board |
| Attacker visibility | Readable via `/sys/block/mmcblk0/device/cid` on Linux; requires local access |
| Failure modes | SD card replacement → binding lost; SD cloning copies the CID |
| Entropy | Manufacturer + serial; low entropy, not cryptographically random |
| Recommendation | Not recommended: SD cards are frequently replaced; binding to the card rather than the board is usually wrong |

### 4. Deploy-Time Seed (`PHASMID_HARDWARE_SECRET_FILE` / `PHASMID_HARDWARE_SECRET`)

| Property | Value |
|---|---|
| Stability | Controlled by operator; explicit and auditable |
| Attacker visibility | Kept by operator; not exposed via OS APIs |
| Failure modes | Lost file → binding lost; explicit backup required |
| Entropy | Operator-controlled; can be high-entropy (256-bit random) |
| Recommendation | Preferred external binding method; already implemented and documented |

---

## Threat Analysis

### Reduces Attack Surface When

- An attacker obtains a copy of `vault.bin` and the state directory but not the
  physical board.  Without the CPU serial in the KDF, a correct passphrase alone is
  sufficient to attempt recovery; with the serial, the attacker also needs the board
  or its serial number.

- An attacker captures the state directory from a backup or SD clone but not the
  original board.  The serial provides a weak additional gate.

### Does Not Help When

- An attacker has physical access to the board.  The CPU serial is readable via
  `/proc/cpuinfo`.

- The attacker knows the board serial number from other sources (purchase record,
  device registration, physical inspection of the board's markings).

- The OS is compromised: a root-level process can read both the serial and any
  plaintext key material from memory.

### Failure Mode Risk

Device binding without documented recovery is a data-loss risk.  If the board fails or
is replaced, the container becomes unrecoverable unless:

1. The operator has a backup of the state directory from the original board, and
2. The operator restores state and re-derives the key on a board with the same serial.

Requirement 2 is infeasible: CPU serials are unique.  Practical recovery requires
an explicit migration step: retrieve on the original board before it fails.

---

## Recommendation

**Keep the current implementation with the following documentation additions:**

1. `HardwareBindingProvider` is opt-in via `/proc/cpuinfo` presence on Linux.  It is
   not a key-material source and must not be described as one.

2. `PHASMID_HARDWARE_SECRET_FILE` or `PHASMID_HARDWARE_SECRET_PROMPT=1` is the
   preferred external binding for high-risk deployments.  These provide operator-chosen
   entropy that can be backed up and controlled.

3. Machine-id binding is not implemented and not recommended: SD cloning copies it,
   reducing the device-tying benefit.

4. SD card CID binding is not implemented and not recommended: card replacement is
   common; tying to the card rather than the board creates the wrong failure mode.

5. No default behavior risks locking users out without an explicit opt-in.  The
   `HardwareBindingProvider` silently returns `None` on platforms without a board serial.

---

## Recovery and Migration Notes

If a Raspberry Pi board must be replaced and the vault was protected with hardware
binding active:

1. Retrieve all entries on the original board before it becomes unavailable.
2. Re-initialize the container on the new board.
3. Re-store entries.

This is the only supported recovery path when hardware binding is active.  There is
no key-escrow mechanism for the hardware-derived binding material.

---

## Field Test Updates

The field test procedure should include:

- Confirm `hardware_binding_status()` via the Doctor page before field evaluation.
- If external key material is configured, confirm it is accessible and not stored
  together with `vault.bin`.
- Record the board serial number in deployment notes for reference if board
  replacement is ever needed.
- Test retrieve and re-store after a simulated board replacement (i.e., reset the
  binding material and confirm old containers cannot be opened without migration).

---

## References

- `src/phasmid/kdf_providers.py` — `HardwareBindingProvider`, `hardware_binding_status()`
- `docs/THREAT_MODEL.md` — hardware binding residual risks
- `docs/SPECIFICATION.md` — v4 key schedule design (HKDF subkeys)
- `docs/RPI_ZERO_APPLIANCE_DEPLOYMENT.md` — key material and storage section
