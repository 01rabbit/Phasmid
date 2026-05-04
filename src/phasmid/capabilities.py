import os
from dataclasses import dataclass
from enum import Enum


class Capability(str, Enum):
    METADATA_CHECK = "metadata_check"
    METADATA_REDUCE = "metadata_reduce"
    FACE_ENROLL = "face_enroll"
    FACE_VERIFY = "face_verify"
    ENTRY_MAINTENANCE = "entry_maintenance"
    AUDIT_EXPORT = "audit_export"
    TOKEN_ROTATION = "token_rotation"
    SESSION_RESET = "session_reset"
    DIAGNOSTICS_DETAIL = "diagnostics_detail"
    RESTRICTED_ACTION = "restricted_action"
    RAPID_LOCAL_CLEAR = "rapid_local_clear"


@dataclass(frozen=True)
class DeploymentPolicy:
    name: str
    enabled: frozenset[Capability]
    quiet_maintenance: bool = False

    def allows(self, capability: Capability) -> bool:
        return capability in self.enabled


STANDARD_CAPABILITIES = frozenset(
    {
        Capability.METADATA_CHECK,
        Capability.METADATA_REDUCE,
        Capability.FACE_ENROLL,
        Capability.FACE_VERIFY,
        Capability.ENTRY_MAINTENANCE,
        Capability.AUDIT_EXPORT,
        Capability.TOKEN_ROTATION,
        Capability.SESSION_RESET,
        Capability.DIAGNOSTICS_DETAIL,
        Capability.RESTRICTED_ACTION,
        Capability.RAPID_LOCAL_CLEAR,
    }
)

FIELD_CAPABILITIES = frozenset(
    {
        Capability.METADATA_CHECK,
        Capability.METADATA_REDUCE,
        Capability.FACE_VERIFY,
        Capability.ENTRY_MAINTENANCE,
        Capability.AUDIT_EXPORT,
        Capability.DIAGNOSTICS_DETAIL,
        Capability.RESTRICTED_ACTION,
    }
)

MAINTENANCE_CAPABILITIES = frozenset(
    {
        Capability.FACE_VERIFY,
        Capability.ENTRY_MAINTENANCE,
        Capability.AUDIT_EXPORT,
        Capability.TOKEN_ROTATION,
        Capability.SESSION_RESET,
        Capability.DIAGNOSTICS_DETAIL,
    }
)

POLICIES = {
    "standard": DeploymentPolicy("standard", STANDARD_CAPABILITIES),
    "field": DeploymentPolicy("field", FIELD_CAPABILITIES, quiet_maintenance=True),
    "maintenance": DeploymentPolicy("maintenance", MAINTENANCE_CAPABILITIES),
}


def active_policy() -> DeploymentPolicy:
    selected = os.environ.get("PHASMID_PROFILE", "standard").strip().lower()
    return POLICIES.get(selected, POLICIES["standard"])


def capability_enabled(capability: Capability) -> bool:
    return active_policy().allows(capability)
