"""Volatile key-store helper for LUKS wrapper integration."""

from __future__ import annotations

import os


class LuksKeyStore:
    """Manage ephemeral key material for LUKS helper scripts."""

    KEY_FILE_NAME = "luks.key"
    KEY_SIZE = 32

    def __init__(self, base_dir: str = "/run/phasmid"):
        self.base_dir = base_dir
        self.key_path = os.path.join(base_dir, self.KEY_FILE_NAME)

    def generate_and_store(self) -> bytes:
        os.makedirs(self.base_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(self.base_dir, 0o700)
        except OSError:
            pass
        key = os.urandom(self.KEY_SIZE)
        with open(self.key_path, "wb") as handle:
            handle.write(key)
        try:
            os.chmod(self.key_path, 0o600)
        except OSError:
            pass
        return key

    def destroy(self) -> bool:
        if not os.path.exists(self.key_path):
            return True
        try:
            length = os.path.getsize(self.key_path)
            with open(self.key_path, "r+b") as handle:
                handle.seek(0)
                handle.write(os.urandom(max(length, self.KEY_SIZE)))
            os.remove(self.key_path)
            return True
        except OSError:
            return False
