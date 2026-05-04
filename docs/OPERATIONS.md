# Local Operations

This document describes repeatable local checks for operators and reviewers.

These commands do not unlock protected entries, do not perform restricted actions, and do not print filesystem paths in normal output.

## Commands

Check local state readiness:

```bash
python3 main.py verify-state
```

Expected neutral output shape:

```text
verify-state: ready
- local_state: ready - local state directory is present
- state_permissions: ready - local state permissions are restricted
```

Check the optional audit log:

```bash
python3 main.py verify-audit-log
```

If audit logging is disabled or no audit log is present, the command reports `not_enabled`. This is not a failure by itself because audit logging is disabled by default for field deployments.

Summarize local health:

```bash
python3 main.py doctor
```

Export a redacted audit log for review:

```bash
python3 main.py export-redacted-log --out review-events.jsonl
```

The redacted export uses a fixed schema and omits detailed fields that could reveal file labels, local paths, or operational grouping.

## Output Rules

Operational commands should report:

- readiness status;
- neutral check names;
- whether attention is required.

Operational commands should not report:

- local filesystem paths;
- internal storage labels;
- object-cue feature data;
- face-lock template data;
- password-derived data;
- detailed restricted-action failure reasons.

## Test Linkage

The local operations commands are covered by automated tests in `tests/test_operations.py`. Field validation still requires the Field Test Procedure and Seizure Review Checklist.

Restricted-flow procedure coverage is tracked in `tests/scenarios/restricted_flows.json` and validated by `tests/test_scenarios.py`.
