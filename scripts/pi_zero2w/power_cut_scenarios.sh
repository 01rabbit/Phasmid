#!/usr/bin/env bash
# scripts/pi_zero2w/power_cut_scenarios.sh
#
# Power-cut scenario orchestrator for Pi Zero 2 W field tests.
# Runs only against a dedicated test vault under _pi_field_test/powercut_lab/.
# It never touches production vault.bin unless you manually point elsewhere.
#
# Usage (run on Pi):
#   bash scripts/pi_zero2w/power_cut_scenarios.sh prepare
#   bash scripts/pi_zero2w/power_cut_scenarios.sh idle
#   bash scripts/pi_zero2w/power_cut_scenarios.sh store
#   bash scripts/pi_zero2w/power_cut_scenarios.sh retrieve
#   bash scripts/pi_zero2w/power_cut_scenarios.sh restricted
#   bash scripts/pi_zero2w/power_cut_scenarios.sh collect

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LAB_DIR="$ROOT_DIR/_pi_field_test/powercut_lab"
RESULTS_DIR="$ROOT_DIR/_pi_field_test/results"
LAB_STATE_DIR="$LAB_DIR/state"
LAB_VAULT="$LAB_DIR/vault.bin"
MARKER_DIR="$LAB_DIR/markers"
VENV_PY="$ROOT_DIR/.venv/bin/python"

mkdir -p "$LAB_DIR" "$RESULTS_DIR" "$MARKER_DIR"

if [[ ! -x "$VENV_PY" ]]; then
  echo "ERROR: $VENV_PY not found. Run remote harness prepare step first." >&2
  exit 1
fi

ts_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

write_marker() {
  local case_name="$1"
  local marker="$MARKER_DIR/${case_name}_start_$(date -u +%Y%m%dT%H%M%SZ).txt"
  {
    echo "case=$case_name"
    echo "start_utc=$(ts_utc)"
    echo "host=$(hostname)"
    echo "kernel=$(uname -r)"
    echo "note=Cut power when GO line appears on console."
  } > "$marker"
  echo "$marker"
}

run_prepare() {
  echo "[prepare] Initializing dedicated power-cut test vault..."
  PHASMID_STATE_DIR="$LAB_STATE_DIR" "$VENV_PY" - <<'PY'
from pathlib import Path
from phasmid.vault_core import PhasmidVault

root = Path("_pi_field_test/powercut_lab")
state = root / "state"
root.mkdir(parents=True, exist_ok=True)
state.mkdir(parents=True, exist_ok=True)
vault_path = root / "vault.bin"

vault = PhasmidVault(str(vault_path), size_mb=256, state_dir=str(state))
vault.format_container(rotate_access_key=True)
seq = ["reference_dummy_matched"]
payload = b"A" * (8 * 1024 * 1024)  # 8 MiB: fits slot while keeping visible progress
vault.store(
    "open-pw-12345678",
    payload,
    seq,
    filename="powercut_payload.bin",
    mode="dummy",
    restricted_recovery_password="purge-pw-12345678",
)
print("prepared_vault", vault_path)
print("prepared_payload_bytes", len(payload))
PY
  echo "[prepare] Done."
}

run_idle() {
  local marker
  marker="$(write_marker "idle")"
  echo "[idle] Marker: $marker"
  echo "[idle] GO: cut power any time in the next 60 seconds."
  for i in $(seq 60 -1 1); do
    echo "[idle] countdown=$i"
    sleep 1
  done
  echo "[idle] Window ended without power cut."
}

run_store() {
  local marker
  marker="$(write_marker "store")"
  echo "[store] Marker: $marker"
  echo "[store] Starting repeated STORE operations on lab vault."
  echo "[store] GO: cut power when you see 'STORE_IN_PROGRESS'."
  PHASMID_STATE_DIR="$LAB_STATE_DIR" "$VENV_PY" - <<'PY'
from phasmid.vault_core import PhasmidVault

vault = PhasmidVault("_pi_field_test/powercut_lab/vault.bin", size_mb=256, state_dir="_pi_field_test/powercut_lab/state")
seq = ["reference_dummy_matched"]
payload = b"B" * (8 * 1024 * 1024)

round_id = 0
while True:
    round_id += 1
    print(f"STORE_ROUND_START round={round_id}", flush=True)
    print(f"STORE_IN_PROGRESS round={round_id} GO", flush=True)
    vault.store(
        "open-pw-12345678",
        payload,
        seq,
        filename=f"powercut_store_round_{round_id}.bin",
        mode="dummy",
        restricted_recovery_password="purge-pw-12345678",
    )
    print(f"STORE_ROUND_DONE round={round_id}", flush=True)
PY
}

run_retrieve() {
  local marker
  marker="$(write_marker "retrieve")"
  echo "[retrieve] Marker: $marker"
  echo "[retrieve] Starting repeated RETRIEVE operations on lab vault."
  echo "[retrieve] GO: cut power when you see 'RETRIEVE_IN_PROGRESS'."
  PHASMID_STATE_DIR="$LAB_STATE_DIR" "$VENV_PY" - <<'PY'
from phasmid.vault_core import PhasmidVault

vault = PhasmidVault("_pi_field_test/powercut_lab/vault.bin", size_mb=256, state_dir="_pi_field_test/powercut_lab/state")
seq = ["reference_dummy_matched"]

round_id = 0
while True:
    round_id += 1
    print(f"RETRIEVE_ROUND_START round={round_id}", flush=True)
    print(f"RETRIEVE_IN_PROGRESS round={round_id} GO", flush=True)
    data, name = vault.retrieve("open-pw-12345678", seq, mode="dummy")
    if data is None:
        print(f"RETRIEVE_ROUND_FAIL round={round_id}", flush=True)
    else:
        print(f"RETRIEVE_ROUND_DONE round={round_id} bytes={len(data)} name={name}", flush=True)
PY
}

run_restricted() {
  local marker
  marker="$(write_marker "restricted")"
  echo "[restricted] Marker: $marker"
  echo "[restricted] Running restricted-like local access-path clear on lab vault."
  echo "[restricted] GO: cut power immediately after 'RESTRICTED_ACTION_DONE GO'."
  PHASMID_STATE_DIR="$LAB_STATE_DIR" "$VENV_PY" - <<'PY'
from phasmid.vault_core import PhasmidVault

vault = PhasmidVault("_pi_field_test/powercut_lab/vault.bin", size_mb=256, state_dir="_pi_field_test/powercut_lab/state")
print("RESTRICTED_ACTION_START", flush=True)
vault.silent_brick()
print("RESTRICTED_ACTION_DONE GO", flush=True)
PY
  # Keep process alive shortly so operator has time to cut after action completion.
  for i in $(seq 20 -1 1); do
    echo "[restricted] post-action window countdown=$i"
    sleep 1
  done
  echo "[restricted] Window ended without power cut."
}

run_collect() {
  local ts
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  local out="$RESULTS_DIR/powercut_collect_${ts}.txt"
  {
    echo "collect_utc=$(ts_utc)"
    echo "hostname=$(hostname)"
    echo "uptime=$(uptime)"
    echo "--- latest markers ---"
    ls -1t "$MARKER_DIR" 2>/dev/null | head -n 8 || true
    echo "--- journal (phasmid.service, last 200) ---"
    journalctl -u phasmid.service -n 200 --no-pager || true
    echo "--- tmp listing ---"
    ls -la /tmp || true
    echo "--- lab dir listing ---"
    ls -la "$LAB_DIR" || true
    echo "--- state dir listing ---"
    ls -la "$LAB_STATE_DIR" || true
  } | tee "$out"
  echo "[collect] Wrote $out"
}

case "${1:-}" in
  prepare) run_prepare ;;
  idle) run_idle ;;
  store) run_store ;;
  retrieve) run_retrieve ;;
  restricted) run_restricted ;;
  collect) run_collect ;;
  *)
    cat <<USAGE
Usage:
  bash scripts/pi_zero2w/power_cut_scenarios.sh prepare
  bash scripts/pi_zero2w/power_cut_scenarios.sh idle
  bash scripts/pi_zero2w/power_cut_scenarios.sh store
  bash scripts/pi_zero2w/power_cut_scenarios.sh retrieve
  bash scripts/pi_zero2w/power_cut_scenarios.sh restricted
  bash scripts/pi_zero2w/power_cut_scenarios.sh collect
USAGE
    exit 1
    ;;
esac
