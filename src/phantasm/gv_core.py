import json
import os
import struct
import time

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import VAULT_KEY_NAME
from .config import state_dir as default_state_dir
from .kdf_engine import KDFEngine


class GhostVault:
    FORMAT_VERSION = 3
    MIN_CONTAINER_SIZE = 4096
    AESGCM_TAG_SIZE = 16
    SALT_SIZE = 16
    NONCE_SIZE = 12
    RECORD_OVERHEAD = SALT_SIZE + NONCE_SIZE + AESGCM_TAG_SIZE
    ARGON2_ITERATIONS = 2
    ARGON2_LANES = 1
    ARGON2_MEMORY_COST = 32768
    ACCESS_KEY_SIZE = 32
    OPEN_ROLE = "open"
    PURGE_ROLE = "purge"
    SLOT_ROLES = (OPEN_ROLE, PURGE_ROLE)

    def __init__(self, container_path, size_mb=10, state_dir=None):
        self.path = container_path
        self.size = self._normalize_size(size_mb)
        self.state_dir = state_dir or default_state_dir()
        self.access_key_path = os.path.join(self.state_dir, VAULT_KEY_NAME)
        self.kdf_engine = KDFEngine(self.state_dir)

    def _normalize_size(self, size_mb):
        try:
            size_bytes = int(float(size_mb) * 1024 * 1024)
        except (TypeError, ValueError) as exc:
            raise ValueError("size_mb must be a positive number") from exc

        if size_bytes < self.MIN_CONTAINER_SIZE:
            raise ValueError(
                f"container size must be at least {self.MIN_CONTAINER_SIZE} bytes"
            )
        return size_bytes

    def _derive_key(
        self,
        password: str,
        gesture_sequence: list,
        mode,
        salt,
        create_access_key=False,
        password_role=OPEN_ROLE,
    ):
        return self.kdf_engine.derive_key(
            password=password,
            gesture_sequence=gesture_sequence,
            mode=mode,
            salt=salt,
            password_role=password_role,
            create_access_key=create_access_key,
        )

    def _load_or_create_access_key(self, create=False):
        return self.kdf_engine._load_or_create_access_key(create=create)

    def rotate_access_key(self):
        self.kdf_engine.rotate_access_key()

    def _require_container(self):
        if not os.path.exists(self.path):
            raise FileNotFoundError(
                f"container file not found: {self.path}. Run format_container() first."
            )

    def _mode_span(self, mode):
        if mode == "secret":
            return self.size // 2, self.size - (self.size // 2)
        if mode == "dummy":
            return 0, self.size // 2
        raise ValueError(f"unsupported mode: {mode}")

    def _slot_span(self, mode, password_role):
        if password_role not in self.SLOT_ROLES:
            raise ValueError(f"unsupported password role: {password_role}")
        start, span_len = self._mode_span(mode)
        first_slot_len = span_len // 2
        if password_role == self.OPEN_ROLE:
            return start, first_slot_len
        return start + first_slot_len, span_len - first_slot_len

    def _plaintext_capacity(self, span_len):
        capacity = span_len - self.RECORD_OVERHEAD
        if capacity <= 4:
            raise ValueError("container is too small for encrypted record")
        return capacity

    def format_container(self, rotate_access_key=False):
        if rotate_access_key:
            self.rotate_access_key()
        else:
            self._load_or_create_access_key(create=True)
        with open(self.path, "wb") as f:
            f.write(os.urandom(self.size))
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def store(
        self,
        password,
        data,
        gesture_sequence,
        filename="payload.bin",
        mode="dummy",
        restricted_recovery_password=None,
    ):
        self._require_container()
        if (
            restricted_recovery_password is not None
            and restricted_recovery_password == password
        ):
            raise ValueError("open and restricted recovery passwords must be different")

        self._write_slot(
            password,
            data,
            gesture_sequence,
            filename=filename,
            mode=mode,
            password_role=self.OPEN_ROLE,
        )

        if restricted_recovery_password:
            self._write_slot(
                restricted_recovery_password,
                data,
                gesture_sequence,
                filename=filename,
                mode=mode,
                password_role=self.PURGE_ROLE,
            )
        else:
            self._randomize_slot(mode, self.PURGE_ROLE)

    def _write_slot(
        self, password, data, gesture_sequence, filename, mode, password_role
    ):
        start, span_len = self._slot_span(mode, password_role)

        plaintext_capacity = self._plaintext_capacity(span_len)
        salt = os.urandom(self.SALT_SIZE)
        nonce = os.urandom(self.NONCE_SIZE)
        key = self._derive_key(
            password,
            gesture_sequence,
            mode,
            salt,
            create_access_key=True,
            password_role=password_role,
        )
        aesgcm = AESGCM(key)

        metadata = {
            "format": "ghostvault-v3",
            "version": self.FORMAT_VERSION,
            "password_role": password_role,
            "filename": os.path.basename(filename or "payload.bin"),
            "payload_len": len(data),
            "created_at": int(time.time()),
            "kdf": "argon2id",
        }
        metadata_bytes = json.dumps(
            metadata, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        required_len = 4 + len(metadata_bytes) + len(data)

        if required_len > plaintext_capacity:
            raise ValueError("encrypted payload does not fit in the container")
        padding = os.urandom(plaintext_capacity - required_len)
        plaintext = (
            struct.pack(">I", len(metadata_bytes)) + metadata_bytes + data + padding
        )
        aad = self._record_aad(mode, password_role)
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
        payload = salt + nonce + ciphertext

        with open(self.path, "r+b") as f:
            f.seek(start)
            f.write(payload)

    def retrieve(self, password, gesture_sequence, mode="dummy"):
        data, filename, _password_role = self.retrieve_with_policy(
            password, gesture_sequence, mode=mode
        )
        return data, filename

    def retrieve_with_policy(self, password, gesture_sequence, mode="dummy"):
        self._require_container()
        for password_role in self.SLOT_ROLES:
            data, filename = self._retrieve_slot(
                password, gesture_sequence, mode, password_role
            )
            if data is not None:
                return data, filename, password_role
        return None, None, None

    def _retrieve_slot(self, password, gesture_sequence, mode, password_role):
        start, span_len = self._slot_span(mode, password_role)
        ciphertext_len = span_len - self.SALT_SIZE - self.NONCE_SIZE

        with open(self.path, "rb") as f:
            f.seek(start)
            salt = f.read(self.SALT_SIZE)
            nonce = f.read(self.NONCE_SIZE)
            ciphertext = f.read(ciphertext_len)
            if len(salt) != self.SALT_SIZE or len(nonce) != self.NONCE_SIZE:
                return None, None
            if len(ciphertext) != ciphertext_len:
                return None, None

        try:
            key = self._derive_key(
                password,
                gesture_sequence,
                mode,
                salt,
                create_access_key=False,
                password_role=password_role,
            )
            aesgcm = AESGCM(key)
            decrypted = aesgcm.decrypt(
                nonce, ciphertext, self._record_aad(mode, password_role)
            )
            if len(decrypted) < 4:
                return None, None

            meta_len = struct.unpack(">I", decrypted[:4])[0]
            if meta_len > len(decrypted) - 4:
                return None, None
            metadata = json.loads(decrypted[4 : 4 + meta_len].decode("utf-8"))
            if (
                metadata.get("format") != "ghostvault-v3"
                or metadata.get("version") != self.FORMAT_VERSION
            ):
                return None, None
            if metadata.get("password_role") != password_role:
                return None, None
            payload_len = metadata.get("payload_len")
            if not isinstance(payload_len, int) or payload_len < 0:
                return None, None
            payload_start = 4 + meta_len
            payload_end = payload_start + payload_len
            if payload_end > len(decrypted):
                return None, None
            actual_data = decrypted[payload_start:payload_end]

            filename = os.path.basename(metadata.get("filename") or "payload.bin")
            return actual_data, filename
        except (
            InvalidTag,
            ValueError,
            OSError,
            json.JSONDecodeError,
            UnicodeDecodeError,
            KeyError,
        ):
            return None, None

    def _record_aad(self, mode, password_role):
        return f"phantasm-record-v3:{mode}:{password_role}:{self.size}".encode("utf-8")

    def _randomize_slot(self, mode, password_role):
        self._require_container()
        start, length = self._slot_span(mode, password_role)
        with open(self.path, "r+b") as f:
            f.seek(start)
            f.write(os.urandom(length))

    def silent_brick(self):
        self.destroy_access_keys()
        self._require_container()
        with open(self.path, "r+b") as f:
            f.seek(0)
            f.write(os.urandom(self.size))

    def destroy_access_keys(self):
        self.kdf_engine.destroy_access_keys()

    def purge_mode(self, mode):
        self._require_container()
        start, length = self._mode_span(mode)
        with open(self.path, "r+b") as f:
            f.seek(start)
            f.write(os.urandom(length))

    def purge_other_mode(self, accessed_mode):
        if accessed_mode == "dummy":
            self.purge_mode("secret")
            return
        if accessed_mode == "secret":
            self.purge_mode("dummy")
            return
        raise ValueError(f"unsupported mode: {accessed_mode}")
