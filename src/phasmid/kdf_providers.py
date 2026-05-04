from __future__ import annotations

import getpass
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass


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


class HardwareBindingProvider(SecretProvider):
    def __init__(self, path: str = "/proc/cpuinfo"):
        self.path = path

    def get_secret(self) -> bytes | None:
        """Retrieve system identifiers for hardware binding."""
        if not os.path.exists(self.path):
            return None

        # Capture hardware-specific binding material (e.g., serial or model)
        binding = []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(("Serial", "Hardware", "Revision")):
                        binding.append(line.split(":")[-1].strip())
        except OSError:
            return None

        return "-".join(binding).encode("utf-8") if binding else None


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


@dataclass(frozen=True)
class HardwareBindingStatus:
    host_supported: bool
    device_binding_available: bool
    external_binding_configured: bool

    def to_dict(self):
        return asdict(self)


def hardware_binding_status(path: str = "/proc/cpuinfo") -> HardwareBindingStatus:
    provider = HardwareBindingProvider(path=path)
    file_path = os.environ.get("PHASMID_HARDWARE_SECRET_FILE", "")
    external_binding_configured = any(
        (
            bool(os.environ.get("PHASMID_HARDWARE_SECRET")),
            bool(file_path and os.path.exists(file_path)),
            os.environ.get("PHASMID_HARDWARE_SECRET_PROMPT") == "1",
        )
    )
    device_binding = provider.get_secret()
    return HardwareBindingStatus(
        host_supported=os.path.exists(path),
        device_binding_available=bool(device_binding),
        external_binding_configured=external_binding_configured,
    )
