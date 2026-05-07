# Phasmid Cryptographic Primitive Inventory

Canonical reference for every cryptographic primitive, parameter, and randomness
source used in Phasmid.  All parameters are centralized in
`src/phasmid/crypto_params.py`; this document is the human-readable companion.

Cross-references: `docs/THREAT_MODEL.md` (SH-01) · `docs/THREAT_ANALYSIS_STRIDE.md`

---

## Primitive Table

| Location | Primitive | Library | Parameters | Parameter Source | Risk Level | Risk Notes |
|---|---|---|---|---|---|---|
| `src/phasmid/record_cypher.py` | AES-GCM (encrypt) | `cryptography` `AESGCM` | Key: 256-bit; Nonce: 96-bit random; Tag: 128-bit; AAD: `phasmid-record-v3:<mode>:<role>:<size>` | `crypto_params.AESGCM_*` | **Low** | Random nonce per record; AEAD tag covers metadata and payload; no counter nonce. |
| `src/phasmid/local_state_crypto.py` | AES-GCM (encrypt/decrypt) | `cryptography` `AESGCM` | Key: 256-bit; Nonce: 96-bit random (prepended to blob); Tag: 128-bit; AAD: caller-supplied | `crypto_params.AESGCM_*` | **Low** | Used for all local state blobs (ORB store, role store). |
| `src/phasmid/kdf_engine.py` | Argon2id | `cryptography` `Argon2id` | `m=32768 KiB`, `t=2`, `p=1`, output=32 bytes | `crypto_params.ARGON2_*` | **Low** | Parameters tuned for RPi Zero 2 W; exceed OWASP 2023 minimums. See §Argon2id below. |
| `src/phasmid/kdf_subkeys.py` | HKDF-SHA-256 | `cryptography` `HKDF` | Hash: SHA-256; Salt: none; Output: 32 bytes; 5 domain labels | `crypto_params.AESGCM_KEY_SIZE` | **Low** | Domain-separated subkeys prevent cross-context key reuse. |
| `src/phasmid/audit.py` | HMAC-SHA-256 | built-in `hmac` + `hashlib` | Key: 32-byte derived material; chain over event records | `crypto_params.AESGCM_KEY_SIZE` | **Low** | Tamper-detectable log chain; verified via `hmac.compare_digest`. |
| `src/phasmid/crypto_boundary.py` | HMAC-SHA-256 (self-test) | built-in `hmac` + `hashlib` | Fixed test vector; comparison via `hmac.compare_digest` | — | **None** | Startup primitive availability check; not security-critical. |
| `src/phasmid/roles.py` | PBKDF2-HMAC-SHA-256 | built-in `hashlib.pbkdf2_hmac` | `iterations=100 000`; `dklen=32`; salt: 32-byte random | `crypto_params.PBKDF2_*` | **Medium** | Not in the vault derivation path; supervisor role only. PBKDF2 is weaker than Argon2id against GPU attacks. See §PBKDF2 note. |
| `src/phasmid/local_state_crypto.py` | SHA-256 (key derivation) | built-in `hashlib` | Input: state key + optional suffix; output: 32 bytes | — | **Low** | Used only when `PHASMID_STATE_SECRET` is set or a suffix is needed. Not a password hash. |
| `src/phasmid/audit.py` | SHA-256 (chain hash) | built-in `hashlib` | Input: previous record hash + current record; output: 32 bytes | — | **None** | Integrity chain only; not secret material. |

---

## Randomness Sources

All randomness is OS-backed CSPRNG.  The `random` module is not used anywhere in `src/phasmid/`.

| Location | Generator | Size | Purpose |
|---|---|---|---|
| `src/phasmid/record_cypher.py` | `os.urandom` | 16 bytes | Per-record Argon2id salt |
| `src/phasmid/record_cypher.py` | `os.urandom` | 12 bytes | AES-GCM nonce (per encrypt call) |
| `src/phasmid/record_cypher.py` | `os.urandom` | variable | Record padding to fixed-size slot |
| `src/phasmid/local_state_crypto.py` | `os.urandom` | 12 bytes | AES-GCM nonce for state blob |
| `src/phasmid/local_state_crypto.py` | `os.urandom` | 32 bytes | Local state key creation |
| `src/phasmid/kdf_engine.py` | `os.urandom` | 32 bytes | Access key creation and overwrite |
| `src/phasmid/audit.py` | `os.urandom` | 32 bytes | HMAC auth material for audit log |
| `src/phasmid/roles.py` | `os.urandom` | 32 bytes | PBKDF2 salt for supervisor passphrase |
| `src/phasmid/approval_flow.py` | `os.urandom` | 16 bytes (hex) | Single-use grant nonce |
| `src/phasmid/web_server.py` | `secrets.token_urlsafe` | 32 bytes | Web server auth token |
| `src/phasmid/web_server.py` | `secrets.token_urlsafe` | 32 bytes | Restricted session tokens |
| `src/phasmid/emergency_daemon.py` | `secrets.token_urlsafe` | 32 bytes | Panic token |
| `src/phasmid/services/doctor_service.py` | `secrets.token_bytes` | 32 bytes | Availability check (discarded) |

**Note on `os.urandom` vs `secrets`:** Both draw from the same OS CSPRNG.
`os.urandom` is used for binary key material; `secrets` is used where URL-safe
strings are required (tokens exposed in HTTP headers or cookies).  Neither is
weaker than the other for cryptographic purposes.

---

## AES-GCM Nonce Strategy

**Strategy:** Random nonce per encryption call via `os.urandom(12)`.

**Rationale:** NIST SP 800-38D §8.2.2 permits random nonces provided the
collision probability is acceptable.  With 96-bit nonces and a random source,
the probability of a collision after N encryptions under the same key is
approximately N²/2⁹⁷.  Phasmid vault slots are written infrequently (dozens
to thousands of times over the device lifetime), making collision probability
negligible.

**No counter nonce exists** in the current codebase.  There is no rollback risk
from counter reset.

**Nonce layout (LocalStateCipher):** `nonce (12 bytes) || ciphertext+tag`.

**Nonce layout (RecordCipher):** `salt (16 bytes) || nonce (12 bytes) || ciphertext+tag`
stored contiguously in the slot region of `vault.bin`.

**Serialization:** Nonce is stored as raw bytes; length is fixed by format constants.

---

## Argon2id Parameters

| Parameter | Value | Rationale |
|---|---|---|
| `memory_cost` | 32 768 KiB (32 MiB) | Exceeds OWASP 2023 minimum (19 456 KiB) by ~67 %. Tested at ~1.0 s on RPi Zero 2 W. |
| `iterations` | 2 | OWASP 2023 minimum is 2.  At minimum to keep latency acceptable on constrained hardware. |
| `lanes` | 1 | Single-core target hardware.  Parallelism provides no benefit and wastes memory bandwidth. |
| `output_length` | 32 bytes | Matches AES-256 key requirement. |
| `salt` | 16 bytes random | Per-record random salt; stored in plaintext alongside ciphertext. |
| `secret` | access key + provider secrets | Mixed in from local state + optional hardware/env/file providers. |

**Upgrade path:** To increase parameters (e.g., raise `memory_cost` to 65 536),
increment `VAULT_FORMAT_VERSION` in `crypto_params.py`, add a migration path in
`vault_core.py`, and update this table.  Old vaults at version N cannot be opened
by code expecting version N+1 without migration.

**Compatible future read:** Parameters are embedded in the record metadata JSON
(`"kdf": "argon2id"`) but the specific `memory_cost`, `iterations`, and `lanes`
values are not currently serialized per-record — they are fixed by `FORMAT_VERSION`.
Any parameter change requires a format version bump.

---

## PBKDF2-HMAC-SHA-256 Note (Medium Risk)

PBKDF2 is used only for supervisor role passphrase hashing (`src/phasmid/roles.py`).
It is **not** used for vault key derivation.

| Parameter | Value | Rationale |
|---|---|---|
| `iterations` | 100 000 | NIST SP 800-132 minimum is 1 000.  We use 100× minimum. |
| `dklen` | 32 bytes | Matches general key size. |
| `salt` | 32 bytes random | Per-hash random salt prevents precomputation attacks. |

**Risk:** PBKDF2-SHA-256 is significantly weaker than Argon2id against GPU
cracking because it has no memory-hard property.  An attacker with a GPU can
test ~1 billion PBKDF2 iterations/second, compared to ~1–10 per second for
Argon2id at the vault parameters.

**Mitigation:** The supervisor role passphrase is local-only, requires physical
device access, and is not on the vault decryption path.  The risk is accepted
for prototype scope.

**Follow-up:** If the supervisor role becomes security-critical in a future
version, replace PBKDF2 with Argon2id and increment `_SCHEMA_VERSION` in
`roles.py`.

---

## Sensitive Comparisons

All sensitive byte comparisons use `hmac.compare_digest` or the `cryptography`
library's AEAD `InvalidTag` exception path (which is timing-safe by design).

| Location | Comparison Type | Method |
|---|---|---|
| `src/phasmid/audit.py:85` | HMAC chain integrity | `hmac.compare_digest` |
| `src/phasmid/web_server.py:262` | Web token | `hmac.compare_digest` |
| `src/phasmid/emergency_daemon.py:52` | Panic token | `hmac.compare_digest` |
| `src/phasmid/crypto_boundary.py:54` | Self-test HMAC | `hmac.compare_digest` |
| `src/phasmid/roles.py` | PBKDF2 hash | `hmac.compare_digest` (replaced custom function in SH-07) |
| `src/phasmid/record_cypher.py` | Ciphertext integrity | `cryptography` `InvalidTag` (AEAD internal) |
| `src/phasmid/local_state_crypto.py` | State blob integrity | `cryptography` `InvalidTag` (AEAD internal) |

**Removed in SH-07:** The hand-rolled `_constant_time_equal` function in
`src/phasmid/roles.py` was replaced with `hmac.compare_digest`.  The custom
implementation was correct but non-standard; `hmac.compare_digest` is the
canonical Python constant-time comparison function.

---

## Non-`cryptography` Crypto Dependencies

| Module | Purpose | Notes |
|---|---|---|
| built-in `hmac` | HMAC-SHA-256 for audit chain and token comparison | Standard library; uses `hashlib` internally |
| built-in `hashlib` | SHA-256 for audit chain, PBKDF2 for roles | Standard library |
| built-in `secrets` | Web token and panic token generation | Standard library CSPRNG wrapper |
| built-in `os.urandom` | Key material, nonces, salts | OS CSPRNG; same entropy source as `secrets` |

All other crypto operations use the `cryptography` package (`cryptography.hazmat.*`).

---

## Risk Summary

| Risk Level | Count | Items |
|---|---|---|
| **High** | 0 | — |
| **Medium** | 1 | PBKDF2 in roles.py (supervisor only; not on vault path) |
| **Low** | 6 | AES-GCM (×2), Argon2id, HKDF, HMAC audit, SHA-256 state key derivation |
| **None** | 3 | HMAC self-test, SHA-256 audit chain, `secrets` availability check |

No High findings.  The single Medium finding (PBKDF2) is scoped to the supervisor
role, has documented rationale, and has a defined upgrade path.
