# Phantasm Threat Model

## Scope

Phantasm is a field-evaluation prototype for local-only coercion-aware storage. It protects payloads in `vault.bin` with password-based cryptographic recovery, a camera-matched physical object cue, a local access key, and authenticated encryption.

It is not a substitute for audited full-disk encryption, hardware-backed key storage, classified-data handling procedures, or a complete answer to compelled disclosure.

## Assets

- Payload bytes and encrypted payload metadata.
- Separation between visible recovery outcomes and protected local state.
- Encrypted camera reference state blob in the configured state directory.
- Local vault access key in the configured state directory.
- Panic token in the configured state directory.
- Web UI mutation token created at process start or supplied through `PHANTASM_WEB_TOKEN`.
- Browser-visible surfaces such as rendered HTML, console output, response headers, filenames, and cached pages.
- CLI output, shell history, application stdout/stderr, and systemd logs.
- camera overlay text and Maintenance diagnostics output.
- Source identity, notes, evidence metadata, temporary field data, and local operational context.

## Assumptions

- The host operating system account is trusted while Phantasm is running.
- Attackers may obtain a copy of `vault.bin`.
- Attackers may observe or copy files in the project directory if OS permissions are weak.
- The Web UI is intended for local use through `127.0.0.1` or USB gadget networking.
- Camera matching is an operational gate, not a cryptographic biometric factor.
- Device capture is realistic, so rendered UI and documentation should avoid explaining the internal disclosure model during normal use.
- Field Mode reduces normal information exposure, but it is not a security boundary.
- Hidden restricted routes reduce casual exposure, but they are not security boundaries.
- Hidden routes are not access control by themselves; server-side token checks, UI unlock state, restricted confirmation, and typed confirmation remain required.

## Current Defenses

- New stores use GhostVault v3 records: random per-record Argon2id salt, random per-record AES-GCM nonce, no plaintext magic/header, and AEAD-authenticated encrypted metadata.
- The local access key is mixed into Argon2id by default, so copying `vault.bin` alone is insufficient for recovery.
- Protected entries can be stored with normal access and restricted recovery passwords that share the same object cue.
- Store flows reject empty, duplicate, short, or highly repetitive passphrases to reduce accidental weak input.
- `PHANTASM_HARDWARE_SECRET_FILE`, `PHANTASM_HARDWARE_SECRET`, or `PHANTASM_HARDWARE_SECRET_PROMPT=1` can add an external value to Argon2id derivation. Data stored with any of these values requires the same value for retrieval.
- Default Argon2id parameters are tuned for Raspberry Pi Zero 2 W class hardware: `memory_cost=32768`, `iterations=2`, `lanes=1`.
- Restricted recovery behavior and explicit restricted actions can update unmatched local state. These paths can cause irreversible data loss.
- Reference keys are stored together in a single AES-GCM encrypted ORB state blob under the configured state directory, not as raw reference photos or semantic per-entry template filenames.
- Image-key matching requires stable results across a short frame window rather than accepting a single-frame match.
- Web mutation endpoints require `X-Phantasm-Token`, apply a simple per-client rate limit, and enforce upload size limits.
- Access recovery flows count repeated local failures and apply a bounded temporary lockout. WebUI limiting is process-local; CLI limiting is stored in local state.
- Web responses include no-store cache headers, frame denial, MIME-sniffing protection, no-referrer policy, constrained browser permissions, and a local-only content security policy. These reduce browser residue and common Web embedding risks but do not make the WebUI safe for untrusted networks.
- Sensitive Web actions require a fresh restricted confirmation session in addition to the Web token and UI unlock state. Restricted action pages and entry maintenance details are withheld until that confirmation is active.
- Optional UI face lock (`PHANTASM_UI_FACE_LOCK=1`) can gate normal WebUI routes with a short-lived local session. This is a UI access control only and is not used for vault encryption.
- When UI face lock is enabled, the normal object-matching preview and object-match state are withheld until the UI is unlocked. The lock screen shows a separate camera preview for enrollment and verification alignment.
- The Web server binds to `127.0.0.1` by default.
- Audit logging is disabled by default. If `PHANTASM_AUDIT=1` is set, security-relevant operations append minimal versioned JSONL records to the state directory's event log without recording passwords, payload bytes, plaintext filenames, or internal slot labels. New records include local integrity fields for review.
- Field Mode (`PHANTASM_FIELD_MODE=1`) hides Maintenance paths, audit export, token rotation, and detailed diagnostics until restricted confirmation is active.
- Store includes a local metadata risk check and limited best-effort metadata reduction for supported file types.
- Documentation includes seizure review, source-safe storage separation, field testing, and Raspberry Pi Zero 2 W appliance deployment guidance.

## Capture-Visible Surfaces

Capture-visible surfaces include the WebUI, rendered HTML, browser history, browser cache, JavaScript console, response headers, download filenames, CLI output, shell history, systemd stdout/stderr, audit logs, state-directory filenames, screenshots, and documentation copied to the device.

These surfaces should not reveal the internal disclosure model, internal trial order, slot purpose, restricted recovery side effects, or the existence of an alternate protected state.

## Residual Risks

- A compromised host can read passwords, process memory, camera frames, Web tokens, and decrypted output.
- ORB feature templates are not high-entropy cryptographic material. If the local state lock key is copied with the state blob, the local template encryption does not protect them.
- If the local access key is copied with `vault.bin`, the local access-key protection does not raise attacker cost.
- If `vault.bin`, the configured state directory, and external key material are carried together on one medium, separation benefits are reduced.
- Secure deletion is best-effort only. SSD wear leveling, backups, snapshots, and journaling filesystems may retain previous data.
- On flash media, recovery resistance depends primarily on key-material destruction or removal, not overwrite guarantees.
- The v3 format avoids a plaintext format marker, but surrounding tool files can still reveal that a Phantasm-style container may be in use.
- Dual password slots duplicate encrypted payload material within the selected internal storage span. This improves operational control but reduces maximum payload size.
- UI face lock can be affected by lighting, camera angle, false rejects, false accepts, and presentation attacks using photos or screens.
- The in-memory Web rate limiter and restricted confirmation state reset on process restart and are not substitutes for a full access-control layer.
- Access-attempt limiting slows repeated local failures but does not stop offline guessing against copied data, compromised hosts, or deliberate state rollback.
- UI tokens can be read from a compromised browser or host session.
- Passphrase policy cannot compensate for observed input, reused passwords, coercion, compromised hosts, or poor operational separation.
- Metadata checks and metadata reduction are best-effort. They can miss embedded identifiers, thumbnails, histories, and application-specific fields.
- Optional audit logs can support local review, including tamper detection for versioned records, but they also create local metadata.
- Browser history, cache, shell history, systemd logs, environment variables, and temporary files can leak operational context if the appliance is not configured carefully.
- Legacy v1/v2 retrieval has been removed. Old containers must be migrated by retrieving with an older build and storing again with this build.

## Operational Guidance

- Keep `PHANTASM_HOST` at the default `127.0.0.1` unless the host is otherwise protected.
- Do not expose the WebUI to an untrusted network.
- Set `PHANTASM_WEB_TOKEN` explicitly for repeatable controlled sessions.
- Prefer `PHANTASM_HARDWARE_SECRET_FILE` or `PHANTASM_HARDWARE_SECRET_PROMPT=1` over long-lived environment variables when adding an external device value.
- Set `PHANTASM_STATE_SECRET` from removable media, a password manager, or a device value if encrypted reference templates must survive project-directory disclosure.
- Enable `PHANTASM_AUDIT=1` only when an audit trail is more important than minimizing local metadata.
- Keep the configured state directory and `vault.bin` on encrypted local storage.
- For high-risk deployments, separate `vault.bin`, local state, memorized password, object cue, and optional external key material across different control conditions.
- Use `PHANTASM_FIELD_MODE=1` for appliance-style deployments.
- Treat UI face lock as a convenience barrier for local interface use, not as a substitute for passwords, object cues, or external values.
- Use `PHANTASM_UI_FACE_ENROLL=1` only during controlled provisioning.
- Reload `/ui-lock` after `python3 main.py reset-face-lock` to consume the short-lived enrollment request.
- Use `python3 main.py reset-face-lock` when the authorized local UI user changes. This intentionally rotates the local access key, clears stored vault data, and clears object bindings as part of the reset.
- Use distinct high-entropy values for normal access and restricted recovery passwords.
- Keep `PHANTASM_PURGE_CONFIRMATION=1` unless the deployment explicitly accepts the data-loss risk of automatic local-state updates.
- Reinitialize the container after a panic event.
- Run the seizure review checklist before field evaluation.
- Review metadata before storing source, evidence, notes, or travel material.
- Keep only necessary data on the device and remove stale entries after the task or trip.
- Run tests before changing cryptographic or Web boundary behavior.
