#!/usr/bin/env bash
# scripts/pi_zero2w/prepare_remote_env.sh
#
# Synchronize the repository to the Raspberry Pi and prepare the Python
# virtual environment. Called by run_remote_perf.sh; reads the same env vars.
#
# Key constraints:
#   - Installs requirements first, then local package entry point.
#   - Verifies that "phasmid --help" succeeds after install.
#   - Does NOT set PHASMID_TMPFS_STATE on the remote side.
#   - Excludes local runtime artifacts from sync (vault.bin, .state, etc.).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

for var in PHASMID_PI_HOST PHASMID_PI_USER PHASMID_PI_REMOTE_DIR PHASMID_PI_SSH_PORT; do
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

has_local_cmd() {
    command -v "$1" >/dev/null 2>&1
}

# ── Step 1: Create remote directory ──────────────────────────────────────────

printf '[prepare] Creating remote directory %s ...\n' "$PHASMID_PI_REMOTE_DIR"
pi_ssh "mkdir -p '$PHASMID_PI_REMOTE_DIR'"

# ── Step 2: Sync repository ───────────────────────────────────────────────────
# Excludes: local runtime artifacts, caches, venv, test artifacts.
# --no-delete: never remove files that exist only on the remote side.

printf '[prepare] Syncing repository to %s:%s ...\n' "$PHASMID_PI_HOST" "$PHASMID_PI_REMOTE_DIR"

if has_local_cmd rsync; then
    rsync -av \
        -e "ssh $(printf '%q ' "${SSH_OPTS[@]}")" \
        --no-delete \
        --exclude='.git/' \
        --exclude='.venv/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='*.pyo' \
        --exclude='.state/' \
        --exclude='vault.bin' \
        --exclude='release/' \
        --exclude='.hypothesis/' \
        --exclude='.mypy_cache/' \
        --exclude='.ruff_cache/' \
        --exclude='.pytest_cache/' \
        --exclude='_pi_field_test/' \
        "$REPO_ROOT/" \
        "$PHASMID_PI_USER@$PHASMID_PI_HOST:$PHASMID_PI_REMOTE_DIR/"
else
    printf '[prepare] rsync not found on macOS host; using tar-over-SSH fallback.\n'
    tar \
        --exclude='.git' \
        --exclude='.venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='*.pyo' \
        --exclude='.state' \
        --exclude='vault.bin' \
        --exclude='release' \
        --exclude='.hypothesis' \
        --exclude='.mypy_cache' \
        --exclude='.ruff_cache' \
        --exclude='.pytest_cache' \
        --exclude='_pi_field_test' \
        -C "$REPO_ROOT" -cf - . \
        | pi_ssh "tar -xf - -C '$PHASMID_PI_REMOTE_DIR'"
fi

printf '[prepare] Sync complete.\n'

# ── Step 3: Create test output directory ──────────────────────────────────────

pi_ssh "mkdir -p '$PHASMID_PI_REMOTE_DIR/_pi_field_test/results'"

# ── Step 4: Validate remote Python and disk before install ───────────────────

printf '[prepare] Validating remote Python and virtualenv support ...\n'
pi_ssh "
set -uo pipefail
if ! command -v python3 >/dev/null 2>&1; then
    printf 'ERROR: python3 is not installed on the target Pi.\n' >&2
    exit 11
fi
if ! python3 -m venv --help >/dev/null 2>&1; then
    printf 'ERROR: python3-venv support is missing. Install python3-venv and retry.\n' >&2
    exit 12
fi
"

printf '[prepare] Checking remote free disk space ...\n'
REMOTE_FREE_KB="$(pi_ssh "df -Pk '$PHASMID_PI_REMOTE_DIR' | awk 'NR==2 {print \\$4}'" 2>/dev/null || true)"
if [[ -z "$REMOTE_FREE_KB" ]]; then
    printf 'WARNING: Could not determine remote free disk space.\n'
else
    printf '[prepare] Remote free space: %s KB\n' "$REMOTE_FREE_KB"
    if [[ "$REMOTE_FREE_KB" -lt 1048576 ]]; then
        printf 'ERROR: Insufficient disk space (< 1GB free) for dependency installation.\n' >&2
        exit 13
    fi
fi

# ── Step 5: Create or reuse .venv and install ─────────────────────────────────

printf '[prepare] Preparing Python virtual environment ...\n'
INSTALL_START="$(date -u +%s)"

pi_ssh "
set -uo pipefail
cd '$PHASMID_PI_REMOTE_DIR'

if [[ ! -d .venv ]]; then
    printf '[prepare] Creating new .venv ...\n'
    python3 -m venv .venv
else
    printf '[prepare] Reusing existing .venv\n'
fi

printf '[prepare] Upgrading pip ...\n'
.venv/bin/python -m pip --version

printf '[prepare] Running: pip install -r requirements.txt ...\n'
.venv/bin/pip install -r requirements.txt 2>&1 | tee '$PHASMID_PI_REMOTE_DIR/_pi_field_test/results/install-remote.log'

printf '[prepare] Running: pip install -e . --no-deps ...\n'
.venv/bin/pip install -e . --no-deps 2>&1 | tee -a '$PHASMID_PI_REMOTE_DIR/_pi_field_test/results/install-remote.log'

printf '[prepare] Installed packages:\n'
.venv/bin/pip list --format=columns 2>&1 | head -30
"

INSTALL_END="$(date -u +%s)"
INSTALL_ELAPSED=$(( INSTALL_END - INSTALL_START ))
printf '[prepare] Install completed in %ds.\n' "$INSTALL_ELAPSED"

printf '[prepare] Checking for likely native source builds of heavy dependencies ...\n'
if pi_ssh "
set -uo pipefail
LOG='$PHASMID_PI_REMOTE_DIR/_pi_field_test/results/install-remote.log'
if [[ -f \"\$LOG\" ]] && grep -E 'Building wheel for (numpy|opencv-python-headless)|Running setup.py' \"\$LOG\" >/dev/null 2>&1; then
    printf 'WARNING: Heavy dependency source-build indicators found in install log.\n'
    printf '         Review wheel availability and Python/OS architecture compatibility.\n'
fi
"; then
    :
fi

# ── Step 6: Verify CLI entry point ────────────────────────────────────────────

printf '[prepare] Verifying phasmid CLI entry point ...\n'
if pi_ssh "
    cd '$PHASMID_PI_REMOTE_DIR'
    .venv/bin/phasmid --help > /dev/null 2>&1
"; then
    printf '[prepare] phasmid CLI entry point: ok\n'
else
    printf 'ERROR: phasmid CLI not found after install.\n' >&2
    printf '       Expected: %s/.venv/bin/phasmid\n' "$PHASMID_PI_REMOTE_DIR" >&2
    printf '       The install may have failed. Check install.log.\n' >&2
    exit 1
fi

# ── Step 7: Write install timing record ──────────────────────────────────────

pi_ssh "
    mkdir -p '$PHASMID_PI_REMOTE_DIR/_pi_field_test/results'
    printf '{\"install_elapsed_s\": %d}\n' $INSTALL_ELAPSED \
        > '$PHASMID_PI_REMOTE_DIR/_pi_field_test/results/install-timing.json'
"

printf '[prepare] Environment ready.\n'
