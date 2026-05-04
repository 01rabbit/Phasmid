# Phasmid

<p align="center">
  <img src="images/Phasmid_logo.png" alt="Phasmid logo" width="200">
</p>

Phasmid is a field-evaluation prototype for local-only coercion-aware storage.

It is the reference implementation of the Janus Eidolon System, a two-slot local storage architecture designed to separate visible disclosure from protected local state under practical risks such as device seizure, compelled access, and over-disclosure.

Phasmid is research software. It is not a replacement for full-disk encryption, hardware-backed key storage, an audited classified-data handling system, or a complete solution to compelled disclosure.

## What It Does

- Creates an encrypted `vault.bin` container.
- Stores protected entries in an internal two-slot container model.
- Uses object-image matching with ORB as an operational access cue.
- Encrypts payloads with AES-GCM and Argon2id-derived keys.
- Mixes a local access key into recovery so `vault.bin` alone is not enough.
- Supports normal access and restricted recovery behavior.
- Provides a CLI and a local WebUI v2.
- Provides owner-controlled restricted actions that can clear local state.
- Includes metadata risk check workflows for metadata-reduced copy review.
- Metadata detection and reduction are best-effort.

Phasmid does not promise perfect deniability. It reduces operational damage in some compelled-access scenarios by separating access conditions, local state, physical-object cues, and restricted recovery behavior.

## Philosophy

Phasmid follows a simple rule: no lies, no unnecessary truth.

The interface should report what the user needs to complete the current operation, but it should not reveal the internal disclosure model, storage structure, trial order, or restricted recovery behavior.

Honest interface. Silent structure.

Phasmid is not field-proven until it has been validated on target hardware with the Field Test Procedure and Seizure Review Checklist.

## When to Use Phasmid

Use Phasmid when the problem is not merely file encryption, but compelled access, device seizure, over-disclosure, metadata risk, or local UI/log leakage.

If your only requirement is normal file encryption on a trusted device, a mature full-disk encryption system, password manager, or audited file-encryption tool may be more appropriate.

Phasmid is intentionally specialized. It is not designed to be the simplest way to encrypt files.

## From Prototype to Solution

Phasmid should not become a stronger product by claiming more. It becomes stronger by making its operating boundary repeatable, testable, and boring.

The path from field-evaluation prototype to operational solution is:

1. keep the scope local-only;
2. keep the interface quiet under capture;
3. provide a reproducible appliance deployment;
4. complete target-hardware field testing;
5. complete seizure-review testing;
6. record validation results for each release;
7. publish only claims that are covered by tests or documented limits.

Run the WebUI in Field Mode by setting `PHASMID_FIELD_MODE=1`. Field Mode reduces normal exposure in capture-visible workflows, but it is not a security boundary. Field Mode is not a security boundary.

Until those validation gates are completed on target hardware, Phasmid should be described as a field-evaluation prototype. After those gates are completed and recorded, it can be described as a local coercion-aware storage appliance for the validated deployment conditions.

## Safe Use Boundary

Phasmid is intended for lawful local protection of sensitive material where device seizure, compelled access, or over-disclosure are realistic risks.

It is appropriate for:

- source-protection workflows,
- temporary field notes,
- research material,
- travel-sensitive files,
- local-only controlled disclosure experiments,
- defensive security research.

It is not intended for:

- covert communication,
- surveillance evasion,
- censorship bypass,
- remote wipe,
- remote unlock,
- offensive operations,
- malware storage,
- illegal concealment,
- replacing organizational classified-data systems.

## Government and Organizational Use Boundary

Phasmid is not approved classified-data handling infrastructure. It does not replace organizational records-management systems, certified encryption products, HSM-backed key management, full-disk encryption, or formal classified-data procedures.

Use of Phasmid in government or organizational environments must follow applicable law, policy, records-retention requirements, and classification rules. Phasmid is intended for local field-evaluation and harm-reduction workflows, not as a substitute for approved systems of record.

## Reviewer Notes and Known Limits

Phasmid is intentionally narrow.

Configurable runtime parameters include `PHASMID_FIELD_MODE=1`, `PHASMID_MIN_PASSPHRASE_LENGTH`, and `PHASMID_ACCESS_MAX_FAILURES`.

Operational review and deployment guidance can be found in:

- `docs/SOURCE_SAFE_WORKFLOW.md`
- `docs/SEIZURE_REVIEW_CHECKLIST.md`
- `docs/FIELD_TEST_PROCEDURE.md`
- `docs/REVIEW_VALIDATION_RECORD.md`
- `docs/SOLUTION_READINESS_PLAN.md`
- `docs/JANUS_EIDOLON_SYSTEM.md`
- `docs/PHASMID_ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `docs/RESTRICTED_ACTIONS.md`
- `docs/STATE_RECOVERY.md`

This README is part of the authoritative appliance deployment guide and review workflow. Release Review Artifacts are generated by the CI pipeline to support review. This is not a validated cryptographic-module certification.

Phasmid does not provide:

- perfect deniability,
- guaranteed secure deletion,
- protection against compromised hosts,
- protection against malware or keyloggers,
- protection against live memory capture,
- protection against camera observation,
- protection against coercion after disclosure,
- certified classified-data handling,
- remote management,
- communications security,
- anonymity,
- censorship bypass,
- surveillance evasion.

## Repository Layout

```text
.
├── main.py                  # Local CLI launcher
├── src/phasmid/            # Application package
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
phasmid init
```

Store a file:

```bash
phasmid store --entry a --file path/to/file
phasmid store --entry b --file path/to/file
```

The CLI keeps a compact entry selector. The WebUI uses neutral entry-based language and does not expose the internal storage model during normal operation.

Retrieve a file:

```bash
phasmid retrieve --out output.bin
```

Clear the local access path:

```bash
phasmid brick
```

Reset the optional UI face lock from the CLI:

```bash
phasmid reset-face-lock
```

This operation has no WebUI route. It requires the confirmation phrase `RESET FACE LOCK AND VAULT`, clears the enrolled face-lock template, rotates the local access key, initializes `vault.bin`, and clears physical-object bindings. Use it when the local UI user changes and stored data must be treated as no longer valid.

After a successful reset, Phasmid creates a short-lived local enrollment request. If the WebUI is already running, reload `/ui-lock` to register the new face lock.

Local operations checks:

```bash
phasmid verify-state
phasmid verify-audit-log
phasmid doctor
phasmid export-redacted-log --out review-events.jsonl
```

These commands report neutral readiness and audit-review status without printing local paths in normal output.

New local state checks use a typed state-store helper for atomic writes, restrictive permissions, and transition validation. Existing vault and object-cue state files remain managed by their owning modules until a documented state migration replaces them.

When audit logging is enabled, new audit records include sequence and integrity fields for local review. Audit logging remains disabled by default because audit records can create additional local metadata.

## WebUI v2

```bash
PYTHONPATH=src python3 -m phasmid.web_server
```

Open `http://127.0.0.1:8000`.

WebUI v2 uses neutral entry-based terminology. Normal screens do not show internal storage labels, retrieval order, or restricted local-state behavior.

Common WebUI/API wording is centralized where practical so terminology checks can audit capture-visible messages consistently.

## Test Command

```bash
python3 -m unittest discover -s tests
python3 -m black --check src tests scripts
python3 -m bandit -r src
```

Static check commands:

```bash
python3 -m black --check src tests scripts
python3 -m bandit -r src
```

Coverage command:

```bash
python3 -m coverage run --source=src -m unittest discover -s tests
python3 -m coverage report -m
```

Alternative short coverage command:

```bash
coverage run -m unittest discover -s tests
coverage report
```

Release Review Artifacts are generated by the CI pipeline and support review of the current branch.

Passing automated tests do not prove field safety. They verify expected local behavior and regression boundaries only.

## License

Phasmid is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).

Third-party dependency licenses are listed in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

Phasmid is research software. The license grants software-use rights; it does not imply operational approval, field validation, classified-data handling approval, or suitability for any specific deployment.
