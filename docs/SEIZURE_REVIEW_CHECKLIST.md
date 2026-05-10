# Seizure Review Checklist

Use this checklist to review what a local observer may learn from normal surfaces. The goal is that normal surfaces do not explain the internal disclosure model.

Review:

- rendered Home screen;
- rendered Store screen;
- rendered Retrieve screen;
- rendered Maintenance screen;
- `/emergency` before restricted confirmation;
- `/emergency` after restricted confirmation;
- browser history;
- browser cache;
- HTML source;
- JavaScript console;
- HTTP response headers;
- download filenames;
- optional audit logs;
- `.state/` filenames;
- temporary upload files;
- shell history;
- systemd logs;
- application stdout and stderr;
- CLI output;
- screenshots;
- README and docs copied to the device;
- environment variables;
- service unit files;
- temporary directories;
- upload directories.

Expected result:

- normal screens use neutral entry language;
- normal screens do not expose storage count or trial order;
- response headers and download names are neutral;
- restricted actions require server-side confirmation and typed action phrases;
- logs and CLI output do not explain structural meaning.

Additional Raspberry Pi LUKS checks (when LUKS is enabled):

- Is the LUKS layer active on the configured state path?
- Is tmpfs key-store material unmounted/cleared after shutdown?
- Is swap disabled or explicitly risk-accepted for this deployment?

This checklist does not make the device tamper-resistant and does not replace operational judgment.
