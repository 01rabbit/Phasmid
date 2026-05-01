import os


DEFAULT_STATE_DIR = ".state"
STATE_BLOB_NAME = "store.bin"
STATE_KEY_NAME = "lock.bin"
VAULT_KEY_NAME = "access.bin"
PANIC_TOKEN_NAME = "signal.key"
PANIC_TRIGGER_NAME = "signal.trigger"
AUDIT_LOG_NAME = "events.log"
FACE_TEMPLATE_NAME = "face.bin"


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
