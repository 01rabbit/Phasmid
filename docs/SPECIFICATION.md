# Phantasm Specification

## 1. Overview

Phantasm is a field-evaluation prototype for local-only coercion-aware storage. It stores encrypted payloads in `vault.bin` and requires a password plus a camera-recognized physical object cue before recovery.

The project is intended for USB gadget mode or localhost access. It is not a replacement for full-disk encryption, hardware-backed key storage, audited classified-data handling, or a complete solution to compelled disclosure.

## 2. Features

- Initialize an encrypted container.
- Store protected entries in an internal two-slot container model.
- Register and verify camera-based physical object cues.
- Encrypt and retrieve payloads.
- Support normal access and restricted recovery behavior.
- Clear local state through restricted owner-controlled actions.
- Operate from a CLI or local WebUI v2.
- Optionally write a minimal audit log.

## 3. Repository Layout

| Path | Purpose |
| --- | --- |
| `main.py` | Compatibility CLI launcher |
| `src/phantasm/cli.py` | CLI implementation |
| `src/phantasm/gv_core.py` | Encrypted container logic |
| `src/phantasm/ai_gate.py` | Camera input, object-cue registration, ORB matching |
| `src/phantasm/web_server.py` | FastAPI Web UI/API |
| `src/phantasm/bridge_ui.py` | OpenCV status UI |
| `src/phantasm/emergency_daemon.py` | Panic trigger watcher and local access-path clear flow |
| `src/phantasm/audit.py` | Optional audit log |
| `src/phantasm/config.py` | Shared state names and runtime policy |
| `src/phantasm/templates/` | WebUI v2 server-rendered templates |
| `scripts/bench_kdf.py` | Argon2id benchmark helper |
| `docs/THREAT_MODEL.md` | Threat model |
| `tests/` | Unit tests |

## 4. Runtime Files

| Path | Purpose |
| --- | --- |
| `vault.bin` | Encrypted container |
| `.state/store.bin` | Encrypted object-cue state blob |
| `.state/lock.bin` | Local key for object-cue state encryption |
| `.state/access.bin` | Local access key required to recover `vault.bin` |
| `.state/signal.key` | Panic trigger token |
| `.state/signal.trigger` | Panic trigger file |
| `.state/events.log` | Optional audit log |
| `.state/events.auth` | Optional audit verifier material |
| `.state/face.bin` | Optional encrypted WebUI face-lock template |
| `.state/face.enroll` | Short-lived first-time face enrollment request |

The default state directory is `.state/` and can be changed with `PHANTASM_STATE_DIR`. The directory is intended to be mode `0700`; sensitive files are intended to be mode `0600`. Neutral filenames reduce obvious metadata, but they do not provide deniability.

New local state code paths should use the typed state store for schema-versioned records, atomic writes, restrictive file permissions, and explicit transition checks. Existing binary state files remain compatibility-managed by their owning modules until a migration path is defined.

## 4.1 Cryptographic Boundary

Phantasm defines a local cryptographic primitive boundary in `src/phantasm/crypto_boundary.py`. Startup checks cover AES-GCM round trip behavior, HMAC-SHA-256 behavior, and random byte generation health. Failure causes local startup to stop with a neutral message in the CLI path.

This boundary improves reviewability and failure detection. It is not a FIPS validation, certification claim, or replacement for independent cryptographic review.

## 5. Internal Entry Model

The container uses two fixed internal storage spans. The CLI keeps a compact `--entry a` / `--entry b` selector for compatibility, while WebUI v2 maps the internal model to neutral protected-entry workflows and does not expose internal labels during normal operation.

## 6. CLI

### Initialize

```bash
python3 main.py init
```

This rotates the local access key, overwrites `vault.bin` with random data, and leaves an empty container ready for new entries.

### Store

```bash
python3 main.py store --entry a --file path/to/file
python3 main.py store --entry b --file path/to/file
```

Store flow:

1. Start the camera gate.
2. Prompt for normal access and restricted recovery passwords.
3. Reject empty, duplicate, short, or highly repetitive passphrases.
4. Register the physical object cue for the selected internal entry.
5. Read the input file.
6. Derive a key with Argon2id.
7. Encrypt the payload with AES-GCM.

### Retrieve

```bash
python3 main.py retrieve --out output.bin
```

Retrieve flow:

1. Start the camera gate.
2. Prompt for the vault password.
3. Verify the registered physical object cue.
4. Attempt recovery against internal candidates.
5. Write or display the recovered payload if access succeeds.
6. Apply restricted recovery behavior only when the password or configured policy requires it.

These settings and passwords can cause data loss:

- `PHANTASM_PURGE_CONFIRMATION=0`
- `PHANTASM_DURESS_MODE=1`
- restricted recovery passwords

### Clear Local Access Path

```bash
python3 main.py brick
```

This flow destroys `.state/access.bin` first, then performs a best-effort overwrite of `vault.bin`. Flash media, snapshots, backups, and journaling filesystems may retain old data. Recovery resistance depends primarily on destruction, rotation, or removal of required key material, not on overwrite guarantees.

### Reset UI Face Lock

```bash
python3 main.py reset-face-lock
```

This CLI-only flow resets the optional WebUI face lock. It requires the typed confirmation phrase `RESET FACE LOCK AND VAULT`, removes the encrypted face-lock template, rotates the local access key, initializes `vault.bin`, clears physical-object bindings, clears active face-lock sessions, and creates a short-lived local enrollment request. This is a data-loss operation because changing the UI user invalidates the local trust boundary for stored entries.

## 7. WebUI v2

Start the server:

```bash
PYTHONPATH=src python3 -m phantasm.web_server
```

The default bind address is `127.0.0.1:8000`.

WebUI v2 is server-rendered with lightweight JavaScript. It preserves the internal two-slot model while presenting normal operations as protected-entry workflows.

Normal navigation:

- Home
- Store
- Retrieve
- Maintenance

The restricted action view is available only by direct route and is not shown in normal navigation. A direct `GET /emergency` renders only a restricted confirmation screen until the browser has a fresh restricted confirmation session. Hidden route concealment is not a security boundary.

`PHANTASM_FIELD_MODE=1` reduces normal Maintenance detail for appliance use. Before restricted confirmation, Maintenance shows only general health, local-only posture, UI lock state, and a confirmation requirement for sensitive maintenance. It hides state paths, audit export, token rotation, and detailed diagnostics until a fresh restricted confirmation is active.

Field Mode is not a security boundary. It reduces casual local exposure in the WebUI and maintenance APIs. It does not prevent forensic inspection, filesystem analysis, memory capture, host compromise, browser compromise, physical coercion, or lawful compulsory process.

Hidden restricted routes are UX concealment only. They are not access control by themselves. High-risk actions are evaluated through a shared local policy layer that combines deployment-mode capability, local tokens, UI unlock state, restricted confirmation freshness, and typed confirmation where applicable.

WebUI responses include conservative browser hardening headers such as no-store cache control, frame denial, MIME-sniffing protection, a local-only content security policy, no-referrer policy, and limited browser permissions. These headers reduce browser-visible residue and common embedding or caching risks. They do not make the WebUI suitable for untrusted networks and are not a substitute for local-only binding, host integrity, or operator discipline.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Home |
| `GET` | `/store` | Store screen |
| `GET` | `/retrieve` | Retrieve screen |
| `GET` | `/maintenance` | Maintenance screen |
| `GET` | `/maintenance/entries` | Entry management screen |
| `GET` | `/emergency` | Hidden restricted action screen |
| `GET` | `/ui-lock` | Optional UI face-lock screen |
| `GET` | `/video_feed` | Camera stream for unlocked UI sessions |
| `GET` | `/status` | Neutral device/object status |
| `POST` | `/restricted/confirm` | Short-lived restricted confirmation |
| `POST` | `/face/enroll` | Enroll or replace optional UI face lock |
| `POST` | `/face/verify` | Unlock optional UI face session |
| `POST` | `/face/lock` | Clear optional UI face session |
| `POST` | `/register_key` | Bind or rebind a physical object |
| `POST` | `/store` | Store a protected entry |
| `POST` | `/metadata/check` | Local metadata risk check |
| `POST` | `/metadata/scrub` | Best-effort local metadata reduction |
| `POST` | `/retrieve` | Retrieve and download the matching entry |
| `POST` | `/purge_other` | Hidden restricted clear action |
| `POST` | `/emergency/initialize` | Hidden container initialization |
| `POST` | `/emergency/brick` | Hidden local access-path clear action |
| `GET` | `/maintenance/diagnostics` | Local diagnostics |
| `POST` | `/maintenance/rotate_token` | Rotate Web mutation token |
| `POST` | `/maintenance/reset_session` | Reset local session counters |
| `GET` | `/maintenance/logs` | Export optional local audit log |

Mutating endpoints require `X-Phantasm-Token`. Sensitive endpoints also require a short-lived restricted confirmation session and typed action confirmation where applicable. Entry Management withholds binding details until restricted confirmation is active and returns only selected-entry neutral status.

`/status` intentionally returns only neutral fields:

- `camera_ready`
- `object_state`
- `device_state`
- `local_mode`

The normal UI must not display internal entry labels, internal retrieval order, or restricted local-state behavior after retrieval.

Detailed maintenance diagnostics may include neutral hardware-binding availability fields after restricted confirmation or when Field Mode is not suppressing detail.

Optional UI face lock is enabled with `PHANTASM_UI_FACE_LOCK=1`. It gates access to normal WebUI routes with a short-lived local session cookie. Face templates are encrypted in the runtime state directory. This lock is not used in Argon2id input and does not participate in vault encryption or retrieval.

First-time face enrollment is disabled unless the WebUI process is started with `PHANTASM_UI_FACE_ENROLL=1` or a valid `.state/face.enroll` request exists. The setup flag is intended for device provisioning only. The enrollment request is created by `python3 main.py reset-face-lock`, is checked when `/ui-lock` is reloaded, and is removed after successful enrollment.

## 8. Capture-Visible Surface Rule

No capture-visible surface should reveal the internal disclosure model, internal trial order, slot purpose, restricted recovery side effects, or the existence of an alternate protected state.

Capture-visible surfaces include the WebUI, rendered HTML, browser history, browser cache, JavaScript console, response headers, download filenames, CLI output, shell history, systemd stdout/stderr, audit logs, state-directory filenames, screenshots, and documentation copied to the device.

Common user-facing wording should be centralized where practical. New UI, CLI, API, and audit text must either reuse shared neutral strings or pass terminology audit before release.

## 9. Stress-Use UX Principle

Phantasm must prefer simple, low-choice flows under stress.

Normal operation should remain:

1. Store
2. Retrieve
3. Maintenance

Restricted actions must remain separated. Field Mode should reduce diagnostic noise. The UI should avoid forcing the user to reason about internal slots, trial order, recovery side effects, or disclosure structure during stressful conditions.

## 10. Metadata and Data Minimization

Store provides a local-only metadata risk check. It does not call cloud services and does not send telemetry.

`/metadata/check` and `/metadata/scrub` enforce the normal Web mutation token, UI unlock state, rate limiting, and upload size limit. Uploaded data is processed in memory; these routes do not require writing the uploaded file to disk, and the intended implementation property is no disk write for uploaded metadata inspection.

The initial checker warns about common risks:

- GPS-like image metadata;
- camera maker or model metadata;
- device serial-like fields;
- document author fields;
- creator application fields;
- document title or subject fields;
- embedded thumbnails;
- local path leakage;
- original filename context.

Storage is not blocked by default. The UI offers continue, best-effort metadata reduction when supported, or cancel.

Best-effort metadata reduction is conservative. It never overwrites the original file unless a future explicit option is added. Unsupported file types fail safely. Downloads use a neutral filename and must not expose the original filename in response headers. Metadata removal is best-effort and may not remove every embedded identifier from every file format.

The Store screen includes a short reminder: store only what is needed and separate identities, evidence, notes, and operational context when possible.

## 11. Cryptography

The current format is GhostVault v3.

- No plaintext magic/header.
- Fixed-width internal storage spans.
- Each span contains a normal access slot and a restricted recovery slot.
- Per-record random salt and nonce.
- AES-GCM authenticated encryption.
- Filename and payload metadata are encrypted.
- v1/v2 compatibility retrieval has been removed.

Argon2id inputs:

- User password
- Physical-object cue token
- Internal mode
- Password role
- Per-record random salt
- `.state/access.bin`
- Optional external values from `PHANTASM_HARDWARE_SECRET_FILE`, `PHANTASM_HARDWARE_SECRET`, or `PHANTASM_HARDWARE_SECRET_PROMPT`

Default Argon2id parameters are tuned for Raspberry Pi Zero 2 W class hardware: `memory_cost=32768`, `iterations=2`, `lanes=1`.

Recommended field hierarchy:

1. strong access password;
2. physical-object cue;
3. `.state/access.bin`;
4. optional external value via `PHANTASM_HARDWARE_SECRET_FILE` or `PHANTASM_HARDWARE_SECRET_PROMPT=1`.

For high-risk deployments, do not store all recovery conditions on the same physical medium. Phantasm is strongest when the encrypted container, local state, memorized password, physical-object cue, and optional external key material are separated.

## 12. Physical-Key Matching

Phantasm extracts ORB features from camera frames.

Registration:

1. Capture several frames over a short interval.
2. Select the candidate with the most keypoints.
3. Reject low-feature images.
4. Reject candidates too similar to an existing object cue.
5. Store templates together in encrypted `.state/store.bin`.

Retrieval:

1. Extract ORB features from current frames.
2. Match against encrypted reference templates.
3. Require enough good matches and homography inliers.
4. Require stable matching in at least 3 of the last 5 frames.
5. Reject ambiguous matches.

The physical object is an operational cue, not a high-entropy cryptographic factor.

## 13. Runtime Policy

| Variable | Purpose | Default |
| --- | --- | --- |
| `PHANTASM_STATE_DIR` | Runtime state directory | `.state` |
| `PHANTASM_STATE_SECRET` | External value for object-cue state encryption | unset |
| `PHANTASM_HARDWARE_SECRET_FILE` | External value file mixed into Argon2id | unset |
| `PHANTASM_HARDWARE_SECRET` | External value string mixed into Argon2id | unset |
| `PHANTASM_HARDWARE_SECRET_PROMPT` | Prompt for an external value | unset |
| `PHANTASM_PURGE_CONFIRMATION` | Require explicit confirmation for configured recovery behavior | `1` |
| `PHANTASM_DURESS_MODE` | Enable opt-in access-triggered local-state update | `0` |
| `PHANTASM_WEB_TOKEN` | Web mutation token | random at start |
| `PHANTASM_HOST` | Web bind host | `127.0.0.1` |
| `PHANTASM_PORT` | Web bind port | `8000` |
| `PHANTASM_MAX_UPLOAD_BYTES` | Web upload limit | `26214400` |
| `PHANTASM_UI_FACE_LOCK` | Require local face check before WebUI use | `0` |
| `PHANTASM_UI_FACE_ENROLL` | Permit first-time face-lock enrollment during setup | `0` |
| `PHANTASM_UI_FACE_ENROLL_SECONDS` | Face enrollment request lifetime | `600` |
| `PHANTASM_UI_FACE_SESSION_SECONDS` | Face-unlocked UI session lifetime | `300` |
| `PHANTASM_RESTRICTED_SESSION_SECONDS` | Restricted confirmation lifetime | `120` |
| `PHANTASM_FIELD_MODE` | Reduce normal WebUI operational detail | `0` |
| `PHANTASM_PROFILE` | Select local capability mode: `standard`, `field`, or `maintenance` | `standard` |
| `PHANTASM_MIN_PASSPHRASE_LENGTH` | Minimum Store passphrase length | `10` |
| `PHANTASM_ACCESS_MAX_FAILURES` | Failed access attempts before temporary lockout | `5` |
| `PHANTASM_ACCESS_LOCKOUT_SECONDS` | Temporary access lockout duration | `60` |
| `PHANTASM_AUDIT` | Enable audit logging | `0` |
| `PHANTASM_AUDIT_FILENAMES` | Record filename hashes | unset |

## 14. Mission Presets and Retention

Phantasm documentation defines neutral mission presets rather than role-revealing UI labels. Examples include:

- Local Notes;
- Temporary Holding;
- Protected Material;
- Travel Set;
- Review Set;
- Research Material.

Presets should influence guidance such as metadata warning, external key material recommendation, retention reminders, audit disabled by default, Field Mode recommendation, and entry separation guidance.

Retention principle: the safest sensitive data is data not carried. Users should remove stale entries after the task or trip, avoid old contact lists, avoid mixing unrelated work in one local entry, and review contents before checkpoints or inspection events.

## 15. Restricted Recovery and Key Destruction

On flash media, complete overwrite-based deletion cannot be guaranteed across every storage layer. Phantasm therefore treats restricted recovery primarily as key-path invalidation and key-material destruction, with best-effort overwrite as a secondary measure.

Restricted recovery must not be represented as guaranteed secure deletion. User-facing surfaces should use neutral terms such as restricted local update, local access path, key material, and best-effort overwrite.

## 16. Appliance and Seizure Review

Raspberry Pi Zero 2 W appliance assumptions are documented in `docs/RPI_ZERO_APPLIANCE_DEPLOYMENT.md`. The recommended appliance posture is local-only binding, USB gadget access, SSH disabled after provisioning, Wi-Fi and Bluetooth disabled unless explicitly needed, dedicated service user, systemd hardening, Field Mode, audit disabled by default, debug disabled by default, no telemetry, no cloud dependency, no remote management, and external key-material separation.

Seizure review requirements are documented in `docs/SEIZURE_REVIEW_CHECKLIST.md`. Review normal screens, restricted pages before and after confirmation, browser history, cache, HTML source, JavaScript console, HTTP response headers, download filenames, optional audit logs, `.state/` names, temporary files, shell history, systemd logs, CLI output, environment variables, and service unit files.

Operational guidance documents include `docs/SOURCE_SAFE_WORKFLOW.md`, `docs/SEIZURE_REVIEW_CHECKLIST.md`, `docs/FIELD_TEST_PROCEDURE.md`, `docs/REVIEW_VALIDATION_RECORD.md`, `docs/OPERATIONS.md`, `docs/RESTRICTED_ACTIONS.md`, and `docs/STATE_RECOVERY.md`.

Optional audit records are versioned and include sequence, previous record hash, record hash, and local verifier fields. This improves local tamper review when audit logging is enabled, but it also creates additional local metadata and is disabled by default.

## 17. Testing

```bash
python3 -m unittest discover -s tests
```

KDF benchmark:

```bash
python3 scripts/bench_kdf.py
```

## 18. Compatibility

This build reads and writes GhostVault v3 only. Older v1/v2 containers must be retrieved with an older build and then stored again with this build.

## 19. Limits

Phantasm does not guarantee protection against a compromised OS, live memory capture, keylogging, camera observation, forced disclosure, complete secure deletion, deniability, or unsafe network exposure.
