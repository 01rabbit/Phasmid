# Phasmid Configuration Reference

This document is the single source of truth for runtime environment variables.
All `PHASMID_*` reads are centralized in `src/phasmid/config.py`.

## Environment Variables

| Variable | Type | Default | Scope | Behavior | Equivalent Setting |
|---|---|---|---|---|---|
| `PHASMID_STATE_DIR` | path | `.state` | CLI/WebUI/TUI | Base local state directory when tmpfs override is not set | `config.state_dir()` |
| `PHASMID_TMPFS_STATE` | path | unset | CLI/WebUI/TUI | Overrides state directory with volatile path (intended tmpfs) | `config.tmpfs_state_dir()` |
| `PHASMID_FIELD_MODE` | bool | `false` | WebUI/TUI/CLI messaging | Reduces capture-visible detail in standard surfaces | `config.field_mode_enabled()` |
| `PHASMID_PURGE_CONFIRMATION` | bool | `true` | Restricted actions | Requires explicit typed confirmation for destructive flow | `config.purge_confirmation_required()` |
| `PHASMID_DURESS_MODE` | bool | `false` | WebUI behavior | Enables restricted-recovery related behavior gates | `config.duress_mode_enabled()` |
| `PHASMID_DUAL_APPROVAL` | bool | `false` | Restricted actions | Enables dual-passphrase approval workflow | `config.dual_approval_enabled()` |
| `PHASMID_MIN_PASSPHRASE_LENGTH` | int (>=1) | `10` | Store/init passphrase policy | Minimum accepted passphrase length | `config.passphrase_min_length()` |
| `PHASMID_ACCESS_MAX_FAILURES` | int (>=1) | `5` | Access limiter | Failure count threshold before lockout | `config.access_max_failures()` |
| `PHASMID_ACCESS_LOCKOUT_SECONDS` | int (>=1) | `60` | Access limiter | Lockout duration after threshold exceeded | `config.access_lockout_seconds()` |
| `PHASMID_WEB_TOKEN` | string | random per process | WebUI mutations | Fixed mutation token if provided; else generated at startup | `config.web_token_env()` |
| `PHASMID_HOST` | host string | `127.0.0.1` | WebUI server | Bind host for WebUI process | `config.web_host()` |
| `PHASMID_PORT` | int (>=1) | `8000` | WebUI server | Bind port for WebUI process | `config.web_port()` |
| `PHASMID_MAX_UPLOAD_BYTES` | int (>=1) | `26214400` | WebUI store/metadata | Upload size ceiling in bytes | `config.max_upload_bytes()` |
| `PHASMID_RESTRICTED_SESSION_SECONDS` | int (>=1) | `120` | WebUI restricted session | Restricted confirmation session TTL | `config.restricted_session_seconds()` |
| `PHASMID_AUDIT` | bool | `false` | Audit logging | Enables optional audit event logging | `config.audit_enabled()` |
| `PHASMID_AUDIT_FILENAMES` | enum (`hash` or unset) | unset | Audit logging | If `hash`, stores filename hash instead of presence-only marker | `config.audit_filename_mode()` |
| `PHASMID_PROFILE` | enum (`standard`, `field`, `maintenance`) | `standard` | Capability policy | Selects capability set and maintenance quietness | `config.profile_name()` |
| `PHASMID_HARDWARE_SECRET_FILE` | path | unset | KDF external factor | Adds file-backed secret material to KDF secret set | `config.hardware_secret_file()` |
| `PHASMID_HARDWARE_SECRET` | string | unset | KDF external factor | Adds env-supplied secret material to KDF secret set | `config.hardware_secret_value()` |
| `PHASMID_HARDWARE_SECRET_PROMPT` | bool-like (`1` enabled) | unset | KDF external factor | Prompts operator for extra key material | `config.hardware_secret_prompt_enabled()` |
| `PHASMID_STATE_SECRET` | string | unset | Local state encryption | Overrides local state key with environment-derived secret | `config.state_secret()` |
| `PHASMID_UI_FACE_LOCK` | bool | `false` | UI lock | Enables face-lock gate in supported flows | `config.ui_face_lock_enabled()` |
| `PHASMID_UI_FACE_ENROLL` | bool | `false` | UI lock | Enables face enrollment flow | `config.ui_face_enrollment_enabled()` |
| `PHASMID_UI_FACE_SESSION_SECONDS` | int (>=1) | component default | UI lock session store | Session TTL override for in-memory face sessions | `config.ui_face_session_seconds(default)` |
| `PHASMID_UI_FACE_ENROLL_SECONDS` | int (>=1) | component default | UI lock enrollment | Enrollment request TTL override | `config.ui_face_enroll_seconds(default)` |
| `PHASMID_DEBUG` | bool | `false` | Diagnostics | Enables debug-mode warning in doctor output | `config.debug_enabled()` |
| `PHASMID_DOCTOR_RECENT_SECONDS` | int (>=1) | `86400` | Doctor | Window for “recent vault activity” warning | `config.doctor_recent_seconds()` |
| `PHASMID_ENABLE_DISPLAY` | bool | `false` | Bridge UI simulator | Enables OpenCV preview window for display simulator | `config.display_enabled()` |
| `PHASMID_DARK` | bool | `false` | TUI theming | Optional dark theme selection flag | `config.tui_dark_enabled()` |
| `PHASMID_LIGHT` | bool | `false` | TUI theming | Optional light theme selection flag | `config.tui_light_enabled()` |
