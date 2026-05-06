from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Profile:
    name: str = "default"
    container_size: str = "512M"
    default_vessel_dir: str = ""
    default_output: str = ""
    recent_tracking: bool = True
    kdf_profile: str = "interactive"
    theme: str = "dark"
    compact_banner: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "container_size": self.container_size,
            "default_vessel_dir": self.default_vessel_dir,
            "default_output": self.default_output,
            "recent_tracking": self.recent_tracking,
            "kdf_profile": self.kdf_profile,
            "theme": self.theme,
            "compact_banner": self.compact_banner,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        allowed = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in allowed})

    FORBIDDEN_KEYS = frozenset({
        "passphrase", "password", "key", "secret", "token",
        "derived_key", "raw_key", "object_key", "recovery",
    })

    def has_secrets(self) -> bool:
        d = self.to_dict()
        for k in self.FORBIDDEN_KEYS:
            if k in d:
                return True
        return False
