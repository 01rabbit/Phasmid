#!/usr/bin/env bash
# scripts/pi_zero2w/prepare_remote_env.sh
#
# Synchronize the repository to the Raspberry Pi and prepare the Python
# virtual environment. Called by run_remote_perf.sh; reads the same env vars.
#
# Key constraints:
#   - Uses "pip install -e ." (not requirements.txt) so the phasmid CLI
#     entry point is created.
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

# ── Step 1: Create remote directory ──────────────────────────────────────────

printf '[prepare] Creating remote directory %s ...\n' "$PHASMID_PI_REMOTE_DIR"
pi_ssh "mkdir -p '$PHASMID_PI_REMOTE_DIR'"

# ── Step 2: Sync repository ───────────────────────────────────────────────────
# Excludes: local runtime artifacts, caches, venv, test artifacts.
# --no-delete: never remove files that exist only on the remote side.

printf '[prepare] Syncing repository to %s:%s ...\n' "$PHASMID_PI_HOST" "$PHASMID_PI_REMOTE_DIR"

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

printf '[prepare] Sync complete.\n'

# ── Step 3: Create test output directory ──────────────────────────────────────

pi_ssh "mkdir -p '$PHASMID_PI_REMOTE_DIR/_pi_field_test/results'"

# ── Step 4: Create or reuse .venv and install ─────────────────────────────────
# Uses "pip install -e ." so the "phasmid" CLI entry point is registered.
# "pip install -r requirements.txt" alone does NOT create the entry point.

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
.venv/bin/pip install --upgrade pip --quiet

printf '[prepare] Running: pip install -e . ...\n'
.venv/bin/pip install -e . 2>&1

printf '[prepare] Installed packages:\n'
.venv/bin/pip list --format=columns 2>&1 | head -30
"

INSTALL_END="$(date -u +%s)"
INSTALL_ELAPSED=$(( INSTALL_END - INSTALL_START ))
printf '[prepare] Install completed in %ds.\n' "$INSTALL_ELAPSED"

# ── Step 5: Verify CLI entry point ────────────────────────────────────────────

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

# ── Step 6: Write install timing record ──────────────────────────────────────

pi_ssh "
    mkdir -p '$PHASMID_PI_REMOTE_DIR/_pi_field_test/results'
    printf '{\"install_elapsed_s\": %d}\n' $INSTALL_ELAPSED \
        > '$PHASMID_PI_REMOTE_DIR/_pi_field_test/results/install-timing.json'
"

printf '[prepare] Environment ready.\n'
