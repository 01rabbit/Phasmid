# LUKS Layer (Stub)

This document is a phase-B stub for LUKS wrapper integration.

## Scope in This Phase

- privileged wrapper path: `/usr/local/bin/phasmid-luks-mount`
- wrapper script source: `scripts/luks_mount.sh`
- mount/unmount/status/brick command stubs only

## Sudoers (minimum privilege)

```text
phasmid ALL=(root) NOPASSWD: /usr/local/bin/phasmid-luks-mount
```

No wildcard sudo rules are required for this phase.

## Notes

- The wrapper script performs best-effort operations only.
- Complete physical media sanitization is not guaranteed.
- Full threat-model and operating procedure content is tracked for Phase 17-E.
