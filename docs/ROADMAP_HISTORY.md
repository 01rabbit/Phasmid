# Roadmap History

This document holds roadmap and milestone history that is intentionally kept out
of `AGENTS.md` so the primary AI context stays focused on active constraints and
current work.

## WebUI Redesign — Completed Sequence

The following issues were resolved in order and merged to `main` via pull
request `#44`:

| Order | Issue | Phase | Description |
|-------|-------|-------|-------------|
| 1 | **#39** | Phase 1–2 | JES Neon-Ops design system: CSS token overhaul, component updates |
| 2 | **#40** | Phase 3 | Operator Console navigation group + WebUI exposure warning banner |
| 3 | **#41** | Phase 0+4 | Backend API endpoints + Operator pages (Doctor, Audit, Guided, Inspect) |
| 4 | **#42** | Phase 5 | WebUI/TUI terminology alignment (Disclosure Face, Passphrase, JES) |
| 5 | **#43** | Phase 6–7 | Brand polish and animation update (cyan glow, phosphor green) |

## Completed Milestones

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
- `#28`: Dual-passphrase approval flow: local supervisor role store (PBKDF2+AES-GCM), in-memory request/grant lifecycle, TTL enforcement, threat analysis, and optional gate (`PHASMID_DUAL_APPROVAL`). ✅
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
- `#5`: Argon2id + HKDF-SHA-256 key schedule design — domain-separated subkey module (`kdf_subkeys.py`), deterministic test vectors, v4 design documented in `SPECIFICATION.md`. ✅
- `#11`: Process hardening — `process_hardening.py` (umask, RLIMIT_CORE, prctl, mlockall), integrated at CLI/WebUI startup, Doctor page status check. ✅
- `#12`: Volatile key-material store — `volatile_state.py`, `PHASMID_TMPFS_STATE` env var, startup validation, Doctor check, tmpfs systemd setup guide in appliance docs. ✅
- `#17`: LUKS documentation — systemd ordering example (crypttab + fstab + Requires), boot/fail-closed procedure in `RPI_ZERO_APPLIANCE_DEPLOYMENT.md`. ✅
- `#1`: Threat model structured STRIDE analysis — `docs/THREAT_ANALYSIS_STRIDE.md` covering all six STRIDE categories with controls and residual risks; `docs/THREAT_MODEL.md` updated with cross-reference. ✅
- `#13`: Device binding input evaluation — `docs/archive/DEVICE_BINDING_ANALYSIS.md` covering CPU serial, machine-id, SD CID, and deploy-time seed; current `HardwareBindingProvider` confirmed as correct approach. ✅
- `#14`: Threshold split-key recovery evaluation — `docs/archive/SPLIT_KEY_RECOVERY_ANALYSIS.md` evaluating split files, memorized values, Shamir threshold schemes, and removable media; no custom SSS implementation; recommends reviewed external tool. ✅
