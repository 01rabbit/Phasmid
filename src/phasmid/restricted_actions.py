from dataclasses import dataclass

from . import strings as text
from .capabilities import Capability


class RestrictedActionRejected(Exception):
    def __init__(self, message=text.OPERATION_REJECTED):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class RestrictedActionPolicy:
    action_id: str
    capability: Capability
    confirmation_phrase: str | None = None
    require_restricted_confirmation: bool = True
    require_password_reentry: bool = False
    require_object_cue: bool = False


# Central confirmation phrases shared by CLI and WebUI
DESTRUCTIVE_CLEAR_PHRASE = "CLEAR LOCAL ENTRY"
INITIALIZE_CONTAINER_PHRASE = "INITIALIZE LOCAL CONTAINER"
EMERGENCY_BRICK_PHRASE = "CLEAR LOCAL ACCESS PATH"
RESTRICTED_CONFIRMATION_PHRASE = "CONFIRM LOCAL CONTROL"
OVERWRITE_CONFIRMATION_PHRASE = "REPLACE LOCAL ENTRY"

RESTRICTED_ACTION_POLICIES = {
    "clear_unmatched_entry": RestrictedActionPolicy(
        action_id="clear_unmatched_entry",
        capability=Capability.RESTRICTED_ACTION,
        confirmation_phrase=DESTRUCTIVE_CLEAR_PHRASE,
    ),
    "clear_local_access_path": RestrictedActionPolicy(
        action_id="clear_local_access_path",
        capability=Capability.RESTRICTED_ACTION,
        confirmation_phrase=EMERGENCY_BRICK_PHRASE,
    ),
    "initialize_container": RestrictedActionPolicy(
        action_id="initialize_container",
        capability=Capability.RESTRICTED_ACTION,
        confirmation_phrase=INITIALIZE_CONTAINER_PHRASE,
    ),
    "rapid_local_clear": RestrictedActionPolicy(
        action_id="rapid_local_clear",
        capability=Capability.RAPID_LOCAL_CLEAR,
        confirmation_phrase="BRICK",
        require_restricted_confirmation=False,
    ),
}


def evaluate_restricted_action(
    policy: RestrictedActionPolicy,
    *,
    capability_allowed: bool,
    restricted_confirmed: bool,
    confirmation: str = "",
    password_reentered: bool = True,
    object_cue_accepted: bool = True,
):
    if not capability_allowed:
        raise RestrictedActionRejected(text.OPERATION_UNAVAILABLE)
    if policy.require_restricted_confirmation and not restricted_confirmed:
        raise RestrictedActionRejected(text.RESTRICTED_CONFIRMATION_REQUIRED)
    if (
        policy.confirmation_phrase is not None
        and confirmation != policy.confirmation_phrase
    ):
        raise RestrictedActionRejected(text.CONFIRMATION_REJECTED)
    if policy.require_password_reentry and not password_reentered:
        raise RestrictedActionRejected(text.OPERATION_REJECTED)
    if policy.require_object_cue and not object_cue_accepted:
        raise RestrictedActionRejected(text.OPERATION_REJECTED)
    return True
