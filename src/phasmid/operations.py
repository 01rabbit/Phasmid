"""Local operations checks for repeatable field procedures."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

from .audit import verify_log_integrity
from .config import (
    AUDIT_AUTH_NAME,
    AUDIT_LOG_NAME,
    STATE_BLOB_NAME,
    STATE_KEY_NAME,
    VAULT_KEY_NAME,
    state_dir,
)
from .kdf_providers import hardware_binding_status
from .state_store import LocalStateStore

STATUS_READY = "ready"
STATUS_ATTENTION = "attention"
STATUS_NOT_ENABLED = "not_enabled"

EXPECTED_STATE_FILES = (
    STATE_BLOB_NAME,
    STATE_KEY_NAME,
    VAULT_KEY_NAME,
)

REDACTED_AUDIT_FIELDS = {
    "ts",
    "event",
    "pid",
    "source",
    "entry",
    "bytes",
    "success",
    "label_present",
    "filename_present",
}


@dataclass(frozen=True)
class OperationCheck:
    name: str
    status: str
    message: str

    def to_dict(self):
        return asdict(self)


def _report(name: str, checks: list[OperationCheck]):
    if not checks:
        status = STATUS_READY
    elif any(check.status == STATUS_ATTENTION for check in checks):
        status = STATUS_ATTENTION
    elif all(check.status == STATUS_NOT_ENABLED for check in checks):
        status = STATUS_NOT_ENABLED
    else:
        status = STATUS_READY
    return {
        "name": name,
        "status": status,
        "checks": [check.to_dict() for check in checks],
    }


def verify_state(base_dir: str | None = None, vault_path: str = "vault.bin"):
    base_dir = base_dir or state_dir()
    checks: list[OperationCheck] = []
    store = LocalStateStore(base_dir)
    layout = store.inspect_layout(EXPECTED_STATE_FILES)

    if not layout["root_present"]:
        checks.append(
            OperationCheck(
                "local_state",
                STATUS_ATTENTION,
                "local state is not initialized",
            )
        )
        return _report("verify-state", checks)

    checks.append(
        OperationCheck(
            "local_state",
            STATUS_READY,
            "local state directory is present",
        )
    )
    checks.append(
        OperationCheck(
            "state_permissions",
            STATUS_READY if layout["root_secure"] else STATUS_ATTENTION,
            "local state permissions are restricted",
        )
    )

    present_files = layout["present_files"]
    checks.append(
        OperationCheck(
            "state_material",
            (
                STATUS_READY
                if len(present_files) == len(EXPECTED_STATE_FILES)
                else STATUS_ATTENTION
            ),
            (
                "required local state material is present"
                if len(present_files) == len(EXPECTED_STATE_FILES)
                else "local state material is incomplete"
            ),
        )
    )

    checks.append(
        OperationCheck(
            "state_file_permissions",
            STATUS_READY if layout["files_secure"] else STATUS_ATTENTION,
            "local state files have restricted permissions",
        )
    )

    checks.append(
        OperationCheck(
            "container",
            STATUS_READY if os.path.exists(vault_path) else STATUS_ATTENTION,
            (
                "local container is present"
                if os.path.exists(vault_path)
                else "local container is not initialized"
            ),
        )
    )

    binding_status = hardware_binding_status()
    if not binding_status.host_supported:
        checks.append(
            OperationCheck(
                "hardware_binding",
                STATUS_NOT_ENABLED,
                "device binding status is not available on this host",
            )
        )
    else:
        checks.append(
            OperationCheck(
                "hardware_binding",
                (
                    STATUS_READY
                    if binding_status.device_binding_available
                    else STATUS_ATTENTION
                ),
                (
                    "device binding material is available"
                    if binding_status.device_binding_available
                    else "device binding material is not present"
                ),
            )
        )

    checks.append(
        OperationCheck(
            "external_binding",
            (
                STATUS_READY
                if binding_status.external_binding_configured
                else STATUS_NOT_ENABLED
            ),
            (
                "supplemental key material source is configured"
                if binding_status.external_binding_configured
                else "supplemental key material source is not configured"
            ),
        )
    )
    return _report("verify-state", checks)


def _audit_path(path: str | None = None) -> str:
    return path or os.path.join(state_dir(), AUDIT_LOG_NAME)


def _audit_auth_path(path: str | None = None, audit_path: str | None = None) -> str:
    if path:
        return path
    if audit_path:
        return os.path.join(os.path.dirname(audit_path), AUDIT_AUTH_NAME)
    return os.path.join(state_dir(), AUDIT_AUTH_NAME)


def verify_audit_log(path: str | None = None, auth_path: str | None = None):
    path = _audit_path(path)
    auth_path = _audit_auth_path(auth_path, audit_path=path)
    checks: list[OperationCheck] = []

    if not os.path.exists(path):
        checks.append(
            OperationCheck(
                "audit_log",
                STATUS_NOT_ENABLED,
                "audit log is not present",
            )
        )
        return _report("verify-audit-log", checks)

    records = []
    parse_errors = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            records.append(record)

    checks.append(
        OperationCheck(
            "audit_parse",
            STATUS_READY if parse_errors == 0 else STATUS_ATTENTION,
            "audit records parse as JSON lines",
        )
    )

    schema_ok = all(
        isinstance(record, dict) and "event" in record and "ts" in record
        for record in records
    )
    checks.append(
        OperationCheck(
            "audit_schema",
            STATUS_READY if schema_ok else STATUS_ATTENTION,
            "audit records use the expected minimal schema",
        )
    )

    chain_records = [
        record
        for record in records
        if _previous_hash_field(record) and _entry_hash_field(record)
    ]
    if chain_records and len(chain_records) == len(records):
        auth_present = os.path.exists(auth_path)
        checks.append(
            OperationCheck(
                "audit_verifier",
                STATUS_READY if auth_present else STATUS_ATTENTION,
                (
                    "audit verifier material is present"
                    if auth_present
                    else "audit verifier material is not present"
                ),
            )
        )
        integrity_ok, _errors = verify_log_integrity(path=path, auth_path=auth_path)
        checks.append(
            OperationCheck(
                "audit_chain",
                STATUS_READY if integrity_ok else STATUS_ATTENTION,
                (
                    "audit integrity verification completed"
                    if integrity_ok
                    else "audit integrity verification requires attention"
                ),
            )
        )
    else:
        checks.append(
            OperationCheck(
                "audit_chain",
                STATUS_NOT_ENABLED,
                "audit chain data is not recorded",
            )
        )

    return _report("verify-audit-log", checks)


def _previous_hash_field(record):
    if "previous_hash" in record:
        return "previous_hash"
    if "prev_hash" in record:
        return "prev_hash"
    return None


def _entry_hash_field(record):
    if "entry_hash" in record:
        return "entry_hash"
    if "event_hash" in record:
        return "event_hash"
    return None


def redact_audit_record(record: dict):
    redacted = {key: record[key] for key in REDACTED_AUDIT_FIELDS if key in record}
    redacted["details_redacted"] = any(
        key not in REDACTED_AUDIT_FIELDS for key in record
    )
    return redacted


def export_redacted_log(output_path: str, input_path: str | None = None):
    input_path = _audit_path(input_path)
    if not os.path.exists(input_path):
        return _report(
            "export-redacted-log",
            [
                OperationCheck(
                    "audit_log",
                    STATUS_NOT_ENABLED,
                    "audit log is not present",
                )
            ],
        )

    count = 0
    with (
        open(input_path, "r", encoding="utf-8") as source,
        open(output_path, "w", encoding="utf-8") as target,
    ):
        for line in source:
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            target.write(json.dumps(redact_audit_record(record), sort_keys=True) + "\n")
            count += 1

    try:
        os.chmod(output_path, 0o600)
    except OSError:
        pass

    return _report(
        "export-redacted-log",
        [
            OperationCheck(
                "redacted_export",
                STATUS_READY,
                f"{count} audit records exported",
            )
        ],
    )


def doctor():
    state_report = verify_state()
    audit_report = verify_audit_log()
    checks = [
        OperationCheck(
            "state",
            state_report["status"],
            "local state check completed",
        ),
        OperationCheck(
            "audit",
            audit_report["status"],
            "audit log check completed",
        ),
    ]
    return _report("doctor", checks)
