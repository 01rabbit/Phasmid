from dataclasses import dataclass

from .capabilities import Capability
from . import strings as text


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
