# Cryptographic Core Module Design (Issue #26)

## Objective

Split `src/phasmid/gv_core.py` into reviewable, separately testable cryptographic modules while maintaining:

- GhostVault v3 container format compatibility
- No changes to encryption/decryption behavior
- Identical test coverage and behavior
- Gradual, traceable refactoring path

## Current State

`gv_core.py` contains 24 methods in a single `GhostVault` class:

- 7 key derivation and key management methods
- 7 record encryption/decryption methods
- 5 container management methods
- 5 utility methods

## Proposed Module Structure

### Phase 1: Extract KDF and Key Management

**Module:** `src/phasmid/kdf_engine.py`

Responsibilities:
- Argon2id KDF invocation and parameter management
- Local access key lifecycle
- Multi-source KDF input composition (password, object cue, hardware secrets)

**Methods to move:**
- `_context_password()`
- `_derive_key()`
- `_kdf_secret()`
- `_load_or_create_access_key()`
- `_write_new_access_key()`
- `rotate_access_key()`
- `destroy_access_keys()`

**API:**
```python
class KDFEngine:
    def derive_key(password: str, gesture_sequence: list, mode: str, salt: bytes, ...) -> bytes
    def get_or_create_access_key() -> bytes
    def destroy_access_keys() -> None
```

### Phase 2: Extract Record Encryption/Decryption

**Module:** `src/phasmid/encryption.py`

Responsibilities:
- AES-GCM encryption and decryption
- Salt and nonce generation
- AEAD associated data construction
- Slot randomization

**Methods to move:**
- `_write_slot()`
- `_retrieve_slot()`
- `_record_aad()`
- `_randomize_slot()`

**API:**
```python
class RecordCrypher:
    def encrypt_record(plaintext: bytes, key: bytes, mode: str, ...) -> (ciphertext, salt, nonce)
    def decrypt_record(ciphertext: bytes, key: bytes, salt: bytes, nonce: bytes, ...) -> plaintext
    def randomize_slot(key: bytes, ...) -> None
```

### Phase 3: Container Lifecycle

**Module:** `src/phasmid/container.py`

Responsibilities:
- Container initialization and format
- Span layout and slot addressing
- Container brick and purge operations

**Methods to move:**
- `format_container()`
- `_mode_span()`
- `_slot_span()`
- `_plaintext_capacity()`
- `_require_container()`
- `silent_brick()`
- `purge_mode()`
- `purge_other_mode()`

**API:**
```python
class ContainerLayout:
    def get_mode_span(mode: str) -> (offset, length)
    def get_slot_span(mode: str, password_role: str) -> (offset, length)
    def format_container(container_path: str, size_bytes: int) -> None
```

## Integration Points

The refactored `GhostVault` class will remain the primary orchestrator:

```python
class GhostVault:
    def __init__(self, container_path: str, size_mb: int = 10, state_dir: str = None):
        self.cipher = RecordCypher()
        self.kdf = KDFEngine(state_dir)
        self.layout = ContainerLayout(container_path, size_bytes)
    
    def store(self, password: str, gesture_sequence: list, plaintext: bytes, ...):
        # Orchestrate: KDF -> Cipher -> Layout
    
    def retrieve(self, password: str, gesture_sequence: list, ...):
        # Orchestrate: KDF -> Cipher -> Layout
```

## Test Strategy

1. Create unit tests for each new module **before** extraction
2. Test module APIs against hardcoded test vectors
3. Verify module tests pass with extracted code
4. Run full integration tests with refactored GhostVault
5. Confirm no regression in existing container compatibility

## Compatibility Guarantees

- GhostVault v3 format unchanged
- All existing test vectors pass
- No public API changes (GhostVault class interface remains)
- Deterministic behavior on identical inputs

## Implementation Schedule

1. Create test vectors and module tests
2. Extract KDF engine
3. Extract encryption module
4. Extract container layout
5. Refactor GhostVault orchestrator
6. Full regression testing
7. Update AGENTS.md with completion status

## Risk Mitigation

- Baseline coverage must remain at 69% or higher
- Each extraction must pass new module-specific tests
- Integration tests run after each phase
- v3 container compatibility verified at each step
