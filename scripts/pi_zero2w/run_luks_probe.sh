#!/usr/bin/env bash
# scripts/pi_zero2w/run_luks_probe.sh
# LUKS calibration probe for Raspberry Pi field testing (#101).

set -euo pipefail

OUT_DIR="${1:-}"
if [[ -z "$OUT_DIR" ]]; then
  echo "usage: $0 <results-dir>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROFILE_PATH="${PHASMID_LUKS_PROFILE:-$REPO_ROOT/profiles/pi-zero2w.json}"

mkdir -p "$OUT_DIR"
LOG_FILE="$OUT_DIR/luks_field_test.log"
JSON_FILE="$OUT_DIR/luks_field_test.json"

: >"$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[luks] Starting LUKS field test probe"
echo "[luks] Output dir: $OUT_DIR"

echo "[luks] Profile path: $PROFILE_PATH"

sudo_cmd=(sudo)
if [[ "$(id -u)" -eq 0 ]]; then
  sudo_cmd=()
fi

TMP_BASE="/tmp/phasmid-luks-probe"
CONTAINER_FILE="$TMP_BASE/luks-probe.img"
KEY_FILE="$TMP_BASE/luks-probe.key"
MAPPER_NAME="phasmid_luks_probe"
ITER_TIME_MS="${PHASMID_LUKS_ITER_TIME_MS:-2000}"
CALIBRATION_SET="${PHASMID_LUKS_CALIBRATION_SET:-2000,1000,750,500,400,300}"
CIPHER="aes-xts-plain64"
KEY_SIZE="256"
BENCHMARK_OUTPUT_FILE="$TMP_BASE/benchmark.txt"
MEASURE_CSV="$TMP_BASE/measurements.csv"

mkdir -p "$TMP_BASE"
trap 'set +e; "${sudo_cmd[@]}" "$CRYPTSETUP_BIN" luksClose "$MAPPER_NAME" >/dev/null 2>&1 || true; rm -rf "$TMP_BASE"' EXIT

# Prefer explicit binary paths for non-interactive shells.
cryptsetup_available=false
CRYPTSETUP_BIN="cryptsetup"
if command -v cryptsetup >/dev/null 2>&1; then
  CRYPTSETUP_BIN="$(command -v cryptsetup)"
  cryptsetup_available=true
elif [[ -x /usr/sbin/cryptsetup ]]; then
  CRYPTSETUP_BIN="/usr/sbin/cryptsetup"
  cryptsetup_available=true
elif [[ -x /sbin/cryptsetup ]]; then
  CRYPTSETUP_BIN="/sbin/cryptsetup"
  cryptsetup_available=true
fi

# Detect AES capability from multiple sources.
aes_present=false
if grep -qiE '(^|[[:space:]])aes([[:space:]]|$)' /proc/cpuinfo 2>/dev/null; then
  aes_present=true
elif lscpu 2>/dev/null | grep -qiE '(^flags:|^Features:).*\baes\b'; then
  aes_present=true
fi

dm_crypt_loadable=false
if lsmod | grep -q '^dm_crypt'; then
  dm_crypt_loadable=true
elif "${sudo_cmd[@]}" modprobe -n dm_crypt >/dev/null 2>&1; then
  dm_crypt_loadable=true
fi

HOSTNAME_VAL="$(hostname 2>/dev/null || echo unknown)"
ARCH_VAL="$(uname -m 2>/dev/null || echo unknown)"
KERNEL_VAL="$(uname -r 2>/dev/null || echo unknown)"
CPU_MODEL_VAL="$({ cat /proc/device-tree/model 2>/dev/null || lscpu 2>/dev/null | awk -F: '/Model name|Model/ {print $2; exit}'; } | tr -d '\0' | sed 's/^ *//;s/ *$//' )"
if [[ -z "$CPU_MODEL_VAL" ]]; then
  CPU_MODEL_VAL="unknown"
fi

cat <<INFO
[luks] aes instruction present: $aes_present
[luks] dm_crypt loadable: $dm_crypt_loadable
[luks] cryptsetup available: $cryptsetup_available
[luks] cryptsetup binary: $CRYPTSETUP_BIN
[luks] requested iter-time: ${ITER_TIME_MS} ms
[luks] calibration set: $CALIBRATION_SET
[luks] hostname: $HOSTNAME_VAL
[luks] arch: $ARCH_VAL
[luks] kernel: $KERNEL_VAL
[luks] cpu model: $CPU_MODEL_VAL
INFO

if [[ "$cryptsetup_available" != "true" ]]; then
  python3 "$SCRIPT_DIR/luks_eval.py" \
    --measurements-csv /dev/null \
    --benchmark-output /dev/null \
    --profile "$PROFILE_PATH" \
    --output "$JSON_FILE" \
    --requested-iter "$ITER_TIME_MS" \
    --cipher "$CIPHER" \
    --key-size "$KEY_SIZE" \
    --cpu-model "$CPU_MODEL_VAL" \
    --kernel "$KERNEL_VAL" \
    --arch "$ARCH_VAL" \
    --hostname "$HOSTNAME_VAL" \
    --aes-instruction-present "${aes_present}" \
    --dm-crypt-loadable "${dm_crypt_loadable}" \
    --cryptsetup-available false \
    --benchmark-ok false
  exit 1
fi

benchmark_ok=false
if "$CRYPTSETUP_BIN" benchmark --cipher "$CIPHER" --key-size "$KEY_SIZE" >"$BENCHMARK_OUTPUT_FILE" 2>&1; then
  benchmark_ok=true
fi

echo "[luks] cryptsetup benchmark ok: $benchmark_ok"
cat "$BENCHMARK_OUTPUT_FILE"

touch "$MEASURE_CSV"

ms_now() {
  python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
}

measure_once() {
  local iter="$1"

  truncate -s 128M "$CONTAINER_FILE"
  dd if=/dev/urandom of="$KEY_FILE" bs=32 count=1 status=none
  chmod 600 "$KEY_FILE"

  "${sudo_cmd[@]}" "$CRYPTSETUP_BIN" luksClose "$MAPPER_NAME" >/dev/null 2>&1 || true

  local format_start format_end open_start open_end
  local format_ms open_ms
  local format_ok open_ok

  format_ok=false
  open_ok=false

  format_start="$(ms_now)"
  if "${sudo_cmd[@]}" "$CRYPTSETUP_BIN" luksFormat \
    --type luks2 \
    --cipher "$CIPHER" \
    --key-size "$KEY_SIZE" \
    --iter-time "$iter" \
    --batch-mode \
    --key-file "$KEY_FILE" \
    "$CONTAINER_FILE"; then
    format_ok=true
  fi
  format_end="$(ms_now)"
  format_ms=$((format_end - format_start))

  open_start="$(ms_now)"
  if [[ "$format_ok" == "true" ]] && "${sudo_cmd[@]}" "$CRYPTSETUP_BIN" luksOpen \
    --key-file "$KEY_FILE" \
    "$CONTAINER_FILE" \
    "$MAPPER_NAME"; then
    open_ok=true
  fi
  open_end="$(ms_now)"
  open_ms=$((open_end - open_start))

  if [[ "$open_ok" == "true" ]]; then
    "${sudo_cmd[@]}" "$CRYPTSETUP_BIN" luksClose "$MAPPER_NAME" >/dev/null 2>&1 || true
  fi

  echo "$iter,$format_ms,$open_ms,$format_ok,$open_ok" >> "$MEASURE_CSV"
  echo "[luks] iter=$iter format_ms=$format_ms open_ms=$open_ms format_ok=$format_ok open_ok=$open_ok"
}

# Ensure requested iter-time is first, then append additional unique candidates.
candidates="$ITER_TIME_MS"
IFS=',' read -r -a raw_candidates <<< "$CALIBRATION_SET"
for c in "${raw_candidates[@]}"; do
  c_trimmed="$(echo "$c" | tr -d '[:space:]')"
  [[ -z "$c_trimmed" ]] && continue
  if [[ ! "$c_trimmed" =~ ^[0-9]+$ ]]; then
    continue
  fi
  if [[ ",$candidates," != *",$c_trimmed,"* ]]; then
    candidates+=";$c_trimmed"
  fi
done

IFS=';' read -r -a iter_candidates <<< "$candidates"
for iter in "${iter_candidates[@]}"; do
  measure_once "$iter"
done

python3 "$SCRIPT_DIR/luks_eval.py" \
  --measurements-csv "$MEASURE_CSV" \
  --benchmark-output "$BENCHMARK_OUTPUT_FILE" \
  --profile "$PROFILE_PATH" \
  --output "$JSON_FILE" \
  --requested-iter "$ITER_TIME_MS" \
  --cipher "$CIPHER" \
  --key-size "$KEY_SIZE" \
  --cpu-model "$CPU_MODEL_VAL" \
  --kernel "$KERNEL_VAL" \
  --arch "$ARCH_VAL" \
  --hostname "$HOSTNAME_VAL" \
  --aes-instruction-present "${aes_present}" \
  --dm-crypt-loadable "${dm_crypt_loadable}" \
  --cryptsetup-available true \
  --benchmark-ok "${benchmark_ok}"

echo "[luks] Wrote $JSON_FILE"
echo "[luks] Wrote $LOG_FILE"
