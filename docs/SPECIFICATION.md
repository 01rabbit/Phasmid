# Phantasm Specification

## 1. Overview

Phantasm is a local secure-storage prototype. It stores encrypted payloads in `vault.bin` and requires a password plus a camera-recognized physical object profile before retrieval.

The project is intended for local use, including USB gadget mode or localhost access. It is not a replacement for full-disk encryption, a hardware security module, or an audited classified-data handling system.

## 2. Features

- Initialize an encrypted container.
- Store Profile A and Profile B payloads.
- Register and verify camera-based physical keys.
- Encrypt and retrieve payloads.
- Use separate open and open+purge passwords for each stored payload.
- Trigger emergency brick behavior.
- Operate from a CLI or local Web UI.
- Optionally write a minimal audit log.

## 3. Repository Layout

| Path | Purpose |
| --- | --- |
| `main.py` | Compatibility CLI launcher |
| `src/phantasm/cli.py` | CLI implementation |
| `src/phantasm/gv_core.py` | Encrypted container logic |
| `src/phantasm/ai_gate.py` | Camera input, physical-key registration, ORB matching |
| `src/phantasm/web_server.py` | FastAPI Web UI/API |
| `src/phantasm/bridge_ui.py` | OpenCV status UI |
| `src/phantasm/emergency_daemon.py` | Panic trigger watcher and brick flow |
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
| `.state/store.bin` | Encrypted physical-key state blob |
| `.state/lock.bin` | Local key for physical-key state encryption |
| `.state/access.bin` | Local access key required to decrypt `vault.bin` |
| `.state/signal.key` | Panic trigger token |
| `.state/signal.trigger` | Panic trigger file |
| `.state/events.log` | Optional audit log |
| `.state/face.bin` | Optional encrypted WebUI face-lock template |
| `.state/face.enroll` | Short-lived first-time face enrollment request |

The default state directory is `.state/` and can be changed with `PHANTASM_STATE_DIR`. The directory is intended to be mode `0700`; secret files are intended to be mode `0600`. Neutral filenames reduce obvious metadata, but they do not provide deniability.

## 5. Profiles

| Display Name | Internal Mode | Purpose |
| --- | --- | --- |
| Profile A | `dummy` | First profile |
| Profile B | `secret` | Second profile |

The CLI accepts `--profile a` or `--profile b`. WebUI v2 maps these internal profiles to neutral protected-entry terminology and does not expose profile selectors during normal operation.

## 6. CLI

### Initialize

```bash
python3 main.py init
```

This rotates the local access key, overwrites `vault.bin` with random data, and leaves an empty container ready for new entries.

### Store

```bash
python3 main.py store --profile a --file path/to/file
python3 main.py store --profile b --file path/to/file
```

Store flow:

1. Start the camera gate.
2. Prompt for two different vault passwords: open and open+purge.
3. Register the physical key for the selected profile.
4. Read the input file.
5. Derive a key with Argon2id.
6. Encrypt the payload with AES-GCM into the profile's open slot.
7. Encrypt the same payload into the profile's open+purge slot using the same physical key and the second password.

### Retrieve

```bash
python3 main.py retrieve --out output.bin
```

Retrieve flow:

1. Start the camera gate.
2. Prompt for the vault password.
3. Verify the registered physical key.
4. Try Profile A open, Profile A open+purge, Profile B open, then Profile B open+purge.
5. Write or display the retrieved payload.
6. If the open password was used, keep the alternate profile intact by default.
7. If the open+purge password was used, silently purge the alternate profile after successful retrieval.
8. For open-password retrieval, purge the alternate profile only when the configured policy allows it.

`PHANTASM_PURGE_CONFIRMATION=0` disables the explicit confirmation phrase and purges the alternate profile after open-password retrieval. `PHANTASM_DURESS_MODE=1` automatically purges Profile B after a successful Profile A open-password retrieval. The open+purge password always purges the alternate profile after successful retrieval. These settings and passwords can cause data loss.

### Brick

```bash
python3 main.py brick
```

The brick flow destroys `.state/access.bin` first, then performs a best-effort overwrite of `vault.bin`. Flash media, snapshots, backups, and journaling filesystems may retain old data.

### Reset UI Face Lock

```bash
python3 main.py reset-face-lock
```

This CLI-only flow resets the optional WebUI face lock. It requires the typed confirmation phrase `RESET FACE LOCK AND VAULT`, removes the encrypted face-lock template, rotates the local access key, initializes `vault.bin`, clears physical-object bindings, clears active face-lock sessions, and creates a short-lived local enrollment request. This is destructive because changing the UI user invalidates the local trust boundary for the stored entries.

## 7. WebUI v2

Start the server:

```bash
PYTHONPATH=src python3 -m phantasm.web_server
```

The default bind address is `127.0.0.1:8000`.

WebUI v2 is server-rendered with lightweight JavaScript. It preserves the internal two-profile model while presenting normal operations as protected-entry workflows.

Normal navigation:

- Home
- Store
- Retrieve
- Maintenance

The Emergency view is available only by direct route and is not shown in normal navigation.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Home |
| `GET` | `/store` | Store screen |
| `GET` | `/retrieve` | Retrieve screen |
| `GET` | `/maintenance` | Maintenance screen |
| `GET` | `/maintenance/entries` | Entry management screen |
| `GET` | `/emergency` | Hidden emergency screen |
| `GET` | `/ui-lock` | Optional UI face-lock screen |
| `GET` | `/video_feed` | Camera stream for unlocked UI sessions |
| `GET` | `/status` | Neutral device/object status |
| `POST` | `/face/enroll` | Enroll or replace optional UI face lock |
| `POST` | `/face/verify` | Unlock optional UI face session |
| `POST` | `/face/lock` | Clear optional UI face session |
| `POST` | `/register_key` | Bind or rebind a physical object |
| `POST` | `/store` | Store a protected entry |
| `POST` | `/retrieve` | Retrieve and download the matching entry |
| `POST` | `/purge_other` | Hidden emergency clear action |
| `POST` | `/emergency/initialize` | Hidden emergency container initialization |
| `POST` | `/emergency/brick` | Hidden emergency brick action |
| `GET` | `/maintenance/diagnostics` | Local diagnostics |
| `POST` | `/maintenance/rotate_token` | Rotate Web mutation token |
| `POST` | `/maintenance/reset_session` | Reset local session counters |
| `GET` | `/maintenance/logs` | Export optional local audit log |

Mutating endpoints require `X-Phantasm-Token`. The token is generated on process start unless `PHANTASM_WEB_TOKEN` is set.

`/status` intentionally returns only neutral fields:

- `camera_ready`
- `object_state`
- `device_state`
- `local_mode`

The normal UI must not display internal profile names, internal retrieval order, or alternate-entry state after retrieval.

Emergency initialization rotates the local access key, overwrites `vault.bin` with a fresh empty container, and clears local object bindings. It is a destructive reset for normal reuse, distinct from emergency brick, which destroys the local access path first.

Optional UI face lock is enabled with `PHANTASM_UI_FACE_LOCK=1`. It gates access to normal WebUI routes with a short-lived local session cookie. Face templates are encrypted in the runtime state directory. This lock is not used in Argon2id input and does not participate in vault encryption or retrieval.

First-time face enrollment is disabled unless the WebUI process is started with `PHANTASM_UI_FACE_ENROLL=1` or a valid `.state/face.enroll` request exists. The setup flag is intended for device provisioning only. The enrollment request is created by `python3 main.py reset-face-lock`, is checked when `/ui-lock` is reloaded, and is removed after successful enrollment. When the UI is locked, `/status` returns a locked state without object-match details and `/video_feed` requires an unlocked UI session. The lock screen has a separate short-lived preview endpoint for enrollment and verification alignment; it is not the normal WebUI camera feed and expires automatically.

Face-lock reset is intentionally available only through the CLI. The WebUI can enroll, verify, and clear the current session, but it does not expose a route that resets the face template and container together.

## 8. Cryptography

The current format is GhostVault v3.

- No plaintext magic/header.
- Fixed-width profile spans.
- Each profile span contains an open slot and an open+purge slot.
- Per-record random salt and nonce.
- AES-GCM authenticated encryption.
- Filename and payload metadata are encrypted.
- v1/v2 compatibility retrieval has been removed.

Argon2id inputs:

- User password
- Physical-key token
- Profile mode
- Password role: open or open+purge
- Per-record random salt
- `.state/access.bin`
- Optional `PHANTASM_HARDWARE_SECRET_FILE`
- Optional `PHANTASM_HARDWARE_SECRET`
- Optional `PHANTASM_HARDWARE_SECRET_PROMPT`

Default Argon2id parameters are tuned for Raspberry Pi Zero 2 W class hardware: `memory_cost=32768`, `iterations=2`, `lanes=1`.

## 9. Physical-Key Matching

Phantasm extracts ORB features from camera frames.

Registration:

1. Capture several frames over a short interval.
2. Select the candidate with the most keypoints.
3. Reject low-feature images.
4. Reject candidates too similar to the other profile.
5. Store Profile A/B templates together in encrypted `.state/store.bin`.

Retrieval:

1. Extract ORB features from current frames.
2. Match against the encrypted reference templates.
3. Require enough good matches and homography inliers.
4. Require stable matching in at least 3 of the last 5 frames.
5. Reject ambiguous matches across both profiles.

The physical key is an operational gate, not a high-entropy cryptographic factor.

## 10. Runtime Policy

| Variable | Purpose | Default |
| --- | --- | --- |
| `PHANTASM_STATE_DIR` | Runtime state directory | `.state` |
| `PHANTASM_STATE_SECRET` | External secret for physical-key state encryption | unset |
| `PHANTASM_HARDWARE_SECRET_FILE` | External secret file mixed into Argon2id | unset |
| `PHANTASM_HARDWARE_SECRET` | External secret string mixed into Argon2id | unset |
| `PHANTASM_HARDWARE_SECRET_PROMPT` | Prompt for an external secret | unset |
| `PHANTASM_PURGE_CONFIRMATION` | Require explicit purge confirmation | `1` |
| `PHANTASM_DURESS_MODE` | Auto-purge Profile B after Profile A retrieval | `0` |
| `PHANTASM_WEB_TOKEN` | Web mutation token | random at start |
| `PHANTASM_HOST` | Web bind host | `127.0.0.1` |
| `PHANTASM_PORT` | Web bind port | `8000` |
| `PHANTASM_MAX_UPLOAD_BYTES` | Web upload limit | `26214400` |
| `PHANTASM_UI_FACE_LOCK` | Require local face check before WebUI use | `0` |
| `PHANTASM_UI_FACE_ENROLL` | Permit first-time face-lock enrollment during setup | `0` |
| `PHANTASM_UI_FACE_ENROLL_SECONDS` | Face enrollment request lifetime | `600` |
| `PHANTASM_UI_FACE_PREVIEW_SECONDS` | Lock-screen camera preview lifetime | `30` |
| `PHANTASM_UI_FACE_SESSION_SECONDS` | Face-unlocked UI session lifetime | `300` |
| `PHANTASM_AUDIT` | Enable audit logging | `0` |
| `PHANTASM_AUDIT_FILENAMES` | Record filename hashes | unset |

## 11. Testing

```bash
python3 -m unittest discover -s tests
```

KDF benchmark:

```bash
python3 scripts/bench_kdf.py
```

## 12. Compatibility

This build reads and writes GhostVault v3 only. Older v1/v2 containers must be retrieved with an older build and then stored again with this build.

## 13. Limits

Phantasm does not guarantee protection against a compromised OS, live memory capture, keylogging, camera observation, forced disclosure, complete secure deletion, deniability, or unsafe network exposure.
