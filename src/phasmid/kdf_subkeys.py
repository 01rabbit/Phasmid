"""
HKDF-SHA-256 domain-separated subkey derivation (v4 key schedule design).

This module provides a second derivation stage that takes Argon2id output
(or any sufficiently random input key material) and derives domain-separated
subkeys via HKDF-SHA-256.

The v3 container format embeds domain separation inline in the Argon2id
context string.  The v4 design separates concerns:

  Argon2id(passphrase + local_key + hardware_secret, salt)
      → 32-byte IKM
      → HKDF-SHA-256(IKM, info=<domain-label>)
      → 32-byte subkey per purpose

This makes each subkey purpose explicitly labelled, cryptographically
independent, and version-tagged.  Changing the label is equivalent to
rekeying for that purpose without touching any other subkey.

v3 containers remain valid indefinitely under the v3 KDFEngine path.
A v4 container uses this module for the second derivation stage.

Migration path
--------------
1. Retrieve existing entry with v3 KDFEngine.
2. Re-store with v4 KDFEngine (uses HKDF stage) and the same passphrase.
3. Verify retrieval with v4.
4. Discard v3 container.

Label conventions
-----------------
All labels are ASCII byte strings prefixed with ``phasmid-v4:``.
The format is ``phasmid-v4:<purpose>[:<version>]``.
Increment the version suffix when the purpose changes semantically.
"""

from __future__ import annotations

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

LABEL_VAULT_OPEN = b"phasmid-v4:vault:open:1"
LABEL_VAULT_PURGE = b"phasmid-v4:vault:purge:1"
LABEL_LOCAL_STATE = b"phasmid-v4:state:1"
LABEL_FACE_LOCK = b"phasmid-v4:face-lock:1"
LABEL_AUDIT_HMAC = b"phasmid-v4:audit-hmac:1"

_SUBKEY_LENGTH = 32


def derive_subkey(ikm: bytes, label: bytes, length: int = _SUBKEY_LENGTH) -> bytes:
    """
    Derive a domain-separated subkey from *ikm* using HKDF-SHA-256.

    Parameters
    ----------
    ikm:
        Input key material, typically 32 bytes of Argon2id output.
    label:
        Domain separation label from the ``LABEL_*`` constants above.
    length:
        Output byte length.  Defaults to 32 (AES-256 / HMAC-SHA-256 key size).

    Returns
    -------
    bytes
        ``length`` bytes of pseudorandom subkey material.
    """
    return HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=None,
        info=label,
    ).derive(ikm)


class SubkeyBundle:
    """
    Derive all standard subkeys from a single Argon2id output in one call.

    Each subkey is cryptographically independent: knowledge of one subkey
    does not help derive another.
    """

    __slots__ = (
        "vault_open",
        "vault_purge",
        "local_state",
        "face_lock",
        "audit_hmac",
    )

    def __init__(self, ikm: bytes) -> None:
        self.vault_open: bytes = derive_subkey(ikm, LABEL_VAULT_OPEN)
        self.vault_purge: bytes = derive_subkey(ikm, LABEL_VAULT_PURGE)
        self.local_state: bytes = derive_subkey(ikm, LABEL_LOCAL_STATE)
        self.face_lock: bytes = derive_subkey(ikm, LABEL_FACE_LOCK)
        self.audit_hmac: bytes = derive_subkey(ikm, LABEL_AUDIT_HMAC)
