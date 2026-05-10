# Design Note: `phasmid touch-vault` (SH-15)

## Question

Should Phasmid add a `phasmid touch-vault` command to rewrite `vault.bin` timestamps
(mtime/atime) in order to reduce recent-use inference?

## Current Decision

Do **not** add this command in the current cycle.

## Rationale

- Timestamp rewriting can itself create an observable pattern if operators run it
  inconsistently.
- Automatic timestamp randomization is operationally risky and can interfere with
  backup/sync workflows and forensic timeline interpretation.
- The new Doctor checks already surface timestamp hygiene (`Recent File Activity`)
  and baseline-size drift (`Vault Size Record`) without mutating user data.

## Safe Interim Posture

- Keep `phasmid doctor` as a non-gating diagnostic tool.
- Provide warning-level feedback when recent vault usage is visible.
- Document local operational procedures separately for environments that need
  explicit timestamp management.

## Revisit Criteria

Revisit this decision only if:

- there is a documented operator workflow for deterministic timestamp handling, and
- tests demonstrate that the command does not create new capture-visible leakage
  patterns or compatibility regressions.
