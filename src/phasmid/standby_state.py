"""
Silent Standby state machine for coercion-safe UI transitions.

Provides a configurable hotkey-triggered transition from sensitive UI state
to a non-sensitive standby state. Recovery requires re-authentication.

State diagram:
  active → standby → sealed
  sealed → active (re-authentication required)
  sealed → dummy_disclosure (coercion-safe path)

What standby does:
  - Removes sensitive UI state from the visible surface.
  - Detaches true-profile UI references.
  - Transitions to a non-sensitive screen.

What standby does NOT do:
  - Erase key material from process memory.
  - Forge logs, fake system events, or perform anti-forensic tampering.
  - Hide the Phasmid process from the system process list.
  - Prevent live memory capture from recovering in-use key material.
"""

from __future__ import annotations

import threading
from enum import Enum


class StandbyState(str, Enum):
    ACTIVE = "active"
    STANDBY = "standby"
    SEALED = "sealed"
    DUMMY_DISCLOSURE = "dummy_disclosure"


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""


class StandbyStateMachine:
    """
    Thread-safe standby state machine.

    Transitions:
      active      → standby         (trigger_standby)
      standby     → sealed          (seal — automatic on standby activation)
      sealed      → active          (recover — requires re-authentication)
      sealed      → dummy_disclosure (enter_dummy_disclosure)
      dummy_disclosure → sealed     (seal_dummy)

    Re-entry to active from standby is disallowed without re-authentication.
    """

    _VALID_TRANSITIONS: dict[StandbyState, set[StandbyState]] = {
        StandbyState.ACTIVE: {StandbyState.STANDBY},
        StandbyState.STANDBY: {StandbyState.SEALED},
        StandbyState.SEALED: {StandbyState.ACTIVE, StandbyState.DUMMY_DISCLOSURE},
        StandbyState.DUMMY_DISCLOSURE: {StandbyState.SEALED},
    }

    def __init__(self) -> None:
        self._state = StandbyState.ACTIVE
        self._lock = threading.Lock()

    @property
    def state(self) -> StandbyState:
        with self._lock:
            return self._state

    def trigger_standby(self) -> None:
        """
        Transition from active to standby, then immediately to sealed.

        This is the hotkey-triggered path. After this call, the state is SEALED.
        """
        with self._lock:
            if self._state != StandbyState.ACTIVE:
                raise InvalidTransitionError(
                    f"Cannot trigger standby from state '{self._state}'; "
                    "must be in ACTIVE state."
                )
            self._state = StandbyState.STANDBY
            self._state = StandbyState.SEALED

    def recover(self) -> None:
        """
        Transition from sealed back to active.

        Caller is responsible for verifying re-authentication before calling this.
        Direct restoration of previous sensitive UI state is disallowed by design.
        """
        with self._lock:
            if self._state != StandbyState.SEALED:
                raise InvalidTransitionError(
                    f"Cannot recover from state '{self._state}'; "
                    "must be in SEALED state."
                )
            self._state = StandbyState.ACTIVE

    def enter_dummy_disclosure(self) -> None:
        """
        Transition from sealed to dummy_disclosure.

        Used in coercion-safe recognition fallback and manual operator choice.
        """
        with self._lock:
            if self._state != StandbyState.SEALED:
                raise InvalidTransitionError(
                    f"Cannot enter dummy disclosure from state '{self._state}'; "
                    "must be in SEALED state."
                )
            self._state = StandbyState.DUMMY_DISCLOSURE

    def seal_dummy(self) -> None:
        """Return from dummy_disclosure back to sealed."""
        with self._lock:
            if self._state != StandbyState.DUMMY_DISCLOSURE:
                raise InvalidTransitionError(
                    f"Cannot seal dummy from state '{self._state}'; "
                    "must be in DUMMY_DISCLOSURE state."
                )
            self._state = StandbyState.SEALED

    def is_active(self) -> bool:
        return self.state == StandbyState.ACTIVE

    def is_sealed(self) -> bool:
        return self.state == StandbyState.SEALED

    def is_in_standby_or_sealed(self) -> bool:
        return self.state in (StandbyState.STANDBY, StandbyState.SEALED)

    def is_dummy_disclosure(self) -> bool:
        return self.state == StandbyState.DUMMY_DISCLOSURE

    def status_dict(self) -> dict[str, object]:
        """Return a status dict safe for diagnostics. Contains no key material."""
        return {"state": self.state.value}
