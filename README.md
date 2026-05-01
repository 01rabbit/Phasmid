# Phantasm

Phantasm is a local secure-storage prototype that combines an encrypted container, a password, and a camera-recognized physical object profile. It is designed for local operation, including USB gadget mode or localhost access.

Phantasm is research software. It is not a replacement for full-disk encryption, a hardware security module, or an audited secrets-management system.

## What It Does

- Creates an encrypted `vault.bin` container.
- Stores separate Profile A and Profile B payloads.
- Uses a camera-based physical key as an additional operational gate.
- Encrypts payloads with AES-GCM and Argon2id-derived keys.
- Uses a local access key so `vault.bin` alone is not enough to decrypt data.
- Supports separate open and open+purge passwords for the same physical-key profile.
- Provides a CLI and local WebUI v2.
- Supports an emergency brick flow that destroys the local access key first.

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

Initialization rotates the local access key and clears the container for new entries.

Store a file:

```bash
python3 main.py store --profile a --file path/to/file
python3 main.py store --profile b --file path/to/file
```

The store flow asks for two different passwords. The open password decrypts the selected profile and leaves the alternate profile intact. The open+purge password decrypts the selected profile and silently purges the alternate profile after successful retrieval. Both passwords use the same registered physical object for that profile.

Retrieve a file:

```bash
python3 main.py retrieve --out output.bin
```

Brick the local access path:

```bash
python3 main.py brick
```

Reset the optional UI face lock from the CLI:

```bash
python3 main.py reset-face-lock
```

This operation has no WebUI route. It requires the confirmation phrase `RESET FACE LOCK AND VAULT`, clears the enrolled face-lock template, rotates the local access key, initializes `vault.bin`, and clears physical-object bindings. Use it when the local UI user changes and the stored vault data must be treated as no longer valid.

## Web UI

```bash
PYTHONPATH=src python3 -m phantasm.web_server
```

Open `http://127.0.0.1:8000`.

WebUI v2 uses neutral entry-based terminology during normal operation. The internal two-profile model remains, but the UI does not expose profile names or retrieval order.

Navigation:

- `Home`: local device state, camera state, object state, and primary actions.
- `Store`: create or update a protected entry by selecting a file, entering an access password, and binding an object.
- `Retrieve`: unlock the matching local entry without choosing an internal profile.
- `Maintenance`: diagnostics, token rotation, audit state, log export, and entry management.
- `/emergency`: hidden route for destructive local actions with typed confirmation.

Optional UI face lock:

```bash
PHANTASM_UI_FACE_LOCK=1 PYTHONPATH=src python3 -m phantasm.web_server
```

When enabled, the WebUI starts at `/ui-lock`. The face check only unlocks the local interface for a short session; it is not mixed into vault encryption or retrieval keys.

Face-lock reset is intentionally CLI-only because it also resets the local container and object bindings.

The hidden Emergency page includes:

- clear unmatched entry
- initialize local container
- emergency brick

`Initialize local container` rotates the local access key, resets `vault.bin`, and clears object bindings so both protected entries are empty and ready for new registration.

## Runtime State

By default, Phantasm writes runtime state to `.state/`:

- `store.bin`: encrypted physical-key state blob
- `lock.bin`: state encryption key
- `access.bin`: local access key required for vault retrieval
- `signal.key` / `signal.trigger`: panic trigger files
- `events.log`: optional audit log
- `face.bin`: optional encrypted WebUI face-lock template

Override the state location with:

```bash
PHANTASM_STATE_DIR=/path/to/state python3 main.py init
```

## Important Environment Variables

| Variable | Purpose |
| --- | --- |
| `PHANTASM_STATE_DIR` | Runtime state directory |
| `PHANTASM_STATE_SECRET` | External secret for physical-key state encryption |
| `PHANTASM_HARDWARE_SECRET_FILE` | External secret file mixed into Argon2id |
| `PHANTASM_HARDWARE_SECRET_PROMPT=1` | Prompt for an external secret |
| `PHANTASM_PURGE_CONFIRMATION=0` | Disable explicit purge confirmation for open-password retrieval |
| `PHANTASM_DURESS_MODE=1` | Auto-purge Profile B after Profile A retrieval |
| `PHANTASM_UI_FACE_LOCK=1` | Require local face check before using the WebUI |
| `PHANTASM_UI_FACE_SESSION_SECONDS` | Face-unlocked UI session lifetime |
| `PHANTASM_AUDIT=1` | Enable audit logging |

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

## Security Notes

Phantasm does not guarantee protection against a compromised host, live memory capture, keylogging, camera observation, forced disclosure, complete secure deletion, or unsafe network exposure. Read the threat model before relying on it for sensitive work.
