from __future__ import annotations

import getpass
import os
from abc import ABC, abstractmethod


class SecretProvider(ABC):
    @abstractmethod
    def get_secret(self) -> bytes | None:
        """Retrieve secret material."""
        pass


class EnvSecretProvider(SecretProvider):
    def __init__(self, env_var: str):
        self.env_var = env_var

    def get_secret(self) -> bytes | None:
        val = os.environ.get(self.env_var)
        return val.encode("utf-8") if val else None


class FileSecretProvider(SecretProvider):
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_secret(self) -> bytes | None:
        if not os.path.exists(self.file_path):
            return None
        with open(self.file_path, "rb") as handle:
            return handle.read().strip()


class PromptSecretProvider(SecretProvider):
    def __init__(self, prompt: str = "Enter additional key material: "):
        self.prompt = prompt
        self._cache: bytes | None = None

    def get_secret(self) -> bytes | None:
        if self._cache is None:
            val = getpass.getpass(self.prompt)
            if val:
                self._cache = val.encode("utf-8")
        return self._cache
