# Field Test Procedure

This procedure evaluates local leakage, operational clarity, recovery behavior, key separation, and user-error resistance.

Physical shock resistance and tamper-resistant casing are out of scope for the Raspberry Pi Zero 2 W prototype. This procedure evaluates local leakage, offline operation, key separation, power-loss behavior, response headers, logs, and user-error resistance.

## Boot and Service

- Boot without network dependency.
- Confirm WebUI binds to `127.0.0.1`.
- Confirm USB gadget access if configured.
- Confirm audit is disabled by default.
- Confirm debug is disabled by default.
- Confirm Field Mode is enabled for appliance evaluation.
- If the optional LUKS storage layer is used, confirm the encrypted volume opens and mounts before Phantasm starts.
- If the optional LUKS storage layer is used, confirm Phantasm fails closed when the encrypted volume is not mounted.

## Store and Retrieve

- Initialize an empty local container.
- Store a small text file.
- Store a binary file.
- Run metadata risk check on a file with obvious path or author text.
- Confirm unsupported metadata reduction fails safely.
- Retrieve with correct password and object cue.
- Retrieve with wrong password.
- Retrieve with object not detected.
- Test object ambiguity if two similar cues are configured.

## Restricted Behavior

- Confirm `/emergency` initially shows only restricted confirmation.
- Confirm restricted actions appear only after fresh restricted confirmation.
- Confirm typed action phrases are required.
- Confirm stale restricted sessions are rejected.
- Confirm retrieval does not show local-state side-effect messages or headers.

## Field Mode Maintenance

- Confirm Maintenance hides state path before restricted confirmation.
- Confirm audit export is hidden before restricted confirmation.
- Confirm token rotation is hidden before restricted confirmation.
- Confirm detailed diagnostics are hidden before restricted confirmation.
- Confirm Entry Management details are withheld before restricted confirmation.

## Capture-Visible Surfaces

- Review CLI output.
- Review browser console.
- Review response headers.
- Review download filenames.
- Review optional audit logs if enabled.
- Review systemd logs.
- Review shell history.
- Review temporary directories.

## Faults

- Test sudden power loss during idle.
- Test sudden power loss during Store.
- Test sudden power loss during Retrieve.
- Test sudden power loss after restricted recovery.
- Review the systemd journal after each power-loss case.
- Review temporary upload directories after each power-loss case.
- Test no network availability.
- Test no-network boot with the optional LUKS storage layer if used.
- Test camera unavailable.
- Test USB gadget-only access.

Record failures with exact screen text, command output, and response headers.
