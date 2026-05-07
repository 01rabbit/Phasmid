import os

DEFAULT_STATE_DIR = ".state"
STATE_BLOB_NAME = "store.bin"
STATE_KEY_NAME = "lock.bin"
VAULT_KEY_NAME = "access.bin"
PANIC_TOKEN_NAME = "signal.key"
PANIC_TRIGGER_NAME = "signal.trigger"
AUDIT_LOG_NAME = "events.log"
AUDIT_AUTH_NAME = "events.auth"
ROLE_STATE_NAME = "roles.bin"


def env_text(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value)


def env_int(name: str, default: int, minimum: int | None = None) -> int:
    raw = env_text(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        value = default
    if minimum is not None:
        return max(minimum, value)
    return value


def state_dir() -> str:
    tmpfs = tmpfs_state_dir()
    if tmpfs:
        return tmpfs
    return env_text("PHASMID_STATE_DIR", DEFAULT_STATE_DIR)


def tmpfs_state_dir() -> str | None:
    value = env_text("PHASMID_TMPFS_STATE", "").strip()
    return value or None


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() not in {"0", "false", "off", "no", ""}


def purge_confirmation_required() -> bool:
    return env_flag("PHASMID_PURGE_CONFIRMATION", default=True)


def duress_mode_enabled() -> bool:
    return env_flag("PHASMID_DURESS_MODE", default=False)


def field_mode_enabled() -> bool:
    return env_flag("PHASMID_FIELD_MODE", default=False)


def experimental_object_model_enabled() -> bool:
    return env_flag("PHASMID_EXPERIMENTAL_OBJECT_MODEL", default=False)


def object_model_path() -> str:
    return env_text("PHASMID_OBJECT_MODEL_PATH", "").strip()


def passphrase_min_length() -> int:
    return env_int("PHASMID_MIN_PASSPHRASE_LENGTH", 10, minimum=1)


def access_max_failures() -> int:
    return env_int("PHASMID_ACCESS_MAX_FAILURES", 5, minimum=1)


def access_lockout_seconds() -> int:
    return env_int("PHASMID_ACCESS_LOCKOUT_SECONDS", 60, minimum=1)


def dual_approval_enabled() -> bool:
    return env_flag("PHASMID_DUAL_APPROVAL", default=False)


def web_host() -> str:
    return env_text("PHASMID_HOST", "127.0.0.1")


def web_port() -> int:
    return env_int("PHASMID_PORT", 8000, minimum=1)


def web_token_env() -> str:
    return env_text("PHASMID_WEB_TOKEN", "").strip()


def max_upload_bytes() -> int:
    return env_int("PHASMID_MAX_UPLOAD_BYTES", 25 * 1024 * 1024, minimum=1)


def restricted_session_seconds() -> int:
    return env_int("PHASMID_RESTRICTED_SESSION_SECONDS", 120, minimum=1)


def audit_enabled() -> bool:
    return env_flag("PHASMID_AUDIT", default=False)


def audit_filename_mode() -> str:
    return env_text("PHASMID_AUDIT_FILENAMES", "").strip().lower()


def profile_name() -> str:
    return env_text("PHASMID_PROFILE", "standard").strip().lower()


def hardware_secret_file() -> str:
    return env_text("PHASMID_HARDWARE_SECRET_FILE", "").strip()


def hardware_secret_value() -> str:
    return env_text("PHASMID_HARDWARE_SECRET", "")


def hardware_secret_prompt_enabled() -> bool:
    return env_text("PHASMID_HARDWARE_SECRET_PROMPT", "") == "1"


def state_secret() -> str:
    return env_text("PHASMID_STATE_SECRET", "")


def debug_enabled() -> bool:
    return env_flag("PHASMID_DEBUG", default=False)


def doctor_recent_seconds() -> int:
    return env_int("PHASMID_DOCTOR_RECENT_SECONDS", 86400, minimum=1)


def display_enabled() -> bool:
    return env_flag("PHASMID_ENABLE_DISPLAY", default=False)


def tui_dark_enabled() -> bool:
    return env_flag("PHASMID_DARK", default=False)


def tui_light_enabled() -> bool:
    return env_flag("PHASMID_LIGHT", default=False)
