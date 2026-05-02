# Raspberry Pi Zero 2 W Deployment

This is a compact deployment summary. The authoritative appliance deployment guide is `docs/RPI_ZERO_APPLIANCE_DEPLOYMENT.md`.

This document describes a conservative local appliance deployment for Raspberry Pi Zero 2 W class hardware.

Phantasm should remain local-only. The expected access path is localhost during development or USB Ethernet gadget mode during appliance use. Do not expose the WebUI to an untrusted network.

## Network Posture

- Bind the WebUI to `127.0.0.1` by default.
- Use USB Ethernet gadget access for the operator interface when needed.
- Disable SSH by default.
- Disable Wi-Fi and Bluetooth by default unless explicitly required for a controlled deployment.
- Do not add cloud unlock, telemetry, analytics, or remote management.
- Configure a firewall so only localhost or the intended USB-side management address can reach the service.

## Service Account

- Run Phantasm as a dedicated unprivileged service user.
- Keep the runtime state directory owned by that user.
- Use `0700` for the state directory.
- Use `0600` for state files.
- Do not run the WebUI as root.

## Storage and Temporary Files

- Keep `vault.bin` and the configured state directory on encrypted local storage when possible.
- Disable swap for the appliance deployment.
- Use `tmpfs` for upload and temporary working directories where practical.
- Keep audit logging disabled by default.
- Keep debug mode disabled by default.

## Key-Material Destruction

Restricted local data-loss behavior should be understood primarily as key-material destruction and local access-path invalidation.

On SD cards and other flash media, overwrite behavior is best effort only. Wear leveling, snapshots, backups, filesystem journals, and controller behavior can leave old data behind. Recovery resistance depends primarily on destruction, rotation, or removal of required key material such as `.state/access.bin`, plus any external values supplied through deployment policy.

Best-effort overwrite may still be attempted, but it must not be described as guaranteed secure deletion.

## Example systemd Unit

Adjust paths and user names for the target image.

```ini
[Unit]
Description=Phantasm local WebUI
After=network.target

[Service]
Type=simple
User=phantasm
Group=phantasm
WorkingDirectory=/opt/phantasm
Environment=PYTHONPATH=/opt/phantasm/src
Environment=PHANTASM_HOST=127.0.0.1
Environment=PHANTASM_PORT=8000
Environment=PHANTASM_FIELD_MODE=1
Environment=PHANTASM_AUDIT=0
Environment=PHANTASM_DEBUG=0
ExecStart=/usr/bin/python3 -m phantasm.web_server
Restart=on-failure
RestartSec=2

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/phantasm /var/lib/phantasm
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
LockPersonality=true
MemoryDenyWriteExecute=true

[Install]
WantedBy=multi-user.target
```

## Operational Checklist

- Create a dedicated `phantasm` user.
- Place code under `/opt/phantasm`.
- Place runtime state under `/var/lib/phantasm` or another dedicated directory.
- Set `PHANTASM_STATE_DIR` to that runtime path.
- Confirm directory mode `0700`.
- Confirm state file mode `0600`.
- Confirm SSH is disabled unless explicitly needed.
- Confirm Wi-Fi and Bluetooth are disabled unless explicitly needed.
- Confirm swap is disabled.
- Confirm firewall policy blocks unintended inbound traffic.
- Run the full test suite before appliance packaging.
