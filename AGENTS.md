# AGENTS.md

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
