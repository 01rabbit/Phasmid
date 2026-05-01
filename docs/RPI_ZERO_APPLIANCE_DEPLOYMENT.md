# Raspberry Pi Zero 2 W Appliance Deployment

This deployment plan reduces exposed services and local leakage for Raspberry Pi Zero 2 W class hardware. It does not provide physical tamper resistance.

## Base System

- Use Raspberry Pi OS Lite with only required packages installed.
- Create a dedicated `phantasm` system user.
- Place the application under `/opt/phantasm`.
- Place runtime state under `/var/lib/phantasm` or another dedicated local directory.
- Set `umask 077` for provisioning and service execution.
- Keep the configured state directory mode `0700`.
- Keep sensitive state files mode `0600`.
- Keep audit disabled by default.
- Keep debug disabled by default.
- Disable swap or minimize it as far as the device workload allows.
- Use `tmpfs` for uploads and temporary files when practical.
- Do not add cloud dependencies, telemetry, analytics, remote unlock, or remote management.

## Local-Only Network Posture

- Bind the WebUI to `127.0.0.1` by default.
- Use USB Ethernet gadget access for local operator access when required.
- Disable SSH after provisioning unless a controlled maintenance window requires it.
- Disable Wi-Fi unless explicitly needed.
- Disable Bluetooth.
- Allow loopback traffic.
- Allow the USB gadget interface only when explicitly configured.
- Deny inbound traffic from all other interfaces.
- Do not expose the WebUI as an Internet-facing service.

## Recommended Environment

```text
PHANTASM_FIELD_MODE=1
PHANTASM_AUDIT=0
PHANTASM_DEBUG=0
PHANTASM_HOST=127.0.0.1
PHANTASM_PORT=8000
PHANTASM_STATE_DIR=/var/lib/phantasm
```

For high-risk deployments, do not store all recovery conditions on the same physical medium. Phantasm is strongest when the encrypted container, local state, memorized password, physical-object cue, and optional external key material are separated.

## systemd Service

An example unit is provided at `contrib/systemd/phantasm.service`.

Recommended hardening options include:

```ini
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/phantasm /var/lib/phantasm /run/phantasm
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
SystemCallFilter=@system-service
UMask=0077
MemoryDenyWriteExecute=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
```

Adjust `ReadWritePaths` to match the actual application and state paths. Do not place external key material directly in the unit file.

## Firewall Guidance

The appliance should deny inbound traffic except loopback and the explicitly configured USB gadget interface.

Example policy goals:

- allow `lo`;
- allow the USB-side local address if used;
- deny inbound from Wi-Fi, Ethernet, and other interfaces;
- deny Internet-facing WebUI access;
- keep remote unlock and remote management out of scope.

## Key Material and Storage

On flash media, complete overwrite-based deletion cannot be guaranteed across every storage layer. Phantasm therefore treats restricted recovery primarily as key-path invalidation and key-material destruction, with best-effort overwrite as a secondary measure.

External key material can be supplied with `PHANTASM_HARDWARE_SECRET_FILE` or `PHANTASM_HARDWARE_SECRET_PROMPT=1`. For high-risk deployment, store external key material away from the same SD card that holds `vault.bin` and the state directory.
