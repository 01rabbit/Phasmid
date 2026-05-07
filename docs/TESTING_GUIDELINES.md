# Phasmid Testing Guidelines

## Purpose

This document defines naming conventions and structural rules for Phasmid tests.
Tests are written to verify specific *claims* about system behavior and *invariants*
that must hold across all inputs.  Naming tests after claims makes it visible which
claims are covered and which are not.

Cross-references: `docs/THREAT_MODEL.md` · `docs/CRYPTO_INVENTORY.md`

---

## Test Naming Convention

### Rule 1 — Claim-backed tests: `test_claim_<CLM-ID>_<description>`

Use this prefix when the test verifies a specific behavioral claim.  Claim IDs
will be defined in `docs/CLAIMS.md` (SH-02).  Until that document exists, use
the placeholder scheme below.

```
test_claim_<CLM-ID>_<what_is_asserted>
```

Examples:
```python
def test_claim_CLM01_brick_overwrites_container_with_random_bytes(): ...
def test_claim_CLM02_brick_preserves_container_file_size(): ...
def test_claim_CLM03_brick_destroys_access_key(): ...
def test_claim_CLM04_brick_is_idempotent(): ...
def test_claim_CLM05_vault_bin_has_no_plaintext_magic_header(): ...
def test_claim_CLM06_field_mode_hides_state_path_before_confirmation(): ...
```

### Rule 2 — Invariant tests: `test_invariant_<description>`

Use this prefix when the test verifies a property that must hold for all valid
inputs (often implemented with property-based testing via `hypothesis`).

```
test_invariant_<what_holds>
```

Examples:
```python
def test_invariant_encrypt_decrypt_roundtrip(): ...
def test_invariant_failure_counter_monotonically_increases(): ...
def test_invariant_container_size_unchanged_after_operations(): ...
```

### Rule 3 — Scenario tests: `test_scenario_<scenario-id>_<phase>`

Use this prefix for multi-step behavioral scenarios that verify a sequence of
operations.

```
test_scenario_<kebab-id>_<phase>
```

Examples:
```python
def test_scenario_brick_irreversibility_store_phase(): ...
def test_scenario_brick_irreversibility_post_brick_open_fails(): ...
```

### Rule 4 — Legacy unit tests

Existing tests that do not yet follow the above conventions are documented in
the mapping table below and need not be renamed if the refactor cost outweighs
the benefit.  New tests must follow Rules 1–3.

---

## Claim ID Placeholder Scheme

Until `docs/CLAIMS.md` is created (SH-02), claim IDs are assigned sequentially
within each module using a `CLM-<NN>` prefix.  The table below maps current
claim-backed tests to their claim ID.

| Claim ID | Claim Statement | Test Location |
|---|---|---|
| CLM-01 | Bricking overwrites `vault.bin` with random data | `tests/scenarios/test_brick_irreversibility.py` |
| CLM-02 | Bricking preserves the container file size | `tests/scenarios/test_brick_irreversibility.py` |
| CLM-03 | Bricking destroys the local access key | `tests/scenarios/test_brick_irreversibility.py` |
| CLM-04 | Bricking is idempotent (double-brick safe) | `tests/scenarios/test_brick_irreversibility.py` |
| CLM-05 | `vault.bin` has no plaintext magic header or format marker | `tests/scenarios/test_headerless_invariant.py` |
| CLM-06 | Field Mode hides state path before restricted confirmation | `tests/scenarios/test_field_mode_visibility.py` |
| CLM-07 | Field Mode hides session token before restricted confirmation | `tests/scenarios/test_field_mode_visibility.py` |
| CLM-08 | Forbidden internal terms are absent from Field Mode HTML output | `tests/scenarios/test_field_mode_visibility.py` |
| CLM-09 | AES-GCM nonces are unique across 10 000 encryptions | `tests/crypto/test_nonce_uniqueness.py` |
| CLM-10 | No `random` module is imported in `src/phasmid/` | `tests/crypto/test_no_weak_randomness.py` |
| CLM-11 | Sensitive comparisons use `hmac.compare_digest` | `tests/crypto/test_constant_time.py` |
| CLM-12 | Argon2id parameters match OWASP 2023 minimums | `tests/crypto/test_kdf_versioning.py` |

---

## Directory Layout

```
tests/
├── crypto/              # Cryptographic primitive tests (SH-05..08)
│   ├── test_nonce_uniqueness.py
│   ├── test_kdf_versioning.py
│   ├── test_constant_time.py
│   └── test_no_weak_randomness.py
├── properties/          # Property-based / invariant tests (SH-12)
│   └── test_vault_invariants.py
├── scenarios/           # Multi-step behavioral scenario tests (SH-10, SH-11, SH-13)
│   ├── forbidden_terms.py       # Shared forbidden-term list (SH-11)
│   ├── known_magics.py          # Known binary magic signatures (SH-13)
│   ├── restricted_flows.json    # Scenario definitions
│   ├── test_brick_irreversibility.py
│   ├── test_field_mode_visibility.py
│   └── test_headerless_invariant.py
└── test_*.py            # Legacy unit tests
```

---

## CI Lint (Naming Convention Check)

The script `scripts/check_test_naming.py` enforces this convention in warning
mode.  Run it with:

```bash
python3 scripts/check_test_naming.py
```

It reports test methods that do not follow Rules 1–3 but does **not** fail the
build (warning mode).  Counts are reported to allow trend tracking.

---

## Legacy Test Mapping

The following existing tests cover claims and may be renamed in future:

| Existing Test | Claim | Status |
|---|---|---|
| `test_nonce_uniqueness.py::TestNonceUniqueness::test_no_nonce_collisions` | CLM-09 | Follows convention in module name |
| `test_constant_time.py::*::test_custom_constant_time_equal_removed` | CLM-11 | Follows convention in module name |
| `test_kdf_versioning.py::TestParamCentralization::test_argon2_memory_cost_meets_owasp_minimum` | CLM-12 | Follows convention in module name |
| `test_record_cypher.py::*` | CLM-05 (partial) | Legacy naming; covered by SH-13 |
| `test_vault_core.py::*` | CLM-01..04 (partial) | Legacy naming; covered by SH-10 |

---

## Definition of a Covered Claim

A claim is considered **covered** when:
1. At least one test with prefix `test_claim_<CLM-ID>_` or `test_invariant_` exists.
2. The test fails when the claim is violated.
3. The test passes on the current codebase.

A claim is **partially covered** when related tests exist but without the
`test_claim_` or `test_invariant_` prefix.

A claim is **uncovered** when no test verifies the stated behavior.  Uncovered
claims must be recorded in `docs/CLAIMS.md` as `untested`.
