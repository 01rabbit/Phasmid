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
- Provides a CLI and local Web UI.
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

## Web UI

```bash
PYTHONPATH=src python3 -m phantasm.web_server
```

Open `http://127.0.0.1:8000`.

## Runtime State

By default, Phantasm writes runtime state to `.state/`:

- `store.bin`: encrypted physical-key state blob
- `lock.bin`: state encryption key
- `access.bin`: local access key required for vault retrieval
- `signal.key` / `signal.trigger`: panic trigger files
- `events.log`: optional audit log

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
