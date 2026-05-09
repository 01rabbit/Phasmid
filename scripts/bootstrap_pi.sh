#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ALLOW_NON_PI="${PHASMID_ALLOW_NON_PI:-0}"
RECREATE_VENV="${PHASMID_RECREATE_VENV:-0}"

log() {
  printf '[bootstrap] %s\n' "$*"
}

warn() {
  printf '[bootstrap][warn] %s\n' "$*" >&2
}

is_raspberry_pi() {
  if [[ -r /proc/device-tree/model ]] && grep -qi 'raspberry pi' /proc/device-tree/model 2>/dev/null; then
    return 0
  fi
  if [[ -r /sys/firmware/devicetree/base/model ]] && grep -qi 'raspberry pi' /sys/firmware/devicetree/base/model 2>/dev/null; then
    return 0
  fi
  return 1
}

apt_install() {
  local -a packages=(
    python3-picamera2
    python3-libcamera
    libcamera-apps
    ffmpeg
    v4l-utils
    python3-venv
    python3-dev
    build-essential
    pkg-config
    libatlas-base-dev
  )

  local -a sudo_prefix=()
  if [[ "$(id -u)" -ne 0 ]]; then
    sudo_prefix=(sudo)
  fi

  log "Installing apt dependencies..."
  "${sudo_prefix[@]}" apt-get update
  "${sudo_prefix[@]}" apt-get install -y "${packages[@]}"
}

prepare_venv() {
  cd "$REPO_ROOT"

  if [[ -d .venv ]] && [[ "$RECREATE_VENV" == "1" ]]; then
    log "Removing existing .venv because PHASMID_RECREATE_VENV=1"
    rm -rf .venv
  fi

  if [[ ! -d .venv ]]; then
    log "Creating .venv with --system-site-packages"
    # Picamera2 is provided by Raspberry Pi OS apt packages and is not reliably
    # distributed via pip for this hardware stack. We keep system packages visible
    # in the virtualenv so python3-picamera2/python3-libcamera stay importable.
    python3 -m venv --system-site-packages .venv
  else
    log "Reusing existing .venv"
  fi

  # shellcheck disable=SC1091
  source .venv/bin/activate

  log "Upgrading pip"
  python -m pip install --upgrade pip

  log "Installing Phasmid in editable mode"
  python -m pip install -e .
}

main() {
  log "Starting Raspberry Pi bootstrap"

  if ! is_raspberry_pi; then
    warn "Raspberry Pi environment was not detected."
    if [[ "$ALLOW_NON_PI" != "1" ]]; then
      warn "Continuing in safe mode. Set PHASMID_ALLOW_NON_PI=1 to acknowledge explicitly."
    fi
  fi

  apt_install
  prepare_venv

  log "Bootstrap complete"
  log "Next: source .venv/bin/activate && ./scripts/validate_pi_environment.sh"
}

main "$@"
