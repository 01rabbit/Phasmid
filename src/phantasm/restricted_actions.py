from dataclasses import dataclass

from .capabilities import Capability


class RestrictedActionRejected(Exception):
    def __init__(self, message="operation rejected"):
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
        raise RestrictedActionRejected("operation unavailable")
    if policy.require_restricted_confirmation and not restricted_confirmed:
        raise RestrictedActionRejected("restricted confirmation required")
    if policy.confirmation_phrase is not None and confirmation != policy.confirmation_phrase:
        raise RestrictedActionRejected("confirmation rejected")
    if policy.require_password_reentry and not password_reentered:
        raise RestrictedActionRejected("operation rejected")
    if policy.require_object_cue and not object_cue_accepted:
        raise RestrictedActionRejected("operation rejected")
    return True
