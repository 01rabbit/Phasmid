import os


DEFAULT_STATE_DIR = ".state"
STATE_BLOB_NAME = "store.bin"
STATE_KEY_NAME = "lock.bin"
VAULT_KEY_NAME = "access.bin"
PANIC_TOKEN_NAME = "signal.key"
PANIC_TRIGGER_NAME = "signal.trigger"
AUDIT_LOG_NAME = "events.log"
AUDIT_AUTH_NAME = "events.auth"
FACE_TEMPLATE_NAME = "face.bin"
FACE_ENROLL_FLAG_NAME = "face.enroll"


def state_dir():
    return os.environ.get("PHANTASM_STATE_DIR", DEFAULT_STATE_DIR)


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() not in {"0", "false", "off", "no", ""}


def purge_confirmation_required():
    return env_flag("PHANTASM_PURGE_CONFIRMATION", default=True)


def duress_mode_enabled():
    return env_flag("PHANTASM_DURESS_MODE", default=False)


def ui_face_lock_enabled():
    return env_flag("PHANTASM_UI_FACE_LOCK", default=False)


def ui_face_enrollment_enabled():
    return env_flag("PHANTASM_UI_FACE_ENROLL", default=False)


def field_mode_enabled():
    return env_flag("PHANTASM_FIELD_MODE", default=False)


def passphrase_min_length():
    value = os.environ.get("PHANTASM_MIN_PASSPHRASE_LENGTH", "10")
    try:
        return max(1, int(value))
    except ValueError:
        return 10
