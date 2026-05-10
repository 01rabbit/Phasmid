# Dual-Passphrase Approval Flow — Analysis and Design (Issue #28)

## Decision

**Minimal implementation adopted — optional and off by default.**

The repository now includes:

- `src/phasmid/roles.py`: encrypted local supervisor passphrase store
- `src/phasmid/approval_flow.py`: in-memory request/grant lifecycle with TTL enforcement
- 46 unit tests covering the full acceptance-criteria matrix

The feature is disabled unless `PHASMID_DUAL_APPROVAL=1` is set in the environment.

---

## What This Is

A local two-person control mechanism for a defined subset of high-risk actions.
An **operator** initiates an action; a **supervisor** must enter a separate locally
stored passphrase to authorize it within a time window.

**This is local knowledge separation, not an external-token factor.**

It does not:

- prevent a single person from knowing all credentials
- prevent collusion between operator and supervisor
- act as a cryptographic factor for vault derivation or AEAD parameters
- replace hardware security modules or out-of-band approval tokens
- provide any protection if the host OS is compromised

---

## Roles

| Role | Description | Passphrase stored? |
|---|---|---|
| **Operator** | Normal system user; initiates actions | No (implicit) |
| **Supervisor** | Second local principal; authorizes high-risk actions | Yes (PBKDF2-HMAC-SHA-256, encrypted) |

Supervisor passphrase storage:

- 32-byte random salt generated fresh on each enrollment
- PBKDF2-HMAC-SHA-256, 100 000 iterations, 32-byte output
- Hash stored as AES-GCM encrypted JSON (`roles.bin`) in the state directory
- Distinct `LocalStateCipher` key suffix (`:roles`) separates it from other state blobs

The operator role has no separate stored credential.  Requiring the operator to
already hold a valid session or vault passphrase is sufficient.

---

## Actions Requiring Dual Approval

| `action_id` | Description | Rationale |
|---|---|---|
| `clear_local_access_path` | Emergency brick / key-path invalidation | Most destructive; irreversible |
| `initialize_container` | Reinitialize the vault container | Destroys all stored entries |

All other actions in `RESTRICTED_ACTION_POLICIES` continue to use the existing
single-operator restricted confirmation flow unchanged.

---

## Approval Flow

```text
Operator                          Supervisor
   │                                  │
   ├─ request(action_id)              │
   │   → ApprovalRequest{nonce}       │
   │   TTL: 300 s                     │
   │                                  │
   │  [out-of-band: operator shares nonce with supervisor]
   │                                  │
   │                   grant(nonce, passphrase, role_store)
   │                   verify passphrase → ApprovalGrant{nonce}
   │                   TTL: 60 s      │
   │                                  │
   ├─ consume(action_id, nonce)       │
   │   grant valid? → action proceeds │
   │   grant removed (single-use)     │
```

### TTL Rationale

| Timer | Value | Rationale |
|---|---|---|
| Request TTL | 300 s | 5 minutes for supervisor to arrive and respond |
| Grant TTL | 60 s | Short window; operator must act immediately after receiving authorization |

Short grant TTL limits the window for grant theft or session fixation.

---

## Threat Analysis

### Threats Addressed

| Threat | Mitigation |
|---|---|
| Single operator unilaterally bricks device | Supervisor passphrase required |
| Opportunistic container reinitialization | Supervisor passphrase required |
| Stale grant reuse | Grants expire after 60 s and are single-use (nonce consumed on use) |
| Grant replay for a different action | `action_id` embedded in grant; checked on consume |
| Long-lived pending requests | Requests expire after 300 s; lazy purge on each call |
| Nonce prediction | 16 bytes from `os.urandom`; 128 bits of entropy |
| Passphrase enumeration | PBKDF2-HMAC-SHA-256, 100k iterations per attempt; no rate-limit bypass |

### Threats Not Addressed

| Threat | Notes |
|---|---|
| **Collusion** | Both credentials may be known to one person; no technical control |
| **Compromised host** | A compromised OS can observe in-memory passphrase entry |
| **Physical coercion** | Both principals can be compelled; this is not coercion resistance |
| **Audit log tampering** | Audit log integrity is handled separately (hash-chaining, #31) |
| **Network-remote grant** | There is no remote approval path; this is local-only |

---

## User-Error Analysis

| Scenario | Behaviour |
|---|---|
| Operator requests approval; supervisor enters wrong passphrase | `wrong_passphrase`; request stays pending; supervisor may retry |
| Operator requests approval; supervisor unavailable within 300 s | Request expires; operator must re-request |
| Supervisor grants; operator does not act within 60 s | Grant expires; operator must re-request |
| Operator calls `consume()` twice with the same nonce | Second call fails with `no_grant` (nonce already removed) |
| Supervisor not configured; operator requests dual approval | Gate reports `supervisor_not_configured`; action is blocked until configured |
| `PHASMID_DUAL_APPROVAL` is not set | Feature is inactive; high-risk actions use existing restricted confirmation flow |

---

## Acceptance Criteria Review

| Criterion | Status |
|---|---|
| Documentation says "local knowledge separation, not external-token factor" | ✅ This document and module docstrings |
| Tests cover stale approval | ✅ `test_request_after_expiry_creates_new_request`, `test_stale_requests_are_purged_on_next_call` |
| Tests cover wrong role | ✅ `test_grant_with_wrong_passphrase_is_rejected`, `test_grant_when_supervisor_not_configured` |
| Tests cover repeated use | ✅ `test_consume_is_single_use`, `test_second_request_while_pending_returns_error` |
| Tests cover direct route bypass | ✅ `test_consume_without_request_and_grant_always_fails`, `test_grant_nonce_cannot_be_reused_across_actions` |
| User-facing wording neutral | ✅ All strings in `strings.py`; no coercion-model references |
| Feature remains optional | ✅ Disabled unless `PHASMID_DUAL_APPROVAL=1` |

---

## Rejected Alternatives

### External Token (TOTP, hardware key)

Requires a third-party service or hardware dependency.  Out of scope for
Phasmid's local-only design boundary.

### Audit-Only (no block)

Logging a warning without blocking high-risk actions provides no separation
guarantee.  Rejected in favour of a hard block when the feature is enabled.

### Persistent Grant Store

Persisting grants to disk extends the window of grant theft.  The in-memory
design ensures grants disappear on process restart; this is the preferred
posture for an appliance device.

### Three-Role Hierarchy (Operator / Supervisor / Auditor)

Adds complexity without a concrete field requirement.  Auditor and Maintainer
roles may be revisited if multi-site deployments emerge.
