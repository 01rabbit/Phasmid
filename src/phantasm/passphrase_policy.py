"""Local passphrase checks for Store flows."""

from __future__ import annotations

from dataclasses import dataclass

from .config import passphrase_min_length


@dataclass(frozen=True)
class PassphraseCheck:
    ok: bool
    message: str = ""


def check_passphrase(value: str, label: str = "Access password"):
    if not value:
        return PassphraseCheck(False, f"{label} must not be empty.")
    minimum = passphrase_min_length()
    if len(value) < minimum:
        return PassphraseCheck(
            False,
            f"{label} must be at least {minimum} characters.",
        )
    if len(set(value)) <= 2:
        return PassphraseCheck(False, f"{label} is too repetitive.")
    return PassphraseCheck(True)


def check_store_passphrases(access_value: str, restricted_value: str = ""):
    access_check = check_passphrase(access_value, "Access password")
    if not access_check.ok:
        return access_check
    if restricted_value:
        if access_value == restricted_value:
            return PassphraseCheck(
                False,
                "Access and restricted recovery passwords must be different.",
            )
        restricted_check = check_passphrase(
            restricted_value,
            "Restricted recovery password",
        )
        if not restricted_check.ok:
            return restricted_check
    return PassphraseCheck(True)
