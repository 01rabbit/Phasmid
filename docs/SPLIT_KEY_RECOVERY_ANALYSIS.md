# Threshold Split-Key Recovery Evaluation

## Purpose

This document evaluates threshold split-key recovery for Phasmid deployments that
cannot use hardware tokens.  The goal is to identify whether split-key approaches
belong in Phasmid's core, in operational documentation, or in a separate tool.

**No custom threshold cryptography implementation is included in this evaluation.**
Any production use of Shamir Secret Sharing or similar schemes requires a
well-reviewed library and independently verified test vectors.  This document
describes the design space and recommends a path that does not introduce
unreviewed cryptographic code.

---

## User Problem

The local vault access key and optional external key material currently live on the
same SD card as `vault.bin`.  If that SD card is the only copy of all required
key material, physical seizure or destruction of the card is a single point of
failure for both the protected content and the ability to recover it.

Split-key recovery addresses this by distributing key material across multiple
locations so that no single location holds enough to reconstruct the key alone.

---

## Evaluated Approaches

### 1. Split Key Files on Separate Media

**Description**: Divide the external key material into two or more files.  Store
one on the SD card, one on a USB drive, one on a separately stored device, etc.
Recovery requires all pieces.

| Property | Assessment |
|---|---|
| Cryptographic complexity | None beyond XOR or concatenation |
| Loss risk | Loss of any one piece → complete loss (no threshold) |
| Coercion risk | Each holder can be compelled independently |
| User error | Misplacing one piece is unrecoverable |
| Implementation | Already supported: `PHASMID_HARDWARE_SECRET_FILE` can point to any path |
| Recommendation | Suitable for simple n-of-n separation; not a threshold scheme |

This is the currently documented approach: store `vault.bin`, the state directory,
and optional external key material under separate physical control conditions.

### 2. Memorized Values (n-of-n)

**Description**: The passphrase itself is a combined value known only in full by the
operator.  No files are split; the split happens in the operator's memory.

| Property | Assessment |
|---|---|
| Cryptographic complexity | None |
| Loss risk | Memory failure → complete loss |
| Coercion risk | Single operator compelled → full disclosure |
| User error | Misremembering any component → no recovery |
| Implementation | Already supported: use a long, structured passphrase |
| Recommendation | Suitable for single-operator deployments; not a threshold scheme |

### 3. Printed Shares (Shamir Secret Sharing)

**Description**: Use Shamir Secret Sharing to split a key into N shares such that
any K shares reconstruct the key.  Print or store shares on physically separate media.

| Property | Assessment |
|---|---|
| Cryptographic complexity | Requires a reviewed SSS library (e.g., `sss-py`, `sslib`) |
| Loss risk | Loss of any K shares → complete loss; loss of fewer than K → no loss |
| Coercion risk | An attacker who captures K share holders can reconstruct |
| User error | Misplaced share below threshold → no loss; above threshold → loss |
| Implementation | Not currently implemented; requires library selection and review |
| Recommendation | Best threshold model, but requires external library and workflow tooling |

**Critical requirement**: Shamir Secret Sharing implementations vary in security.
Common pitfalls include non-uniform randomness, missing finite-field consistency checks,
and share encoding errors.  A production deployment should use an independently
reviewed library with published test vectors, not a handwritten implementation.

### 4. Removable Media Separation

**Description**: Store the external key material (`PHASMID_HARDWARE_SECRET_FILE`)
on a USB drive or microSD card kept physically separate from the main SD card.  Remove
and secure the removable media after each access session.

| Property | Assessment |
|---|---|
| Cryptographic complexity | None |
| Loss risk | Physical loss of the removable media → binding lost |
| Coercion risk | Attacker must obtain both the main device and the removable media |
| User error | Forgetting to re-insert → startup fails; recoverable by inserting and restarting |
| Implementation | Already supported: `PHASMID_HARDWARE_SECRET_FILE` |
| Recommendation | Practical and immediately available; not a threshold scheme |

---

## Risk Matrix

| Threat | Separate Files | Memorized | Shamir (K-of-N) | Removable Media |
|---|---|---|---|---|
| Single-media seizure | Mitigated | Mitigated | Mitigated | Mitigated |
| Loss of one piece | Complete loss | Complete loss | Threshold-bounded | Complete loss |
| Coercion of one holder | Mitigated (all needed) | Complete disclosure | Threshold-bounded | Mitigated (both needed) |
| User error (forget location) | Complete loss | Complete loss | Threshold-bounded | Recoverable |
| Implementation risk | None | None | Library-dependent | None |

---

## Recommendation

**For the current Phasmid prototype, threshold split-key is not added to core.**

Rationale:

1. The removable media pattern (`PHASMID_HARDWARE_SECRET_FILE` on a USB drive)
   provides practical two-location separation with no additional code or cryptographic
   assumptions.  This is the recommended operational approach.

2. True threshold recovery (Shamir K-of-N) provides better loss and coercion
   properties, but requires a reviewed library, share management workflow, and
   recovery documentation that go beyond the current prototype scope.

3. The existing `PHASMID_HARDWARE_SECRET_FILE` mechanism is already the correct
   interface for external key material.  Any future threshold implementation should
   produce a file at that path (i.e., reconstruct and write the key to a tmpfs path)
   rather than modifying the vault KDF.

**Threshold split-key as a separate tool**: A command-line tool that takes a
`PHASMID_HARDWARE_SECRET_FILE` value, splits it into N Shamir shares using a reviewed
library, and reconstructs it back into a file would compose cleanly with the current
design.  This tool belongs in a separate repository with independent review, not in
Phasmid core.

---

## Operational Guidance (Current)

Until a reviewed threshold tool exists, the recommended approach for deployments
that need key-material separation:

1. Generate a high-entropy external key material value:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))" > /media/usb/phasmid.key
   ```
2. Set `PHASMID_HARDWARE_SECRET_FILE=/media/usb/phasmid.key` in the service environment.
3. Store the USB drive separately from the device.
4. Keep a second encrypted copy (e.g., in a password manager or separately secured media).
5. Document the recovery procedure: to recover on a new device, both the main SD card
   and the USB drive (or its backup) are required.

This provides two-location separation with no new code and acceptable user-error
resistance for a single operator or small team.

---

## Claims Not Made

This analysis does not claim that split-key approaches provide:

- Perfect protection against compelled disclosure (all holders can be compelled)
- Guaranteed availability (shares can be lost)
- Protection against a compromised OS or physical hardware capture

---

## References

- `docs/THREAT_MODEL.md` — key material separation and operational guidance
- `docs/SOURCE_SAFE_WORKFLOW.md` — external key material storage guidance
- `docs/RPI_ZERO_APPLIANCE_DEPLOYMENT.md` — key material and storage section
- `src/phasmid/kdf_providers.py` — `FileSecretProvider`, `EnvSecretProvider`
