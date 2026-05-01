import hashlib
import json
import os
import time
from .config import AUDIT_LOG_NAME, state_dir


def _state_dir():
    path = state_dir()
    os.makedirs(path, mode=0o700, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path


def audit_event(event, **fields):
    if not _audit_enabled():
        return
    sanitized_fields = _sanitize_fields(fields)
    record = {
        "ts": int(time.time()),
        "event": event,
        "pid": os.getpid(),
        **sanitized_fields,
    }
    path = os.path.join(_state_dir(), AUDIT_LOG_NAME)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _sanitize_fields(fields):
    sanitized = {}
    for key, value in fields.items():
        if "profile" in key:
            sanitized["entry"] = "local_entry"
            continue
        if key == "filename":
            if value:
                sanitized["filename_present"] = True
                if os.environ.get("PHANTASM_AUDIT_FILENAMES") == "hash":
                    filename = os.path.basename(str(value))
                    sanitized["filename_hash"] = hashlib.sha256(filename.encode("utf-8")).hexdigest()
            else:
                sanitized["filename_present"] = False
            continue
        sanitized[key] = value
    return sanitized


def _audit_enabled():
    value = os.environ.get("PHANTASM_AUDIT", "0").lower()
    return value not in {"0", "false", "off", "no"}
