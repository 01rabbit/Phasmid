"""
Dual-approval flow for high-risk local operations (Issue #28).

This module provides:
- :class:`ApprovalRequest`  — an operator-initiated request for supervisor sign-off
- :class:`ApprovalGrant`    — a supervisor-verified, time-limited grant
- :class:`DualApprovalGate` — in-memory state machine managing the full lifecycle

Design constraints:
- Purely in-memory; no persistence (grants must be ephemeral and short-lived).
- Single-use grants; each grant nonce may be consumed only once.
- Stale requests and grants are purged on every access.
- This is local knowledge separation, not a cryptographic factor.
- Actions not in DUAL_APPROVAL_ACTIONS pass through unconditionally when dual
  approval is disabled.
- Supervisor passphrase is verified via :class:`~phasmid.roles.RoleStore`.

Threat properties (summary):
- Does not prevent one person knowing both credentials.
- Does not prevent collusion between operator and supervisor.
- Provides auditable evidence that two separate passphrases were entered for a
  high-risk action.
- Nonces are cryptographically random (16 bytes); replay within TTL is prevented.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from . import strings as text
from .roles import RoleStore

# Actions that require supervisor sign-off when dual approval is enabled.
DUAL_APPROVAL_ACTIONS: frozenset[str] = frozenset(
    {
        "clear_local_access_path",
        "initialize_container",
    }
)

_REQUEST_TTL = 300  # seconds; operator has 5 minutes to get supervisor approval
_GRANT_TTL = 60  # seconds; grant must be consumed within 60 seconds


@dataclass(frozen=True)
class ApprovalRequest:
    """Operator-initiated approval request."""

    action_id: str
    nonce: str  # 32-char hex; links request ↔ grant
    created_at: float
    ttl_seconds: int = _REQUEST_TTL

    def is_expired(self, now: float | None = None) -> bool:
        return (now or time.monotonic()) - self.created_at > self.ttl_seconds


@dataclass(frozen=True)
class ApprovalGrant:
    """Supervisor-verified, single-use grant."""

    action_id: str
    nonce: str  # must match the originating ApprovalRequest
    granted_at: float
    ttl_seconds: int = _GRANT_TTL

    def is_expired(self, now: float | None = None) -> bool:
        return (now or time.monotonic()) - self.granted_at > self.ttl_seconds


@dataclass(frozen=True)
class ApprovalFlowResult:
    """Neutral result of any approval-flow operation."""

    ok: bool
    reason: str  # machine-readable tag
    message: str  # neutral human-readable string
    nonce: str = ""


class DualApprovalGate:
    """
    In-memory lifecycle manager for dual-approval requests and grants.

    One pending request is allowed per action at a time.  A new
    :meth:`request` call for an action with an unexpired pending request
    returns an error rather than silently replacing it.

    Expired entries are purged lazily on each public call.
    """

    def __init__(self) -> None:
        self._pending: dict[str, ApprovalRequest] = {}  # action_id → request
        self._grants: dict[str, ApprovalGrant] = {}  # nonce → grant

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def requires_dual_approval(self, action_id: str) -> bool:
        return action_id in DUAL_APPROVAL_ACTIONS

    def request(self, action_id: str) -> ApprovalFlowResult:
        """
        Create an approval request for *action_id*.

        Returns an error if the action does not require dual approval, or if a
        pending unexpired request already exists.
        """
        self._purge_expired()
        if action_id not in DUAL_APPROVAL_ACTIONS:
            return ApprovalFlowResult(
                ok=False,
                reason="not_required",
                message=text.DUAL_APPROVAL_NOT_ENABLED,
            )
        if action_id in self._pending:
            existing = self._pending[action_id]
            if not existing.is_expired():
                return ApprovalFlowResult(
                    ok=False,
                    reason="already_pending",
                    message=text.DUAL_APPROVAL_ALREADY_PENDING,
                    nonce=existing.nonce,
                )
        nonce = os.urandom(16).hex()
        req = ApprovalRequest(
            action_id=action_id,
            nonce=nonce,
            created_at=time.monotonic(),
        )
        self._pending[action_id] = req
        return ApprovalFlowResult(
            ok=True,
            reason="request_created",
            message=text.DUAL_APPROVAL_REQUEST_CREATED,
            nonce=nonce,
        )

    def grant(
        self,
        nonce: str,
        supervisor_passphrase: str,
        role_store: RoleStore,
    ) -> ApprovalFlowResult:
        """
        Verify *supervisor_passphrase* and, if valid, create a grant for the
        request identified by *nonce*.

        The supervisor must supply this nonce out-of-band from the operator.
        """
        # Look up the request before purging so we can distinguish
        # "never existed" from "existed but expired".
        req = self._find_request_by_nonce(nonce)
        self._purge_expired()

        if req is None:
            return ApprovalFlowResult(
                ok=False,
                reason="no_request",
                message=text.DUAL_APPROVAL_REQUEST_NOT_FOUND,
            )
        if req.is_expired():
            self._pending.pop(req.action_id, None)
            return ApprovalFlowResult(
                ok=False,
                reason="request_expired",
                message=text.DUAL_APPROVAL_REQUEST_EXPIRED,
            )

        if not role_store.is_configured():
            return ApprovalFlowResult(
                ok=False,
                reason="supervisor_not_configured",
                message=text.DUAL_APPROVAL_SUPERVISOR_NOT_CONFIGURED,
            )
        result = role_store.verify_supervisor(supervisor_passphrase)
        if not result.verified:
            return ApprovalFlowResult(
                ok=False,
                reason="wrong_passphrase",
                message=text.DUAL_APPROVAL_WRONG_PASSPHRASE,
            )

        grant = ApprovalGrant(
            action_id=req.action_id,
            nonce=nonce,
            granted_at=time.monotonic(),
        )
        self._grants[nonce] = grant
        return ApprovalFlowResult(
            ok=True,
            reason="granted",
            message=text.DUAL_APPROVAL_GRANTED,
            nonce=nonce,
        )

    def consume(self, action_id: str, nonce: str) -> ApprovalFlowResult:
        """
        Consume a valid grant for *action_id*.  Single-use; removes both the
        pending request and the grant on success.
        """
        # Look up before purging to distinguish expired from never-existed.
        grant = self._grants.get(nonce)
        self._purge_expired()

        if grant is None:
            return ApprovalFlowResult(
                ok=False,
                reason="no_grant",
                message=text.DUAL_APPROVAL_REQUEST_NOT_FOUND,
            )
        if grant.action_id != action_id:
            return ApprovalFlowResult(
                ok=False,
                reason="action_mismatch",
                message=text.DUAL_APPROVAL_REQUEST_NOT_FOUND,
            )
        if grant.is_expired():
            self._grants.pop(nonce, None)
            self._pending.pop(action_id, None)
            return ApprovalFlowResult(
                ok=False,
                reason="grant_expired",
                message=text.DUAL_APPROVAL_GRANT_EXPIRED,
            )

        del self._grants[nonce]
        self._pending.pop(action_id, None)
        return ApprovalFlowResult(
            ok=True,
            reason="consumed",
            message=text.DUAL_APPROVAL_CONSUMED,
        )

    def status(self, action_id: str) -> dict[str, object]:
        """Return a neutral status dict for operator-facing display."""
        self._purge_expired()
        req = self._pending.get(action_id)
        has_request = req is not None and not req.is_expired()
        has_grant = has_request and req is not None and req.nonce in self._grants
        return {
            "action_id": action_id,
            "requires_dual_approval": self.requires_dual_approval(action_id),
            "pending_request": has_request,
            "grant_available": has_grant,
            "nonce": req.nonce if has_request and req else "",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired_actions = [
            aid for aid, req in self._pending.items() if req.is_expired(now)
        ]
        for aid in expired_actions:
            nonce = self._pending.pop(aid).nonce
            self._grants.pop(nonce, None)

        expired_grants = [n for n, g in self._grants.items() if g.is_expired(now)]
        for nonce in expired_grants:
            del self._grants[nonce]

    def _find_request_by_nonce(self, nonce: str) -> ApprovalRequest | None:
        for req in self._pending.values():
            if req.nonce == nonce:
                return req
        return None
