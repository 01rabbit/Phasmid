# Phasmid Key Lifecycle Audit

## Scope

This document summarizes the current key-material lifecycle in Phasmid:
creation, use, unlock/recovery, shutdown posture, and local access-path clearing.

It is an implementation audit summary, not a formal certification artifact.

## Lifecycle Summary

1. Creation
- A local access key is generated with `os.urandom()` by `KDFEngine._write_new_access_key()`.
- The key is written to `.state/access.bin` (or `PHASMID_STATE_DIR/access.bin`).
- The state directory is created with restrictive permissions (`0700` target).
- The key file is written with restrictive permissions (`0600` target).

2. Use in KDF
- Argon2id derivation combines passphrase context with secret material assembled by `KDFEngine._kdf_secret()`.
- Secret material can include:
  - local access key (`access.bin`);
  - optional external value from `PHASMID_HARDWARE_SECRET_FILE`;
  - optional static value from `PHASMID_HARDWARE_SECRET`;
  - hardware-binding provider output.
- Object-cue matching is operational gating and does not supply cryptographic key material.

3. Recovery / Unlock Path
- Recovery requires container ciphertext plus KDF inputs needed by the selected entry path.
- `vault.bin` alone is insufficient when required local/external secret inputs are missing.
- If `access.bin` and other required secret inputs are copied together with `vault.bin`, separation benefits are reduced.

4. Rotation / Replacement
- `rotate_access_key()` unlinks the old local access key and writes a newly generated key.
- `format_container(rotate_access_key=True)` rotates local access key material during container re-initialization.

5. Local Access-Path Clearing
- `vault.silent_brick()` calls:
  - `destroy_access_keys()` first (best-effort overwrite + file removal for `access.bin`);
  - container overwrite path second (`container_layout.silent_brick()`).
- This order enforces key-path invalidation before overwrite.
- On flash media, overwrite is best effort only.

## Persistent Key-Material Locations (Current)

- `.state/access.bin`: raw local access key bytes (persistent by design in current architecture).
- Optional external secret file (if configured): path defined by `PHASMID_HARDWARE_SECRET_FILE`.
- `vault.bin`: encrypted payload container; not raw key storage.

Phasmid currently retains persistent local key material in `access.bin` for recovery-path separation behavior. This is a known tradeoff and must be treated as sensitive local state.

## Memory and Runtime Notes

- Key material is derived and used in-process for cryptographic operations.
- Python/runtime memory is not guaranteed to be fully scrubbed after use.
- Swap, crash dumps, and host compromise can expose in-use material.

## Brick / Restricted-Clear Interpretation

Phasmid brick and restricted-clear behavior are logical access-destruction mechanisms:

- key-path invalidation through local key-material destruction;
- best-effort overwrite of stored ciphertext.

They are not physical media sanitization guarantees for SD/eMMC/flash devices.

## Hardening Direction (Documentation-Only in This Phase)

- Keep `vault.bin` and state on encrypted local storage.
- Separate external secret material from the same physical medium where feasible.
- Prefer volatile key handling for additional layers (for example, tmpfs-backed wrappers) where deployment permits.
- Keep claims aligned with flash/FTL limits and avoid secure-deletion language.
