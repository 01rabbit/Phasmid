#!/usr/bin/env bash
# scripts/pi_zero2w/run_remote_perf.sh
#
# Top-level entry point for Phasmid Pi Zero 2W remote field testing.
# Run from macOS. All test phases execute on the target Pi via SSH.
#
# Required environment variables:
#   PHASMID_PI_HOST       Hostname or IP of the Raspberry Pi
#   PHASMID_PI_USER       SSH username on the Pi
#   PHASMID_PI_REMOTE_DIR Absolute path to working directory on the Pi
#   PHASMID_PI_SSH_PORT   SSH port (typically 22)
# Optional:
#   PHASMID_PI_SSH_KEY    Path to SSH private key (uses ssh-agent if unset)
#
# Usage:
#   export PHASMID_PI_HOST=phasmid-pi.local
#   export PHASMID_PI_USER=pi
#   export PHASMID_PI_REMOTE_DIR=/home/pi/Phasmid
#   export PHASMID_PI_SSH_PORT=22
#   ./scripts/pi_zero2w/run_remote_perf.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── Environment validation ─────────────────────────────────────────────────────

MISSING=()
for var in PHASMID_PI_HOST PHASMID_PI_USER PHASMID_PI_REMOTE_DIR PHASMID_PI_SSH_PORT; do
    [[ -z "${!var:-}" ]] && MISSING+=("$var")
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    printf 'ERROR: Missing required environment variables:\n' >&2
    for v in "${MISSING[@]}"; do printf '  %s\n' "$v" >&2; done
    printf '\nSet them before running, for example:\n' >&2
    printf '  export PHASMID_PI_HOST=phasmid-pi.local\n' >&2
    printf '  export PHASMID_PI_USER=pi\n' >&2
    printf '  export PHASMID_PI_REMOTE_DIR=/home/pi/Phasmid\n' >&2
    printf '  export PHASMID_PI_SSH_PORT=22\n' >&2
    exit 1
fi

# Guard against PHASMID_TMPFS_STATE leaking into the test environment.
# If this variable is set but the path does not exist on the Pi, both the CLI
# and the WebUI will fail at startup with RuntimeError.
if [[ -n "${PHASMID_TMPFS_STATE:-}" ]]; then
    printf 'WARNING: PHASMID_TMPFS_STATE="%s" is set in the current shell.\n' "$PHASMID_TMPFS_STATE" >&2
    printf '         This variable must NOT be active during field test runs unless\n' >&2
    printf '         a tmpfs mount is provisioned on the Pi at that path.\n' >&2
    printf '         Unset it before running: unset PHASMID_TMPFS_STATE\n' >&2
    printf '         Continuing anyway — remote commands will NOT inherit this variable.\n' >&2
fi

# ── SSH helpers ────────────────────────────────────────────────────────────────

SSH_OPTS=(
    -p "$PHASMID_PI_SSH_PORT"
    -o BatchMode=yes
    -o ConnectTimeout=15
    -o StrictHostKeyChecking=accept-new
)
[[ -n "${PHASMID_PI_SSH_KEY:-}" ]] && SSH_OPTS+=(-i "$PHASMID_PI_SSH_KEY")

pi_ssh() {
    # Unset PHASMID_TMPFS_STATE so it is not forwarded to the Pi.
    env -u PHASMID_TMPFS_STATE \
        ssh "${SSH_OPTS[@]}" "$PHASMID_PI_USER@$PHASMID_PI_HOST" "$@"
}

pi_rsync() {
    rsync -az \
        -e "ssh $(printf '%q ' "${SSH_OPTS[@]}")" \
        "$@"
}

# ── Output setup ──────────────────────────────────────────────────────────────

RESULTS_DIR="$REPO_ROOT/release/pi-zero2w"
mkdir -p "$RESULTS_DIR"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_LOG="$RESULTS_DIR/run.log"
: > "$RUN_LOG"

log()  { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*" | tee -a "$RUN_LOG"; }
warn() { log "WARNING: $*"; }
fail() { log "ERROR: $*"; exit 1; }

# Track phase results for summary
declare -A PHASE_RESULTS

phase_ok()   { PHASE_RESULTS["$1"]="ok";   log "  phase $1: ok"; }
phase_fail() { PHASE_RESULTS["$1"]="fail"; warn "phase $1: failed"; }
phase_skip() { PHASE_RESULTS["$1"]="skip"; log "  phase $1: skipped"; }

# ── Phase A: SSH sanity and architecture check ─────────────────────────────────

log "=== Phasmid Pi Zero 2W Remote Field Test — $TIMESTAMP ==="
log "Host     : $PHASMID_PI_HOST:$PHASMID_PI_SSH_PORT"
log "User     : $PHASMID_PI_USER"
log "RemoteDir: $PHASMID_PI_REMOTE_DIR"
log "Results  : $RESULTS_DIR"
log ""
log "--- Phase A: SSH sanity check ---"

if ! pi_ssh "echo connected" > /dev/null 2>&1; then
    fail "Cannot connect to $PHASMID_PI_HOST:$PHASMID_PI_SSH_PORT. Verify the host is reachable and SSH is enabled."
fi
log "SSH connectivity: ok"

ARCH="$(pi_ssh "uname -m" 2>/dev/null || true)"
log "Target architecture: $ARCH"

if [[ "$ARCH" != "aarch64" ]]; then
    fail "Target reports architecture '$ARCH' but 'aarch64' is required.
Flash 64-bit Raspberry Pi OS Lite (not 32-bit) and retry.
32-bit ARM (armv7l) lacks pre-built wheels for key dependencies."
fi

phase_ok "ssh_sanity"

# ── Phase B: System info ──────────────────────────────────────────────────────

log ""
log "--- Phase B: System info ---"
if SYSINFO_OUT="$("$SCRIPT_DIR/collect_system_info.sh" 2>&1)"; then
    printf '%s\n' "$SYSINFO_OUT" | tee -a "$RUN_LOG"
    printf '%s\n' "$SYSINFO_OUT" > "$RESULTS_DIR/sysinfo.txt"
    phase_ok "system_info"
else
    warn "System info collection had errors; continuing"
    phase_fail "system_info"
fi

# ── Phase C: Sync and prepare env ─────────────────────────────────────────────

log ""
log "--- Phase C: Repository sync and environment preparation ---"
INSTALL_LOG="$RESULTS_DIR/install.log"

if "$SCRIPT_DIR/prepare_remote_env.sh" 2>&1 | tee "$INSTALL_LOG" | tee -a "$RUN_LOG"; then
    phase_ok "prepare_env"
else
    warn "Environment preparation failed; see $INSTALL_LOG"
    phase_fail "prepare_env"
fi

# ── Phase D–N: Performance and timing measurements ────────────────────────────

if [[ "${PHASE_RESULTS[prepare_env]:-}" != "fail" ]]; then
    log ""
    log "--- Phase D–N: Performance and timing measurements ---"

    REMOTE_RESULTS_DIR="$PHASMID_PI_REMOTE_DIR/_pi_field_test/results"
    REMOTE_SCRIPT="$PHASMID_PI_REMOTE_DIR/scripts/pi_zero2w/run_local_perf.py"

    if pi_ssh "
        set -uo pipefail
        cd '$PHASMID_PI_REMOTE_DIR'
        mkdir -p '$REMOTE_RESULTS_DIR'
        PHASMID_STATE_DIR='$PHASMID_PI_REMOTE_DIR/_pi_field_test/.state' \
        PHASMID_AUDIT=0 \
        PHASMID_DEBUG=0 \
        .venv/bin/python '$REMOTE_SCRIPT' --results-dir '$REMOTE_RESULTS_DIR'
    " 2>&1 | tee -a "$RUN_LOG"; then
        phase_ok "perf_timing"
    else
        warn "Performance/timing phase failed or partially failed"
        phase_fail "perf_timing"
    fi
else
    warn "Skipping performance phases because environment preparation failed"
    phase_skip "perf_timing"
fi

# ── Phase I: WebUI viability ─────────────────────────────────────────────────

if [[ "${PHASE_RESULTS[prepare_env]:-}" != "fail" ]]; then
    log ""
    log "--- Phase I: WebUI viability ---"

    REMOTE_RESULTS_DIR="$PHASMID_PI_REMOTE_DIR/_pi_field_test/results"

    if pi_ssh "
        set -uo pipefail
        cd '$PHASMID_PI_REMOTE_DIR'
        mkdir -p '$REMOTE_RESULTS_DIR'
        PHASMID_HOST=127.0.0.1 \
        PHASMID_PORT=8001 \
        PHASMID_FIELD_MODE=1 \
        PHASMID_AUDIT=0 \
        PHASMID_DEBUG=0 \
        bash scripts/pi_zero2w/run_webui_probe.sh '$REMOTE_RESULTS_DIR'
    " 2>&1 | tee -a "$RUN_LOG"; then
        phase_ok "webui"
    else
        warn "WebUI probe failed or partially failed"
        phase_fail "webui"
    fi
else
    phase_skip "webui"
fi

# ── Collect results from Pi ───────────────────────────────────────────────────

log ""
log "--- Collecting results from Pi ---"

REMOTE_RESULTS_DIR="$PHASMID_PI_REMOTE_DIR/_pi_field_test/results"
if pi_rsync \
    --no-delete \
    "$PHASMID_PI_USER@$PHASMID_PI_HOST:$REMOTE_RESULTS_DIR/" \
    "$RESULTS_DIR/" 2>&1 | tee -a "$RUN_LOG"; then
    log "Results copied to $RESULTS_DIR"
else
    warn "Could not copy all results from Pi; check $REMOTE_RESULTS_DIR manually"
fi

# ── Summary ───────────────────────────────────────────────────────────────────

log ""
log "=== Phase summary ==="
OVERALL="ok"
for phase in ssh_sanity system_info prepare_env perf_timing webui; do
    status="${PHASE_RESULTS[$phase]:-unknown}"
    log "  $phase: $status"
    [[ "$status" == "fail" ]] && OVERALL="fail"
done

log ""
log "Overall status : $OVERALL"
log "Timestamp      : $TIMESTAMP"
log "Results dir    : $RESULTS_DIR"

if [[ "$OVERALL" == "fail" ]]; then
    log "One or more phases failed. Review $RUN_LOG and partial results in $RESULTS_DIR."
    exit 1
fi
