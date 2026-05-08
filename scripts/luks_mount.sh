#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"
CONTAINER="${2:-/opt/phasmid/luks.img}"
MOUNT_POINT="${3:-/mnt/phasmid-vault}"
MAPPER_NAME="phasmid-vault"
KEY_FILE="/run/phasmid/luks.key"

case "$ACTION" in
    mount)
        cryptsetup luksOpen --key-file "$KEY_FILE" "$CONTAINER" "$MAPPER_NAME"
        mount "/dev/mapper/$MAPPER_NAME" "$MOUNT_POINT"
        ;;
    unmount)
        umount "$MOUNT_POINT" || true
        cryptsetup luksClose "$MAPPER_NAME" || true
        ;;
    status)
        cryptsetup status "$MAPPER_NAME" 2>/dev/null | head -5 || true
        ;;
    brick)
        # best-effort — complete erasure is not guaranteed
        shred -n 3 "$KEY_FILE" 2>/dev/null || true
        rm -f "$KEY_FILE"
        cryptsetup luksErase "$CONTAINER" --batch-mode || true
        ;;
    *)
        echo "usage: $0 {mount|unmount|status|brick} [container_path] [mount_point]" >&2
        exit 2
        ;;
esac
