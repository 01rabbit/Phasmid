#!/usr/bin/env bash
# scripts/pi_zero2w/collect_system_info.sh
#
# Collect target hardware and OS metadata from the Raspberry Pi via SSH.
# Called by run_remote_perf.sh; reads the same env vars.
# Output is plain text suitable for logging and inclusion in reports.

set -uo pipefail

for var in PHASMID_PI_HOST PHASMID_PI_USER PHASMID_PI_SSH_PORT; do
    if [[ -z "${!var:-}" ]]; then
        printf 'ERROR: %s is not set\n' "$var" >&2
        exit 1
    fi
done

SSH_OPTS=(
    -p "$PHASMID_PI_SSH_PORT"
    -o BatchMode=yes
    -o ConnectTimeout=15
    -o StrictHostKeyChecking=accept-new
)
[[ -n "${PHASMID_PI_SSH_KEY:-}" ]] && SSH_OPTS+=(-i "$PHASMID_PI_SSH_KEY")

pi_ssh() {
    env -u PHASMID_TMPFS_STATE \
        ssh "${SSH_OPTS[@]}" "$PHASMID_PI_USER@$PHASMID_PI_HOST" "$@"
}

printf '[sysinfo] Collecting system information from %s ...\n' "$PHASMID_PI_HOST"

pi_ssh "
set -uo pipefail

sep() { printf '  %-20s %s\n' \"\$1\" \"\$2\"; }

printf '\n[target hardware]\n'
sep 'hostname:'     \"\$(hostname 2>/dev/null || echo unknown)\"
sep 'arch:'         \"\$(uname -m)\"
sep 'kernel:'       \"\$(uname -r)\"

os_name=\$(grep '^PRETTY_NAME' /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '\"' || echo unknown)
sep 'os:'           \"\$os_name\"

sep 'python:'       \"\$(python3 --version 2>&1 || echo unavailable)\"

printf '\n[memory]\n'
mem_total=\$(grep MemTotal  /proc/meminfo | awk '{print \$2}')
mem_avail=\$(grep MemAvailable /proc/meminfo | awk '{print \$2}')
sep 'mem_total:'    \"\${mem_total} kB\"
sep 'mem_available:' \"\${mem_avail} kB\"

swap_total=\$(grep SwapTotal /proc/meminfo | awk '{print \$2}')
if [[ \"\$swap_total\" == '0' ]]; then
    sep 'swap:'     'disabled (good)'
else
    sep 'swap:'     \"ENABLED — \${swap_total} kB (may affect KDF timing measurements)\"
fi

printf '\n[storage]\n'
disk_info=\$(df -h \"\${PHASMID_PI_REMOTE_DIR:-\$HOME}\" 2>/dev/null | tail -1 || df -h / | tail -1)
sep 'disk_avail:'   \"\$(echo \"\$disk_info\" | awk '{print \$4}')\"
sep 'disk_used:'    \"\$(echo \"\$disk_info\" | awk '{print \$3}')\"
sep 'disk_total:'   \"\$(echo \"\$disk_info\" | awk '{print \$2}')\"

# Detect if /tmp is tmpfs
if findmnt -n -o FSTYPE /tmp 2>/dev/null | grep -q tmpfs; then
    sep 'tmpfs:/tmp:'  'yes'
else
    sep 'tmpfs:/tmp:'  'no'
fi

printf '\n[thermal]\n'
if command -v vcgencmd > /dev/null 2>&1; then
    temp_out=\$(vcgencmd measure_temp 2>/dev/null || echo 'unavailable')
    sep 'temperature:' \"\$temp_out\"

    throttled=\$(vcgencmd get_throttled 2>/dev/null || echo 'unavailable')
    sep 'throttled:'   \"\$throttled\"
    if [[ \"\$throttled\" != 'throttled=0x0' ]] && [[ \"\$throttled\" != 'unavailable' ]]; then
        printf '  WARNING: Non-zero throttle status detected.\n'
        printf '           0x50000 = under-voltage, 0x20002 = currently throttled.\n'
        printf '           Thermal or power issues may affect timing measurements.\n'
    fi
else
    temp_path=/sys/class/thermal/thermal_zone0/temp
    if [[ -f \"\$temp_path\" ]]; then
        raw=\$(cat \"\$temp_path\")
        temp_c=\$(awk \"BEGIN{printf \\\"%.1f\\\", \$raw/1000}\")
        sep 'temperature:' \"\${temp_c} C (via thermal_zone0)\"
    else
        sep 'temperature:' 'unavailable'
    fi
    sep 'throttled:' 'vcgencmd not available'
fi

printf '\n[system load]\n'
load=\$(uptime 2>/dev/null | awk -F'load average:' '{print \$2}' | tr -d ' ')
sep 'load_avg:'    \"\$load\"

printf '\n'
" 2>&1

printf '[sysinfo] Done.\n'
