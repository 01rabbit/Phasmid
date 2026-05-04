# State Recovery

Phantasm treats local state recovery as a controlled diagnostic process, not as a bypass.

## Principles

- Prefer diagnosis over repair.
- Do not rewrite unknown state automatically.
- Do not expose state paths in normal output.
- Do not reveal internal storage labels in CLI or WebUI messages.
- Do not treat flash-media overwrite as guaranteed deletion.

## Diagnostic Commands

Use:

```bash
python3 main.py verify-state
python3 main.py doctor
```

If local state is incomplete, the safest response is usually to reinitialize through the documented restricted flow rather than editing state files manually.

## Audit Review

If audit logging was enabled:

```bash
python3 main.py verify-audit-log
python3 main.py export-redacted-log --out review-events.jsonl
```

`verify-audit-log` checks the local audit chain and the verifier material used for local integrity review.

The redacted export is intended for review. It should not include local paths, file labels, object-cue features, face-lock templates, or password-derived data.

## Field Review

State recovery checks should be recorded in `docs/REVIEW_VALIDATION_RECORD.md` when performed on target hardware.
