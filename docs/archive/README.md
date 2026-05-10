# Archive Policy (docs/archive)

This directory stores historical documentation that is no longer part of the
active operational baseline but is kept for traceability.

## What belongs in archive

Move documents here when they are primarily:

- completed analysis records (`*_ANALYSIS.md`)
- completed evaluation artifacts (`*_EVALUATION*.md`)
- completed planning records (`*_PLAN.md`)
- historical drafts (`*_DRAFT.md`)
- implementation notes superseded by merged behavior

## What should not be archived

Do not archive active authority and operator-facing baseline documents:

- `docs/THREAT_MODEL.md`
- `docs/SPECIFICATION.md`
- `README.md`
- `docs/CLAIMS.md`
- `docs/NON_CLAIMS.md`
- `docs/PHASMID_ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `docs/RESTRICTED_ACTIONS.md`
- `docs/TUI_OPERATOR_CONSOLE.md`
- deployment and field-validation runbooks currently in use

## Archiving rules

1. Keep file names unchanged when moving to preserve traceability.
2. Update all in-repo links that pointed to the old path.
3. Keep historical references explicit (for example, in `ROADMAP_HISTORY.md`).
4. Do not move files that are still cited as active authority in `AGENTS.md`.
5. Prefer small, periodic archive moves instead of large one-time sweeps.

## Notes

Archived documents are informational history, not operational authority.
When content conflicts, follow the authority order defined in `AGENTS.md` and
summarized in `docs/README_INDEX.md`.
