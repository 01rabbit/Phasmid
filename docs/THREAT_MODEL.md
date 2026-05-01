# Phantasm Threat Model

## Scope

Phantasm is a local secure-storage prototype. It protects payloads in `vault.bin` with a password, a camera-matched physical object profile, and an authenticated container format. It is not a substitute for audited full-disk encryption, hardware-backed key storage, or classified-data handling procedures.

## Assets

- Payload bytes and original filename metadata.
- Profile A/Profile B separation.
- Encrypted camera reference state blob in the configured state directory.
- Local vault access key in the configured state directory.
- Panic token in the configured state directory.
- Web UI mutation token created at process start or supplied through `PHANTASM_WEB_TOKEN`.

## Assumptions

- The host operating system account is trusted while Phantasm is running.
- Attackers may obtain a copy of `vault.bin`.
- Attackers may observe or copy files in the project directory if OS permissions are weak.
- The Web UI is intended for local use through `127.0.0.1`.
- Camera matching is an operational gate, not a cryptographic biometric factor.

## Current Defenses

- New stores use GhostVault v3 records: random per-record Argon2id salt, random per-record AES-GCM nonce, no plaintext magic/header, and AEAD-authenticated encrypted metadata.
- The local access key is mixed into Argon2id by default, so copying `vault.bin` alone is insufficient for decryption.
- Each profile can be stored with two passwords that share the same physical-key profile: an open password and an open+purge password.
- `PHANTASM_HARDWARE_SECRET_FILE`, `PHANTASM_HARDWARE_SECRET`, or `PHANTASM_HARDWARE_SECRET_PROMPT=1` can add an external secret to Argon2id derivation. Data stored with any of these values requires the same value for retrieval.
- Default Argon2id parameters are tuned for Raspberry Pi Zero 2 W class hardware: `memory_cost=32768`, `iterations=2`, `lanes=1`.
- Profile spans are separated in the container, and purge operations overwrite the selected span.
- Open-password retrieval does not automatically purge the alternate profile by default. CLI purge requires an explicit confirmation phrase, and Web purge is exposed as a separate mutating endpoint.
- Open+purge-password retrieval silently purges the alternate profile after successful retrieval.
- `PHANTASM_PURGE_CONFIRMATION=0` disables the explicit confirmation phrase and purges the alternate profile automatically after open-password retrieval.
- `PHANTASM_DURESS_MODE=1` enables opt-in duress behavior: Profile A open-password retrieval automatically purges Profile B. This is disabled by default because it can cause irreversible data loss.
- Reference keys are stored together in a single AES-GCM encrypted ORB state blob under the configured state directory, not as raw reference photos or semantic per-profile template filenames.
- Image-key matching requires stable results across a short frame window rather than accepting a single-frame match.
- Web mutation endpoints require `X-Phantasm-Token`, apply a simple per-client rate limit, and enforce upload size limits.
- Optional UI face lock (`PHANTASM_UI_FACE_LOCK=1`) can gate normal WebUI routes with a short-lived local session. This is a UI access control only and is not used for vault encryption.
- UI face-lock reset is CLI-only and requires a typed confirmation phrase. It clears the face template, rotates the local access key, initializes the vault container, and clears physical-object bindings so a changed UI user starts from an empty local state.
- The Web server binds to `127.0.0.1` by default.
- Panic triggers require the secret value from the state directory's signal key.
- Audit logging is disabled by default. If `PHANTASM_AUDIT=1` is set, security-relevant operations append minimal JSONL records to the state directory's event log without recording passwords, payload bytes, or plaintext filenames. Filename hashes are only recorded when `PHANTASM_AUDIT_FILENAMES=hash`.

## Residual Risks

- A compromised host can read passwords, process memory, camera frames, Web tokens, and decrypted output.
- ORB feature templates are not high-entropy secrets. If the local state lock key is copied with the state blob, the local template encryption does not protect them. Set `PHANTASM_STATE_SECRET` from outside the project directory for stronger at-rest protection.
- If the local access key is copied with `vault.bin`, the local access-key protection does not raise the attacker's cost. Use an external secret source for higher resistance.
- Secure deletion is best-effort only. SSD wear leveling, backups, snapshots, and journaling filesystems may retain previous data.
- The v3 format avoids a plaintext format marker, but fixed profile spans and the surrounding tool files can still reveal that a Phantasm-style container may be in use.
- Dual password slots duplicate the encrypted payload within the selected profile span. This improves operational control but reduces the maximum payload size per profile.
- UI face lock is not a cryptographic authenticator for vault data. It can be affected by lighting, camera angle, false rejects, false accepts, and presentation attacks using photos or screens.
- The in-memory Web rate limiter resets on process restart and is not a substitute for a real access-control layer.
- Legacy v1/v2 retrieval has been removed. Old containers must be migrated by retrieving with an older build and storing again with this build.

## Operational Guidance

- Keep `PHANTASM_HOST` at the default `127.0.0.1` unless the host is otherwise protected.
- Set `PHANTASM_WEB_TOKEN` explicitly for repeatable controlled sessions.
- Prefer `PHANTASM_HARDWARE_SECRET_FILE` or `PHANTASM_HARDWARE_SECRET_PROMPT=1` over long-lived environment variables when adding an external device secret. Plain environment variables can be exposed through process inspection on compromised systems.
- Set `PHANTASM_STATE_SECRET` from removable media, a password manager, or a device secret if encrypted reference templates must survive project-directory disclosure.
- Enable `PHANTASM_AUDIT=1` only when an audit trail is more important than minimizing local metadata.
- Keep the configured state directory and `vault.bin` on encrypted local storage.
- Treat UI face lock as a convenience barrier for local interface use, not as a substitute for passwords, object cues, or external secrets.
- Use `python3 main.py reset-face-lock` when the authorized local UI user changes. This intentionally rotates the local access key, clears stored vault data, and clears object bindings as part of the reset.
- Use distinct high-entropy values for open and open+purge passwords. The open+purge password is intentionally destructive.
- Keep `PHANTASM_PURGE_CONFIRMATION=1` unless the deployment explicitly accepts the data-loss risk of automatic purge.
- Treat Profile A/Profile B as convenience separation, not a guarantee of plausible deniability.
- Reinitialize the container after a real panic event.
- Run tests before changing cryptographic or Web boundary behavior.
