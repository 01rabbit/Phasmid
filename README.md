# Phantasm

Phantasm is a local-only, coercion-aware secure-storage prototype. It explores how visible disclosure and protected local state can diverge when device seizure and compelled access are practical risks.

Phantasm is research software. It is not a replacement for full-disk encryption, hardware-backed key storage, an audited classified-data handling system, or a complete solution to compelled disclosure.

## What It Does

- Creates an encrypted `vault.bin` container.
- Stores protected entries in an internal two-slot container model.
- Uses object-image matching with ORB as an operational access cue.
- Encrypts payloads with AES-GCM and Argon2id-derived keys.
- Mixes a local access key into recovery so `vault.bin` alone is not enough.
- Supports normal access and restricted recovery behavior.
- Provides a CLI and a local WebUI v2.
- Provides owner-controlled restricted actions that can clear local state.

Phantasm does not promise perfect deniability. It reduces operational damage in some compelled-access scenarios by separating access conditions, local state, physical-object cues, and restricted recovery behavior.

## Philosophy

Phantasm follows a simple rule: no lies, no unnecessary truth.

The interface should report what the user needs to complete the current operation, but it should not reveal the internal disclosure model, storage structure, trial order, or restricted recovery behavior.

## Repository Layout

```text
.
├── main.py                  # Compatibility CLI launcher
├── src/phantasm/            # Application package
│   ├── cli.py
│   ├── gv_core.py
│   ├── ai_gate.py
│   ├── web_server.py
│   └── templates/
├── docs/                    # Specification and threat model
├── scripts/                 # Utility scripts
├── tests/                   # Unit tests
└── requirements.txt
```

Runtime files such as `vault.bin`, `.state/`, and audit logs are intentionally ignored by Git.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## CLI Usage

Initialize a container:

```bash
python3 main.py init
```

Store a file:

```bash
python3 main.py store --entry a --file path/to/file
python3 main.py store --entry b --file path/to/file
```

The CLI keeps a compact entry selector for compatibility. The WebUI uses neutral entry-based language and does not expose the internal storage model during normal operation.

Retrieve a file:

```bash
python3 main.py retrieve --out output.bin
```

Clear the local access path:

```bash
python3 main.py brick
```

Reset the optional UI face lock from the CLI:

```bash
python3 main.py reset-face-lock
```

This operation has no WebUI route. It requires the confirmation phrase `RESET FACE LOCK AND VAULT`, clears the enrolled face-lock template, rotates the local access key, initializes `vault.bin`, and clears physical-object bindings. Use it when the local UI user changes and stored data must be treated as no longer valid.

After a successful reset, Phantasm creates a short-lived local enrollment request. If the WebUI is already running, reload `/ui-lock` to register the new face lock.

## WebUI v2

```bash
PYTHONPATH=src python3 -m phantasm.web_server
```

Open `http://127.0.0.1:8000`.

WebUI v2 uses neutral entry-based terminology. Normal screens do not show internal storage labels, retrieval order, or restricted local-state behavior.

Navigation:

- `Home`: local device state, camera state, object state, and primary actions.
- `Store`: create or update a protected entry by selecting a file, entering an access password, and binding an object.
- `Retrieve`: unlock the matching local entry without choosing an internal slot.
- `Maintenance`: diagnostics, token rotation, audit state, log export, and entry management.
- `/emergency`: hidden route for restricted local actions with typed confirmation.

Restricted actions are not shown in normal navigation. Hidden routes are UX concealment only, so restricted actions also require the Web mutation token, an unlocked UI session when face lock is enabled, a fresh restricted confirmation, and a typed action phrase. The hidden restricted route initially renders only a confirmation screen.

Field Mode reduces Maintenance detail and other operational hints:

```bash
PHANTASM_FIELD_MODE=1 PYTHONPATH=src python3 -m phantasm.web_server
```

Field Mode is recommended for high-risk local appliance deployments. It reduces casual leakage but is not a security boundary.

Optional UI face lock:

```bash
PHANTASM_UI_FACE_LOCK=1 PYTHONPATH=src python3 -m phantasm.web_server
```

When enabled, the WebUI starts at `/ui-lock`. The face check only unlocks the local interface for a short session; it is not mixed into vault encryption or retrieval keys.

First-time face enrollment is an explicit setup mode:

```bash
PHANTASM_UI_FACE_LOCK=1 PHANTASM_UI_FACE_ENROLL=1 PYTHONPATH=src python3 -m phantasm.web_server
```

Use setup mode only while provisioning the device. Normal locked sessions withhold the main object-matching preview until the UI is unlocked. The lock screen shows a local camera preview for enrollment and verification alignment without exposing the normal object-matching UI.

## Object Matching

Object-image matching is an operational access cue layered on top of password-based cryptographic recovery. It is not high-entropy cryptographic key material and is not a substitute for strong passwords, key management, or secure operational procedure.

Matching can fail because of lighting, camera quality, object orientation, motion blur, or ambiguous objects. Failure messages are intentionally neutral.

## Metadata Awareness

The Store screen includes a local metadata risk check. It can warn when a file appears to contain GPS-like fields, camera or author metadata, creator application fields, embedded thumbnails, local path leakage, or original filename context.

The optional metadata reduction path is best-effort, local-only, and conservative. It does not overwrite the original file and does not claim forensic-grade sanitization.

## Runtime State

By default, Phantasm writes runtime state to `.state/`:

- `store.bin`: encrypted object-cue state blob
- `lock.bin`: state encryption key
- `access.bin`: local access key required for vault retrieval
- `signal.key` / `signal.trigger`: panic trigger files
- `events.log`: optional audit log
- `face.bin`: optional encrypted WebUI face-lock template
- `face.enroll`: short-lived first-time face enrollment request

Override the state location with:

```bash
PHANTASM_STATE_DIR=/path/to/state python3 main.py init
```

## Important Environment Variables

| Variable | Purpose |
| --- | --- |
| `PHANTASM_STATE_DIR` | Runtime state directory |
| `PHANTASM_STATE_SECRET` | External value for object-cue state encryption |
| `PHANTASM_HARDWARE_SECRET_FILE` | External value file mixed into Argon2id |
| `PHANTASM_HARDWARE_SECRET_PROMPT=1` | Prompt for an external value |
| `PHANTASM_PURGE_CONFIRMATION=0` | Disable explicit confirmation for configured recovery behavior |
| `PHANTASM_DURESS_MODE=1` | Enable opt-in access-triggered local-state update |
| `PHANTASM_WEB_TOKEN` | Web mutation token |
| `PHANTASM_UI_FACE_LOCK=1` | Require local face check before using the WebUI |
| `PHANTASM_UI_FACE_ENROLL=1` | Permit first-time WebUI face-lock enrollment during setup |
| `PHANTASM_UI_FACE_ENROLL_SECONDS` | Face enrollment request lifetime |
| `PHANTASM_UI_FACE_SESSION_SECONDS` | Face-unlocked UI session lifetime |
| `PHANTASM_RESTRICTED_SESSION_SECONDS` | Restricted confirmation lifetime |
| `PHANTASM_FIELD_MODE=1` | Reduce normal WebUI operational detail |
| `PHANTASM_AUDIT=1` | Enable audit logging |

## Local-Only Trust Boundary

Phantasm is intended for localhost or USB Ethernet gadget access. It should not be exposed to an untrusted network and should not be deployed as an Internet-facing service. Remote management, telemetry, cloud unlock, and analytics are intentionally out of scope.

Restricted local data-loss behavior should be understood primarily as key-material destruction and local access-path invalidation. Best-effort overwrite may be attempted, but SD card behavior means overwrite must not be treated as guaranteed secure deletion.

For high-risk deployments, do not store all recovery conditions on the same physical medium. Phantasm is strongest when the encrypted container, local state, memorized password, physical-object cue, and optional external key material are separated.

## Test

```bash
python3 -m unittest discover -s tests
```

KDF benchmark:

```bash
python3 scripts/bench_kdf.py
```

## Documentation

- [Specification](docs/SPECIFICATION.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [Raspberry Pi Zero 2 W Deployment](docs/RPI_ZERO_DEPLOYMENT.md)
- [Raspberry Pi Zero 2 W Appliance Deployment](docs/RPI_ZERO_APPLIANCE_DEPLOYMENT.md)
- [Source-Safe Storage Workflow](docs/SOURCE_SAFE_WORKFLOW.md)
- [Seizure Review Checklist](docs/SEIZURE_REVIEW_CHECKLIST.md)
- [Field Test Procedure](docs/FIELD_TEST_PROCEDURE.md)

## Security Notes

Phantasm does not guarantee protection against a compromised host, live memory capture, keylogging, camera observation, shoulder surfing, active surveillance, forced disclosure, forensic analysis of the entire device, complete secure deletion, or unsafe network exposure.

It is not a replacement for audited full-disk encryption, hardware-backed key storage, or formal classified-data handling systems.
