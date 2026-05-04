# AGENTS.md

<<<<<<< HEAD
> **Notice**: This file is the primary context entry point for AI-assisted development.
> It defines the project boundaries, security invariants, and the current roadmap.

## 0. Quick Start for AI Agents
1. **Identify the Task**: Match your task to a domain in the [Canonical Source Map](#2-canonical-source-map).
2. **Load Minimal Context**: Load only the files and documentation sections listed for that domain.
3. **Verify Invariants**: Check your proposed changes against the [Core Invariants](#3-core-invariants).
4. **Follow Language Rules**: Ensure all user-visible text follows [Neutral Language Rules](#4-user-facing-language-rules).
5. **Run Tests**: Execute the relevant tests and static analysis.

---

## 1. Project Status & Roadmap

### 🚩 Current Focus: Hardening & Modularity
The goal is to transition from a "field-evaluation prototype" to a "local appliance solution" by strengthening boundaries and improving testability.

### 🛤 Roadmap (Next Priority Issues)
1.  **#26 Split Vault Core**: Refactor `gv_core.py` into reviewable modules (IO, Crypto, Policy).
    *   *Reference*: `docs/CRYPTO_MODULE_DESIGN.md`
2.  **#19 Multi-source KDF**: Design and implement a pipeline for mixing local device-binding inputs into the KDF.
3.  **#16 Integrity Manifest**: Implement a workflow for generating signed release manifests and SBOMs.
4.  **#27 AI Gate Decoupling**: Separate camera handling, object matching, and face lock logic.

### ✅ Completed Milestones
-   `#8` & `#9`: CI pipeline with static analysis (`ruff`, `mypy`) and 70% coverage gate.
-   `#22`: Centralized restricted action policy enforcement.
-   `#23`: Typed local state store with atomic transitions.
-   `#24`: Local coercion scenario matrix and restricted-flow tests.
-   `#25`: Centralized user-visible strings in `strings.py`.
-   `#29`: Local operations commands (`doctor`, `verify-state`) and documentation alignment.

---

## 2. Canonical Source Map

| Domain | Key Source Files | Key Documentation | Relevant Issues |
| :--- | :--- | :--- | :--- |
| **Cryptography** | `gv_core.py`, `crypto_boundary.py` | `SPECIFICATION.md` (11, 15), `THREAT_MODEL.md` | #4, #5, #10, #19, #26 |
| **WebUI / API** | `web_server.py`, `templates/` | `SPECIFICATION.md` (7-9), `THREAT_MODEL.md` | #3, #7, #15, #21 |
| **CLI / Main** | `main.py`, `cli.py` | `SPECIFICATION.md` (6), `OPERATIONS.md` | #4, #6, #7, #11, #29 |
| **Biometrics / AI**| `ai_gate.py`, `face_lock.py` | `SPECIFICATION.md` (12), `THREAT_MODEL.md` | #20, #27, #28 |
| **State / Config** | `config.py`, `state_store.py` | `STATE_RECOVERY.md`, `DEPLOYMENT.md` | #12, #13, #17, #23 |
| **Metadata** | `metadata.py` | `SPECIFICATION.md` (10) | #24, #25 |
| **Audit / Logs** | `audit.py`, `operations.py` | `THREAT_MODEL.md` | #2, #16, #29 |
| **CI / Testing** | `tests/`, `.github/workflows/` | `REVIEW_VALIDATION_RECORD.md` | #9, #16 |

---

## 3. Core Invariants
*Preserve these unless an explicit Threat Model update is requested.*

- **Local-Only**: No cloud, no telemetry, binds to `127.0.0.1`.
- **Deniable Access**: `vault.bin` + password is insufficient without local state (`lock.bin`).
- **Access Cues**: Object matching is a *cue*, not a cryptographic key. Never treat low-entropy biometric data as high-entropy secrets.
- **Neutral Language**: UI/CLI must not reveal internal semantics (dummy/secret, real/fake, decoy).
- **Hardened Actions**: Restricted actions (e.g., `brick`) require server-side checks and short-lived confirmation.
- **Quiet Mode**: "Field Mode" must reduce casual exposure without creating detectable timing or error differences.

---

## 4. User-Facing Language Rules

| Prefer | Avoid |
| :--- | :--- |
| Protected entry, Local entry | Dummy, Secret, Hidden slot |
| Object cue, Access cue | Biometric proof, Image key |
| Key-path invalidation, Access-path clearing | Secure delete, Self-destruct, Wipe |
| Restricted local update | Panic password, Duress password |
| Metadata risk, Metadata reduction | Sanitization, Unbreakable, Military grade |

---

## 5. Operational Discipline

### AI Context Management
- Load only the **minimal set of files** required for the current domain.
- Do not initiate broad repository-wide rewrites.
- Check `ruff` and `mypy` before submitting any Python changes.

### Change & Test Strategy
- **Surgical Edits**: Use `replace` instead of `write_file` for large files.
- **Verification**: Always run `python3 -m unittest discover -s tests` after changes.
- **No Regressions**: Ensure coverage stays above **70%**.

---

## 6. Scope & Authority
1. `docs/THREAT_MODEL.md`: Controls security assumptions and risks.
2. `docs/SPECIFICATION.md`: Controls behavior and implementation contracts.
3. `README.md`: Controls project summary and installation.
4. `AGENTS.md`: This file (Development Guidance only).
=======
## Purpose

This file is the first context entry point for AI-assisted development in this repository.

Phantasm is a field-evaluation prototype for local-only coercion-aware storage. It explores lawful local protection of sensitive material where device seizure, compelled access, over-disclosure, metadata risk, and local UI/log leakage are practical risks.

Phantasm is research software. It is not a replacement for full-disk encryption, hardware-backed key storage, an audited classified-data handling system, organizational records-management systems, or a complete solution to compelled disclosure.

Use this file to keep AI-assisted changes small, scoped, and consistent with the project boundary.

## Project Boundary

Preserve this boundary in code, documentation, tests, and UI behavior:

- local-only operation by default
- protected entries stored in `vault.bin`
- local runtime state under `.state/` or `PHANTASM_STATE_DIR`
- password-based cryptographic recovery
- Argon2id-derived keys
- AES-GCM authenticated encryption
- local access key material mixed into recovery
- object-image matching as an operational access cue
- optional UI face lock as a local interface gate
- neutral WebUI and CLI language
- restricted local actions with explicit confirmation
- best-effort local access-path invalidation
- target-hardware field evaluation before stronger claims

Do not expand Phantasm into remote management, cloud recovery, telemetry, covert communication, censorship bypass, surveillance evasion, malware storage, offensive operations, or classified-data handling infrastructure.

## Non-Negotiable Security Claims

Do not claim that Phantasm provides:

- perfect deniability
- guaranteed secure deletion
- protection against compromised hosts
- protection against malware or keyloggers
- protection against live memory capture
- protection against camera observation
- protection against physical coercion after disclosure
- certified classified-data handling
- formal compliance approval
- anonymity
- covert communication
- censorship bypass
- surveillance evasion
- remote wipe
- remote unlock
- remote attestation
- tamper-proof audit logging
- protection on untrusted networks

When discussing deletion, restricted recovery, panic behavior, bricking, or emergency actions, describe the behavior as:

- local access-path clearing
- key-material destruction
- key-path invalidation
- restricted local update
- best-effort overwrite

Never describe it as guaranteed secure deletion.

## Core Invariants

Preserve these invariants unless a change explicitly updates the threat model, specification, tests, and user-facing documentation.

- The system is local-only by default.
- The WebUI binds to `127.0.0.1` by default.
- `vault.bin` alone should not be enough for normal recovery when required local state is absent.
- The local access key remains part of the recovery path unless a documented migration changes the container format.
- Object matching is an operational access cue, not cryptographic key material.
- ORB descriptors, image coordinates, face templates, and camera frames must not be described as high-entropy secrets.
- UI face lock is a local interface gate only and must not be treated as vault encryption.
- Hidden routes are UX concealment only, not access control.
- Field Mode reduces casual local exposure but is not a security boundary.
- Restricted actions must require server-side checks, short-lived restricted confirmation, and typed confirmation where applicable.
- Normal UI and CLI flows must not reveal internal storage labels, trial order, restricted recovery behavior, or alternate protected state.
- Capture-visible surfaces must use neutral language.
- Audit logging remains optional and must not record passwords, payload bytes, plaintext filenames, internal entry semantics, or disclosure structure.
- Metadata reduction is best-effort and must not be described as complete sanitization.
- Passing automated tests does not prove field safety.

## Canonical Source Map

Load only the relevant files for the requested change. Do not load the whole repository by default.

### Cryptography, Container Format, and Key Path

Use this context for changes involving `vault.bin`, GhostVault, Argon2id, AES-GCM, salts, nonces, local access key material, span layout, record parsing, restricted recovery slots, destructive behavior, or migration:

- `src/phantasm/gv_core.py`
- `docs/SPECIFICATION.md`, especially sections 11 and 15
- `docs/THREAT_MODEL.md`
- `tests/test_gv_core.py` and related tests

Relevant issues:

- `#4` cryptographic erase and local access-path invalidation
- `#5` Argon2id + HKDF-SHA-256 migration
- `#10` cryptographic module boundary and startup self-tests
- `#19` local multi-source key derivation pipeline
- `#26` vault cryptographic core split

### WebUI, API Routes, and Restricted Actions

Use this context for changes involving FastAPI routes, Web mutation token, restricted confirmation, hidden routes, Field Mode, face lock sessions, store/retrieve routes, maintenance routes, emergency routes, response headers, or neutral download filenames:

- `src/phantasm/web_server.py`
- `src/phantasm/templates/`
- `docs/SPECIFICATION.md`, especially sections 7, 8, and 9
- `docs/THREAT_MODEL.md`
- `tests/test_web_server.py` and related tests

Relevant issues:

- `#3` observable differences in restricted recovery flows
- `#7` authentication attempt limiting and backoff
- `#15` WebUI security headers and CSRF review
- `#21` deployment profiles and capability table
- `#22` restricted action policy enforcement
- `#24` local coercion and restricted-flow scenario matrix
- `#25` user-visible UI and CLI strings

### CLI Behavior

Use this context for changes involving `main.py`, command syntax, CLI output, confirmations, retrieve/store/init/brick/reset-face-lock behavior, or CLI terminology:

- `main.py`
- `src/phantasm/cli.py`
- `docs/SPECIFICATION.md`, especially section 6
- `docs/THREAT_MODEL.md`
- `tests/test_cli.py` and related tests

Relevant issues:

- `#4` cryptographic erase and local access-path invalidation
- `#6` access passphrase policy and strength checks
- `#7` authentication attempt limiting and backoff
- `#11` process hardening and secure memory best-effort support
- `#25` user-visible UI and CLI strings
- `#29` local operations commands and docs alignment

### Object Cue, Camera Matching, and Face Lock

Use this context for changes involving ORB matching, camera capture, object cue registration, match ambiguity, stable multi-frame matching, face template enrollment, or UI lock behavior:

- `src/phantasm/ai_gate.py`
- `src/phantasm/face_lock.py`
- `docs/SPECIFICATION.md`, especially section 12
- `docs/THREAT_MODEL.md`
- related tests in `tests/`

Relevant issues:

- `#20` multi-object cue and visual sequence matching
- `#27` split camera, object cue, and face UI lock responsibilities
- `#28` local dual-passphrase approval flow, if face-lock replacement is affected

### Metadata Handling

Use this context for changes involving metadata risk detection, metadata reduction, uploads, in-memory processing, file type support, original filename handling, or neutral metadata-reduced downloads:

- `src/phantasm/metadata.py`
- `src/phantasm/web_server.py` metadata routes
- `docs/SPECIFICATION.md`, especially section 10
- `docs/THREAT_MODEL.md`
- related tests in `tests/`

Relevant issues:

- `#24` scenario matrix
- `#25` user-visible UI and CLI strings

### Audit Logging

Use this context for changes involving event logs, audit record shape, hash chains, HMACs, log export, audit filenames, event names, or audit metadata:

- `src/phantasm/audit.py`
- `src/phantasm/web_server.py` maintenance log export
- `docs/THREAT_MODEL.md`
- `docs/SPECIFICATION.md`
- related tests in `tests/`

Relevant issues:

- `#2` hash-chained audit log integrity checks
- `#16` release integrity manifest and SBOM workflow
- `#29` local operations commands and docs alignment

### Local State and Deployment Posture

Use this context for changes involving `.state/`, state file names, state permissions, typed state, tmpfs, LUKS, deployment profile, appliance setup, service hardening, runtime secrets, or Raspberry Pi deployment:

- `src/phantasm/config.py`
- `docs/RPI_ZERO_APPLIANCE_DEPLOYMENT.md`
- `docs/RPI_ZERO_DEPLOYMENT.md`
- `docs/FIELD_TEST_PROCEDURE.md`
- `docs/SEIZURE_REVIEW_CHECKLIST.md`
- `docs/REVIEW_VALIDATION_RECORD.md`
- `docs/SOLUTION_READINESS_PLAN.md`
- related tests in `tests/`

Relevant issues:

- `#11` process hardening and secure memory best-effort support
- `#12` volatile local key-material store using tmpfs
- `#13` local device-binding inputs
- `#17` optional LUKS layer
- `#18` restricted recovery observability on target hardware
- `#21` deployment profiles and capability table
- `#23` typed local state store and transition checks
- `#29` local operations commands and docs alignment

### Testing, CI, Coverage, and Release Review

Use this context for changes involving tests, CI, static analysis, coverage, release validation, SBOMs, manifests, or review records:

- `tests/`
- `.github/workflows/`
- `pyproject.toml`
- `requirements-dev.txt`
- `scripts/`
- `docs/REVIEW_VALIDATION_RECORD.md`
- `docs/SOLUTION_READINESS_PLAN.md`
- `README.md`

Relevant issues:

- `#16` release integrity manifest and SBOM workflow
- `#24` scenario matrix

## Documentation Authority

When documents overlap, use this authority order:

1. `docs/THREAT_MODEL.md` controls security assumptions, residual risks, and safety boundaries.
2. `docs/SPECIFICATION.md` controls intended behavior and implementation contracts.
3. `README.md` controls public-facing project summary, installation, usage, and known limits.
4. Deployment documents control appliance setup and operational procedures.
5. Field test and seizure review documents control validation procedure and review evidence.
6. Issue descriptions describe planned work but do not override merged documentation.

Do not silently resolve contradictions. If code, tests, README, specification, threat model, and issue text conflict, state the conflict and update the affected artifacts in the same change when appropriate.

## User-Facing Language Rules

Use neutral terms in WebUI, CLI output, logs, response bodies, headers, filenames, documentation examples, and tests that assert visible text.

Prefer:

- protected entry
- local entry
- object cue
- access cue
- local access path
- restricted confirmation
- restricted local update
- key material
- key-path invalidation
- best-effort overwrite
- metadata risk
- local-only operation
- Field Mode
- UI face lock
- object cue accepted
- no valid entry found
- local container initialized

Avoid in normal user-facing surfaces:

- dummy
- secret
- hidden slot
- real
- fake
- decoy
- purge slot
- trial order
- alternate state
- duress password
- panic password
- self-destruct
- dead man switch
- secure delete
- biometric proof
- authenticated by object
- classified approved
- military grade
- unbreakable
- deniable encryption

Internal implementation names may remain in code when necessary, but normal capture-visible behavior should stay neutral.

## Capture-Visible Surface Rule

Before changing any of the following, check whether the change reveals internal disclosure structure:

- WebUI text
- HTML templates
- JavaScript console messages
- API responses
- response headers
- download filenames
- CLI output
- shell-visible messages
- systemd stdout or stderr
- audit events
- exported logs
- diagnostics
- browser-visible routes
- documentation copied to a deployed device
- tests that encode user-visible strings

Do not reveal during normal operation:

- internal slot labels
- internal retrieval order
- restricted recovery side effects
- alternate protected state
- object binding internals
- local state paths in Field Mode before restricted confirmation
- original filenames where neutral filenames are required
- whether a failure was caused by password, object cue, local state, restricted policy, or internal candidate mismatch, unless required for safe operation

## AI Context Discipline

For any AI-assisted task:

1. Identify the affected domain using the Canonical Source Map.
2. Load only the relevant source files, tests, and document sections.
3. State which core invariants the change touches.
4. Make the smallest safe change.
5. Update tests when behavior changes.
6. Update documentation when behavior, claims, terminology, or operational assumptions change.
7. Avoid broad repository-wide rewrites unless explicitly required.
8. Do not combine unrelated refactors with security-sensitive behavior changes.
9. Do not change cryptographic behavior and UI language in the same patch unless the issue explicitly requires it.
10. Do not modify container compatibility without a documented migration or compatibility plan.

## Current Issue Priority Guidance

When choosing the next work item, prefer changes that reduce future risk and AI context cost before making compatibility-sensitive cryptographic changes.

Recommended order:

1. Add or maintain this `AGENTS.md`.
2. `#24` add local coercion and restricted-flow scenario matrix. ✅ Complete
3. `#23` introduce typed local state store and transition checks. ✅ Complete
4. `#26` split vault cryptographic core into reviewable modules. ✅ Complete
5. `#19` design local multi-source key derivation pipeline.

Completed implementations:
- `#8` CI and static analysis gates ✅
- `#9` coverage gating and operational procedure testing ✅
- `#22` centralized restricted action policy ✅
- `#25` centralized user-visible strings ✅
- `#26` split vault cryptographic core into reviewable modules ✅
- `#29` local operations commands and docs alignment ✅


## Testing Expectations

Run or update tests when changing:

- cryptography or container format
- KDF inputs
- local access key behavior
- state file layout
- Web mutation authorization
- restricted confirmation
- restricted actions
- Field Mode visibility
- face lock behavior
- object cue behavior
- metadata checking or scrubbing
- audit output
- UI terminology
- CLI terminology
- destructive or restricted operations
- diagnostics
- response headers
- download filenames

Default test command:

```bash
python3 -m unittest discover -s tests
```

KDF benchmark command:

```bash
python3 scripts/bench_kdf.py
```

Passing automated tests do not prove field safety. They verify implementation contracts only. Field safety still requires target-hardware field testing and seizure review.

## Change Discipline

Make small, reviewable changes.

Do not:

- add telemetry
- add cloud dependencies
- add remote unlock
- add remote wipe
- expose the WebUI to untrusted networks by default
- weaken local-only defaults
- weaken typed confirmations
- weaken short-lived restricted sessions
- weaken Web mutation token checks
- weaken upload limits
- weaken neutral error behavior
- increase Field Mode diagnostic detail before restricted confirmation
- introduce compliance, certification, or field-proven claims without validation records
- silently break existing v3 containers
- silently migrate stored data
- store all recovery conditions on the same medium by default
- add custom threshold cryptography without review and test vectors
- treat device identifiers as high-entropy secrets
- treat UI face lock as vault encryption
- treat object cues as cryptographic authentication

If a proposed change would improve convenience but weaken capture-visible quietness, local-only posture, or recovery safety, reject the change or require an explicit threat-model update.

## Review Checklist for AI-Generated Changes

Before finalizing an AI-generated change, verify:

- The touched domain matches the loaded context.
- Core invariants are preserved.
- User-facing language remains neutral.
- Field Mode remains quiet.
- Hidden routes are not treated as access control.
- Restricted actions still require the intended predicates.
- Download filenames remain neutral where required.
- Audit records do not expose sensitive semantics.
- Metadata handling does not claim complete sanitization.
- Deletion behavior is not described as guaranteed secure deletion.
- Tests cover the changed behavior.
- Documentation claims match actual implementation.
- Existing container compatibility is preserved or migration is explicitly documented.

## Scope of This File

This file is development guidance only. It does not define user-facing product claims, legal advice, operational approval, or deployment authorization.

If this file conflicts with the threat model or specification, the threat model and specification take precedence according to the Documentation Authority section.
>>>>>>> 0c73292 (Update AGENTS.md: Mark issue #26 as completed)
