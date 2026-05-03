# Raspberry Pi Zero 2 W Appliance Deployment

This is the authoritative Raspberry Pi Zero 2 W appliance deployment guide for Phantasm.

This deployment plan reduces exposed services and local leakage for Raspberry Pi Zero 2 W class hardware. It does not provide physical tamper resistance, anti-forensic guarantees, or hardware-grade secure storage.

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

## Camera Module

Recommended camera for the Raspberry Pi Zero 2 W prototype:

- Raspberry Pi Camera Module 3 NoIR Wide
- Sony IMX708 12MP sensor
- Mechanical autofocus
- Wide FoV
- NoIR support for optional infrared illumination
- CSI connection

Raspberry Pi Zero 2 W requires a 22-pin to 15-pin Raspberry Pi Zero camera cable. The standard 15-pin camera cable is not compatible with the Pi Zero camera connector.

The camera is used as an operational object-cue capture device. It is not treated as cryptographic key material, biometric identity proof, or a tamper-resistant sensor.

## Physical Signature Reduction (Stealth)

To prevent the device from drawing attention via LEDs or serial console activity:

### Disable LEDs

Add the following to `/boot/config.txt`:

```text
# Disable Power LED
dtparam=pwr_led_trigger=none
dtparam=pwr_led_activelow=off
# Disable Activity LED
dtparam=act_led_trigger=none
dtparam=act_led_activelow=off
```

### Suppress Boot Console

In `/boot/cmdline.txt`, add `consoleblank=0 loglevel=1 quiet` and remove `console=tty1` to ensure no text is emitted to a connected display during boot.

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

## Optional LUKS Storage Layer

An optional dm-crypt/LUKS2 layer can be used as defense in depth for appliance deployments. This is not a compliance claim and does not make Phantasm certified data-at-rest infrastructure.

Use this only after confirming the target SD card layout. The commands below can erase data if pointed at the wrong device.

Recommended placement:

- dedicate a separate partition or external local volume for Phantasm runtime data;
- mount it at `/var/lib/phantasm-secure` or another dedicated path;
- set `PHANTASM_STATE_DIR` to a directory on that mounted volume;
- keep `vault.bin` on the same encrypted volume or another encrypted local path;
- use a storage-layer passphrase that is different from Phantasm access passwords.

Example setup outline:

```bash
sudo cryptsetup luksFormat --type luks2 /dev/mmcblk0p3
sudo cryptsetup luksOpen /dev/mmcblk0p3 phantasm-state
sudo mkfs.ext4 -m 0 /dev/mapper/phantasm-state
sudo mkdir -p /var/lib/phantasm-secure
sudo mount /dev/mapper/phantasm-state /var/lib/phantasm-secure
sudo mkdir -p /var/lib/phantasm-secure/.state
sudo chown -R phantasm:phantasm /var/lib/phantasm-secure
sudo chmod 0700 /var/lib/phantasm-secure /var/lib/phantasm-secure/.state
```

Service environment example:

```ini
Environment=PHANTASM_STATE_DIR=/var/lib/phantasm-secure/.state
WorkingDirectory=/var/lib/phantasm-secure
ReadWritePaths=/var/lib/phantasm-secure
```

Boot and service ordering:

- The encrypted volume must be opened and mounted before `phantasm.service` starts.
- If the volume is unavailable, the service should fail closed rather than create a fallback state directory on unencrypted storage.
- Record the mount procedure in the deployment notes.
- Test reboot, mount failure, and no-network startup before field evaluation.

Recovery and backup notes:

- Losing the LUKS passphrase can make the local Phantasm state unavailable.
- Backups of the encrypted volume should be handled as sensitive local media.
- Do not store storage-layer passphrases, Phantasm access passwords, and optional external key material together.
- SD card cloning can copy encrypted containers and stale state; review cloned media before reuse.
