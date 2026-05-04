import json
import os
import struct
import time

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class RecordCipher:
    FORMAT_VERSION = 3
    AESGCM_TAG_SIZE = 16
    SALT_SIZE = 16
    NONCE_SIZE = 12
    RECORD_OVERHEAD = SALT_SIZE + NONCE_SIZE + AESGCM_TAG_SIZE
    OPEN_ROLE = "open"
    PURGE_ROLE = "purge"
    SLOT_ROLES = (OPEN_ROLE, PURGE_ROLE)

    def __init__(self, container_path, container_size):
        self.container_path = container_path
        self.container_size = container_size

    def _record_aad(self, mode, password_role):
        return f"phantasm-record-v3:{mode}:{password_role}:{self.container_size}".encode("utf-8")

    def encrypt_record(
        self,
        plaintext: bytes,
        key: bytes,
        mode: str,
        password_role: str,
        filename: str = "payload.bin",
        payload_len: int = None,
        created_at: int = None,
        salt: bytes = None,
    ) -> tuple[bytes, bytes, bytes]:
        """Encrypt a record and return (salt, nonce, ciphertext)"""
        if payload_len is None:
            payload_len = len(plaintext)
        if created_at is None:
            created_at = int(time.time())
        if salt is None:
            salt = os.urandom(self.SALT_SIZE)

        nonce = os.urandom(self.NONCE_SIZE)
        aesgcm = AESGCM(key)

        metadata = {
            "format": "ghostvault-v3",
            "version": self.FORMAT_VERSION,
            "password_role": password_role,
            "filename": os.path.basename(filename or "payload.bin"),
            "payload_len": payload_len,
            "created_at": created_at,
            "kdf": "argon2id",
        }
        metadata_bytes = json.dumps(
            metadata, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

        required_len = 4 + len(metadata_bytes) + len(plaintext)
        plaintext_capacity = self._plaintext_capacity_for_slot(mode, password_role)
        if required_len > plaintext_capacity:
            raise ValueError("encrypted payload does not fit in the container")

        padding = os.urandom(plaintext_capacity - required_len)
        record_plaintext = (
            struct.pack(">I", len(metadata_bytes)) + metadata_bytes + plaintext + padding
        )
        aad = self._record_aad(mode, password_role)
        ciphertext = aesgcm.encrypt(nonce, record_plaintext, aad)

        return salt, nonce, ciphertext

    def decrypt_record(
        self,
        ciphertext: bytes,
        key: bytes,
        salt: bytes,
        nonce: bytes,
        mode: str,
        password_role: str,
    ) -> tuple[bytes, str, dict]:
        """Decrypt a record and return (data, filename, metadata) or raise exception"""
        aesgcm = AESGCM(key)
        aad = self._record_aad(mode, password_role)
        decrypted = aesgcm.decrypt(nonce, ciphertext, aad)

        if len(decrypted) < 4:
            raise ValueError("decrypted record too short")

        meta_len = struct.unpack(">I", decrypted[:4])[0]
        if meta_len > len(decrypted) - 4:
            raise ValueError("invalid metadata length")

        metadata = json.loads(decrypted[4 : 4 + meta_len].decode("utf-8"))
        if (
            metadata.get("format") != "ghostvault-v3"
            or metadata.get("version") != self.FORMAT_VERSION
        ):
            raise ValueError("invalid record format or version")

        if metadata.get("password_role") != password_role:
            raise ValueError("password role mismatch")

        payload_len = metadata.get("payload_len")
        if not isinstance(payload_len, int) or payload_len < 0:
            raise ValueError("invalid payload length")

        payload_start = 4 + meta_len
        payload_end = payload_start + payload_len
        if payload_end > len(decrypted):
            raise ValueError("payload length exceeds decrypted data")

        actual_data = decrypted[payload_start:payload_end]
        filename = os.path.basename(metadata.get("filename") or "payload.bin")

        return actual_data, filename, metadata

    def randomize_slot(self, mode: str, password_role: str):
        """Randomize a slot by overwriting with random data"""
        start, length = self._slot_span(mode, password_role)
        with open(self.container_path, "r+b") as f:
            f.seek(start)
            f.write(os.urandom(length))

    def _plaintext_capacity_for_slot(self, mode: str, password_role: str) -> int:
        """Calculate plaintext capacity for a specific slot"""
        _start, span_len = self._slot_span(mode, password_role)
        capacity = span_len - self.RECORD_OVERHEAD
        if capacity <= 4:
            raise ValueError("container is too small for encrypted record")
        return capacity

    def _mode_span(self, mode: str) -> tuple[int, int]:
        """Get the span for a mode"""
        if mode == "secret":
            return self.container_size // 2, self.container_size - (self.container_size // 2)
        if mode == "dummy":
            return 0, self.container_size // 2
        raise ValueError(f"unsupported mode: {mode}")

    def _slot_span(self, mode: str, password_role: str) -> tuple[int, int]:
        """Get the span for a slot within a mode"""
        if password_role not in self.SLOT_ROLES:
            raise ValueError(f"unsupported password role: {password_role}")
        start, span_len = self._mode_span(mode)
        first_slot_len = span_len // 2
        if password_role == self.OPEN_ROLE:
            return start, first_slot_len
        return start + first_slot_len, span_len - first_slot_len