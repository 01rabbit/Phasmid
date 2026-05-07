# AGENTS.md

> **Notice**: This file is the primary context entry point for AI-assisted development.
> It defines the project boundaries, security invariants, and the current roadmap.

## 0. Quick Start for AI Agents

1. **Identify the Task**: Match your task to a domain in the [Canonical Source Map](#canonical-source-map).
2. **Load Minimal Context**: Load only the files and documentation sections listed for that domain.
3. **Verify Invariants**: Check your proposed changes against the [Core Invariants](#core-invariants).
4. **Follow Language Rules**: Ensure all user-visible text follows [User-Facing Language Rules](#user-facing-language-rules).
5. **Run Tests**: Execute the relevant tests and static analysis before submitting.

---

## Purpose

This file is the first context entry point for AI-assisted development in this repository.

Phasmid is a field-evaluation prototype for local-only coercion-aware storage. It explores lawful local protection of sensitive material where device seizure, compelled access, over-disclosure, metadata risk, and local UI/log leakage are practical risks.

Phasmid is research software. It is not a replacement for full-disk encryption, hardware-backed key storage, an audited classified-data handling system, organizational records-management systems, or a complete solution to compelled disclosure.

Use this file to keep AI-assisted changes small, scoped, and consistent with the project boundary.

---

## Project Status & Roadmap

### Current Focus: JES Operator Interface — Post-Unification Stabilization

The JES Operator Interface unification work is now merged into **`main`**. The current focus is stabilizing the unified operator experience, preserving WebUI/TUI terminology parity, and continuing follow-on work without reintroducing branch-specific assumptions. Design concept: *政府機関・軍 × DEFCONハッカー* — institutional structure with terminal-hacker aesthetic.

### Active Branch

**`main`** contains:
- TUI Operator Console (Textual-based): full operator screen set (Home, Doctor, Audit, Guided, Inspect, Create, Open, Face Manager, Settings, About)
- Merged WebUI redesign phases `#39` through `#43`

Target: maintain and harden the unified JES operator surface on `main`.

### WebUI Redesign — Completed Sequence

The following issues were resolved in order and merged to `main` via pull request `#44`:

| Order | Issue | Phase | Description |
|-------|-------|-------|-------------|
| 1 | **#39** | Phase 1–2 | JES Neon-Ops design system: CSS token overhaul, component updates |
| 2 | **#40** | Phase 3 | Operator Console navigation group + WebUI exposure warning banner |
| 3 | **#41** | Phase 0+4 | Backend API endpoints + Operator pages (Doctor, Audit, Guided, Inspect) |
| 4 | **#42** | Phase 5 | WebUI/TUI terminology alignment (Disclosure Face, Passphrase, JES) |
| 5 | **#43** | Phase 6–7 | Brand polish and animation update (cyan glow, phosphor green) |

### Other Open Priority Issues

- No open priority issues are currently listed here. Add new items as post-unification work is prioritized.

### Completed Milestones

- `#8` & `#9`: CI pipeline with static analysis (`ruff`, `mypy`) and 70% coverage gate. ✅
- `#19`: Multi-source KDF provider pipeline with hardware binding. ✅
- `#31`: Audit log hash-chaining and integrity verification. ✅
- `#32`: Hardware-binding status reporting for field-evaluation units. ✅
- `#22`: Centralized restricted action policy enforcement. ✅
- `#30`: Rigorous metadata scrubbing for JPEG, PNG, and Office ZIP formats. ✅
- `#23`: Typed local state store with atomic transitions. ✅
- `#24`: Local coercion scenario matrix and restricted-flow tests. ✅
- `#25`: Centralized user-visible strings in `strings.py`. ✅
- `#26`: Vault cryptographic core split (KDFEngine / RecordCipher / ContainerLayout). ✅
- `#29`: Local operations commands (`doctor`, `verify-state`) and documentation alignment. ✅
- `#16`: Release integrity manifest and SBOM workflow (optional Ed25519 manifest signing). ✅
- `#20`: Multi-object cue and visual sequence evaluation artifacts, neutral policy-gate prototype, and recommendation baseline. ✅
- `#27`: AI gate decoupling (camera, cue matching/persistence, face-lock/session boundaries, service integration). ✅
- `#28`: Dual-passphrase approval flow: local supervisor role store (PBKDF2+AES-GCM), in-memory request/grant lifecycle, TTL enforcement, threat analysis, and optional gate (PHASMID_DUAL_APPROVAL). ✅
- `#38`: Lightweight recognition evaluation: LBP histogram face recognizer, ORB/AKAZE parametric object matcher, offline benchmark harness, and Pi Zero 2 W measurement plan. Hardware validation pending. ✅
- `#39`: JES Neon-Ops design system: CSS token overhaul and component updates. ✅
- `#40`: Operator Console navigation group and WebUI exposure warning banner. ✅
- `#41`: Backend API endpoints and Operator pages (Doctor, Audit, Guided, Inspect). ✅
- `#42`: WebUI/TUI terminology alignment (Disclosure Face, Passphrase, JES). ✅
- `#43`: Brand polish and animation update (cyan glow, phosphor green). ✅
- TUI Operator Console: full Textual-based operator console. ✅
- WebUI redesign gap fixes, including frame-lock animation, toast variants, and Store capture flow. ✅
- `#18`: Restricted-recovery observability analysis (offline path measurement harness, timing and write-channel analysis, Pi Zero 2 W measurement plan). ✅
- `#3`: Observable difference reduction — response/header neutrality tests, timing normalization documentation. ✅
- `#4`: Cryptographic erase formalization — key-material invalidation sequence spec, ordering tests, best-effort overwrite language. ✅
- `#5`: Argon2id + HKDF-SHA-256 key schedule design — domain-separated subkey module (`kdf_subkeys.py`), deterministic test vectors, v4 design documented in SPECIFICATION.md. ✅
- `#11`: Process hardening — umask 0o077, RLIMIT_CORE=0, prctl dumpable clear (Linux), mlockall (Linux); `process_hardening.py` module, Doctor page integration, CLI/WebUI startup hooks. ✅
- `#12`: Volatile key-material store — `PHASMID_TMPFS_STATE` env var, `volatile_state.py`, `config.py` state-dir routing, fail-closed startup guard, Doctor page check, systemd tmpfs mount example in `RPI_ZERO_APPLIANCE_DEPLOYMENT.md`. ✅
- `#17`: Optional LUKS encrypted storage layer — systemd crypttab + fstab + `Requires=` ordering documented in `RPI_ZERO_APPLIANCE_DEPLOYMENT.md`; fail-closed guarantee; no code changes required. ✅
- `#1`: Threat model structured STRIDE analysis — `docs/THREAT_ANALYSIS_STRIDE.md` covering all six STRIDE categories with controls and residual risks; `docs/THREAT_MODEL.md` updated with cross-reference. ✅
- `#13`: Device binding input evaluation — `docs/DEVICE_BINDING_ANALYSIS.md` covering CPU serial, machine-id, SD CID, and deploy-time seed; current `HardwareBindingProvider` confirmed as correct approach. ✅
- `#14`: Threshold split-key recovery evaluation — `docs/SPLIT_KEY_RECOVERY_ANALYSIS.md` evaluating split files, memorized values, Shamir threshold schemes, and removable media; no custom SSS implementation; recommends reviewed external tool. ✅

---

## Project Boundary

Preserve this boundary in code, documentation, tests, and UI behavior:

- local-only operation by default
- protected entries stored in `vault.bin`
- local runtime state under `.state/` or `PHASMID_STATE_DIR`
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

Do not expand Phasmid into remote management, cloud recovery, telemetry, covert communication, censorship bypass, surveillance evasion, malware storage, offensive operations, or classified-data handling infrastructure.

---

## Non-Negotiable Security Claims

Do not claim that Phasmid provides:

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

---

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

---

## Canonical Source Map

Load only the relevant files for the requested change. Do not load the whole repository by default.

### Cryptography, Container Format, and Key Path

Use this context for changes involving `vault.bin`, the Phasmid vault core, Argon2id, AES-GCM, salts, nonces, local access key material, span layout, record parsing, restricted recovery slots, destructive behavior, or migration:

- `src/phasmid/vault_core.py`
- `src/phasmid/crypto_boundary.py`
- `src/phasmid/kdf_engine.py`
- `src/phasmid/kdf_providers.py`
- `src/phasmid/container_layout.py`
- `src/phasmid/record_cypher.py`
- `docs/SPECIFICATION.md`, especially sections 11 and 15
- `docs/THREAT_MODEL.md`
- `tests/test_vault_core.py` and related tests

Relevant issues:

- `#4` cryptographic erase and local access-path invalidation
- `#5` Argon2id + HKDF-SHA-256 migration
- `#10` cryptographic module boundary and startup self-tests
- `#19` local multi-source key derivation pipeline ✅
- `#26` vault cryptographic core split ✅

### TUI Operator Console

Use this context for changes involving the Textual-based operator interface, TUI screens, widgets, theme, banner, service layer, or WebUI lifecycle management from the TUI:

- `src/phasmid/tui/app.py`
- `src/phasmid/tui/theme.py`
- `src/phasmid/tui/banner.py`
- `src/phasmid/tui/screens/` (all screen files)
- `src/phasmid/tui/widgets/` (all widget files)
- `src/phasmid/services/` (shared service layer: doctor, audit, guided, inspection, vessel, profile, webui)
- `src/phasmid/models/` (data models: vessel, profile, doctor, audit, inspection)
- `docs/TUI_OPERATOR_CONSOLE.md`
- `tests/test_tui.py`

Design concept: *政府機関・軍 × DEFCON hacker* — institutional structure with terminal-hacker aesthetic.  
Theme: `phasmid-dark` (`primary=#00d7af`, `background=#0d0d0d`, `success=#87d700`).

Key TUI-only responsibilities (do not replicate these in WebUI):
- Vessel creation, listing, and file-system operations via `VesselService`
- Profile and settings persistence via `ProfileService`
- WebUI lifecycle control (start/stop/auto-kill) via `WebUIService`
- Secure passphrase input (terminal prompt, not browser field)

Relevant issues:
- `#39` JES Neon-Ops design system for WebUI (TUI color parity) ✅
- `#41` Operator Console pages (shared service layer usage) ✅
- `#42` Terminology alignment (TUI vocabulary → WebUI) ✅

### WebUI, API Routes, and Restricted Actions

Use this context for changes involving FastAPI routes, Web mutation token, restricted confirmation, hidden routes, Field Mode, face lock sessions, store/retrieve routes, maintenance routes, emergency routes, response headers, or neutral download filenames:

- `src/phasmid/web_server.py`
- `src/phasmid/templates/`
- `src/phasmid/restricted_actions.py`
- `src/phasmid/capabilities.py`
- `src/phasmid/emergency_daemon.py`
- `src/phasmid/bridge_ui.py`
- `docs/SPECIFICATION.md`, especially sections 7, 8, and 9
- `docs/THREAT_MODEL.md`
- `tests/test_web_server.py` and related tests

Relevant issues:

- `#3` observable differences in restricted recovery flows
- `#7` authentication attempt limiting and backoff
- `#15` WebUI security headers and CSRF review
- `#21` deployment profiles and capability table
- `#22` restricted action policy enforcement ✅
- `#24` local coercion and restricted-flow scenario matrix ✅
- `#25` user-visible UI and CLI strings ✅
- `#39` JES Neon-Ops design system overhaul (Phase 1–2) ✅
- `#40` Operator Console navigation + WebUI exposure banner (Phase 3) ✅
- `#41` Operator Console pages: Doctor, Audit, Guided, Inspect (Phase 0+4) ✅
- `#42` WebUI/TUI terminology alignment (Phase 5) ✅
- `#43` Brand polish and animation update (Phase 6–7) ✅

### CLI Behavior

Use this context for changes involving `main.py`, command syntax, CLI output, confirmations, retrieve/store/init/brick/reset-face-lock behavior, or CLI terminology:

- `main.py`
- `src/phasmid/cli.py`
- `src/phasmid/passphrase_policy.py`
- `docs/SPECIFICATION.md`, especially section 6
- `docs/THREAT_MODEL.md`
- `tests/test_cli.py` and related tests

Relevant issues:

- `#4` cryptographic erase and local access-path invalidation
- `#6` access passphrase policy and strength checks
- `#7` authentication attempt limiting and backoff
- `#11` process hardening and secure memory best-effort support
- `#25` user-visible UI and CLI strings ✅
- `#29` local operations commands and docs alignment ✅

### Object Cue, Camera Matching, and Face Lock

Use this context for changes involving ORB matching, camera capture, object cue registration, match ambiguity, stable multi-frame matching, face template enrollment, or UI lock behavior:

- `src/phasmid/ai_gate.py`
- `src/phasmid/face_lock.py`
- `docs/SPECIFICATION.md`, especially section 12
- `docs/THREAT_MODEL.md`
- related tests in `tests/`

Relevant issues:

- `#20` multi-object cue and visual sequence matching
- `#27` split camera, object cue, and face UI lock responsibilities
- `#28` local dual-passphrase approval flow, if face-lock replacement is affected

### Metadata Handling

Use this context for changes involving metadata risk detection, metadata reduction, uploads, in-memory processing, file type support, original filename handling, or neutral metadata-reduced downloads:

- `src/phasmid/metadata.py`
- `src/phasmid/web_server.py` metadata routes
- `docs/SPECIFICATION.md`, especially section 10
- `docs/THREAT_MODEL.md`
- related tests in `tests/`

Relevant issues:

- `#24` scenario matrix ✅
- `#25` user-visible UI and CLI strings ✅
- `#30` metadata reduction for exported payloads

### Audit Logging

Use this context for changes involving event logs, audit record shape, hash chains, HMACs, log export, audit filenames, event names, or audit metadata:

- `src/phasmid/audit.py`
- `src/phasmid/operations.py`
- `src/phasmid/web_server.py` maintenance log export
- `docs/THREAT_MODEL.md`
- `docs/SPECIFICATION.md`
- related tests in `tests/`

Relevant issues:

- `#2` hash-chained audit log integrity checks
- `#16` release integrity manifest and SBOM workflow
- `#29` local operations commands and docs alignment ✅
- `#31` audit integrity and hash-chaining

### Local State and Deployment Posture

Use this context for changes involving `.state/`, state file names, state permissions, typed state, attempt limiting, tmpfs, LUKS, deployment profile, appliance setup, service hardening, runtime secrets, or Raspberry Pi deployment:

- `src/phasmid/config.py`
- `src/phasmid/state_store.py`
- `src/phasmid/attempt_limiter.py`
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
- `#18` restricted recovery observability on target hardware ✅
- `#21` deployment profiles and capability table
- `#23` typed local state store and transition checks ✅
- `#29` local operations commands and docs alignment ✅

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
- `#24` scenario matrix ✅

---

## Documentation Authority

When documents overlap, use this authority order:

1. `docs/THREAT_MODEL.md` controls security assumptions, residual risks, and safety boundaries.
2. `docs/SPECIFICATION.md` controls intended behavior and implementation contracts.
3. `README.md` controls public-facing project summary, installation, usage, and known limits.
4. Deployment documents control appliance setup and operational procedures.
5. Field test and seizure review documents control validation procedure and review evidence.
6. Issue descriptions describe planned work but do not override merged documentation.

Do not silently resolve contradictions. If code, tests, README, specification, threat model, and issue text conflict, state the conflict and update the affected artifacts in the same change when appropriate.

---

## User-Facing Language Rules

Use neutral terms in WebUI, CLI output, logs, response bodies, headers, filenames, documentation examples, and tests that assert visible text.

Prefer:

- protected entry / Disclosure Face (TUI-aligned term for WebUI operator pages)
- local entry
- object cue
- access cue
- passphrase (preferred over "access password" in operator-facing contexts)
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
- Janus Eidolon System / JES (brand subtitle, operator-facing)
- Vessel (TUI term for the deniable container; use in operator pages)
- Disclosure Face 1 / Disclosure Face 2 (TUI-aligned labels for entry select options)
- Live Sensor Feed (camera panel title in operator context)

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

---

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

---

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

---

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

---

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

---

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

---

## Operational Discipline

### AI Context Management

- Load only the **minimal set of files** required for the current domain.
- Do not initiate broad repository-wide rewrites.
- Check `ruff` and `mypy` before submitting any Python changes.

### Change & Test Strategy

- **Surgical Edits**: Prefer targeted edits over full-file rewrites for large files.
- **Verification**: Always run `python3 -m unittest discover -s tests` after changes.
- **No Regressions**: Ensure coverage stays above **70%**.

---

## Scope of This File

This file is development guidance only. It does not define user-facing product claims, legal advice, operational approval, or deployment authorization.

If this file conflicts with the threat model or specification, the threat model and specification take precedence according to the Documentation Authority section.
