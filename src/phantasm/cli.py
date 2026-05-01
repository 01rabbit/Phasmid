import argparse
import getpass
import os
import sys
import time

from .ai_gate import get_gesture_sequence, gate
from .audit import audit_event
from .bridge_ui import ui
from .config import duress_mode_enabled, purge_confirmation_required
from .emergency_daemon import EmergencyDaemon
from .gv_core import GhostVault

CAMERA_WARMUP_TIMEOUT = 10
REFERENCE_MATCH_TIMEOUT = 10
MODE_LABELS = {
    "dummy": "Profile A",
    "secret": "Profile B",
}
PROFILE_TO_MODE = {
    "a": "dummy",
    "b": "secret",
    "profile_a": "dummy",
    "profile_b": "secret",
}


def display_mode_label(mode):
    return MODE_LABELS.get(mode, "Profile")


def resolve_mode(profile_value):
    if profile_value not in PROFILE_TO_MODE:
        raise ValueError(f"unsupported profile: {profile_value}")
    return PROFILE_TO_MODE[profile_value]

def fake_loading(message, duration=2):
    chars = ["/", "-", "\\", "|"]
    start_time = time.time()
    i = 0
    while time.time() - start_time < duration:
        sys.stdout.write(f"\r[*] {message}... {chars[i % len(chars)]}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write(f"\r[+] {message}... DONE\n")


def _wait_for_camera_frame(timeout=CAMERA_WARMUP_TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with gate.lock:
            if gate.latest_frame is not None:
                return True
        time.sleep(0.1)
    return False


def _wait_for_reference_match(timeout=REFERENCE_MATCH_TIMEOUT, expected_mode=None):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if expected_mode is not None and gate.last_match_mode == expected_mode:
            return True
        if expected_mode is None and gate.last_match_mode in gate.AUTH_TOKENS:
            return True
        time.sleep(0.1)
    return False


def _register_reference_key(mode):
    print(f"[INFO] Position the object for {display_mode_label(mode)}, then press Enter to capture.")
    input()

    success, msg = gate.capture_reference(mode)
    if not success:
        return False, msg

    print(f"[AI GATE] {display_mode_label(mode)} reference captured. Validating image key...")
    if not _wait_for_reference_match(expected_mode=mode):
        return False, f"Reference captured, but no stable match was detected for {display_mode_label(mode)}."

    return True, "Reference key registered."


def _collect_auth_sequence():
    print("[INFO] Show the registered physical key to the camera, then press Enter to continue.")
    input()

    if _wait_for_reference_match():
        print(f"[AI GATE] Physical key matched for {display_mode_label(gate.last_match_mode)}.")
    elif gate.last_match_mode == gate.MATCH_AMBIGUOUS:
        print("[AI GATE] Ambiguous match detected. The registered image keys are too similar.")
    else:
        print("[AI GATE] No reference match detected within timeout.")

    return get_gesture_sequence(length=1)


def _confirm_purge_other_mode(accessed_mode):
    if not purge_confirmation_required():
        return True

    other_mode = "secret" if accessed_mode == "dummy" else "dummy"
    other_label = display_mode_label(other_mode)
    accessed_label = display_mode_label(accessed_mode)
    print(f"\n[SAFETY] {other_label} remains intact by default.")
    if accessed_mode == "secret":
        print("[SAFETY] Profile A may be needed as a decoy profile. Do not purge it unless you intend to.")

    confirmation = f"DELETE {other_label.upper()}"
    answer = input(
        f'[PURGE] Delete alternate profile ({other_label}) after accessing {accessed_label}? '
        f'Type "{confirmation}" to confirm: '
    ).strip()
    return answer == confirmation


def _auto_purge_reason(accessed_mode):
    if duress_mode_enabled() and accessed_mode == "dummy":
        return "duress_dummy_access"
    if not purge_confirmation_required():
        return "confirmation_disabled"
    return None

def main():
    parser = argparse.ArgumentParser(description="GhostVault Phantasm - Tactical Secure Storage v3")
    parser.add_argument("action", choices=["init", "store", "retrieve", "brick"], help="operation to run")
    parser.add_argument(
        "--profile",
        choices=["a", "b"],
        default="a",
        help="profile to use",
    )
    parser.add_argument(
        "--mode",
        choices=["dummy", "secret"],
        dest="legacy_mode",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--file", help="path to the input file")
    parser.add_argument("--out", help="path where decrypted output will be written")
    args = parser.parse_args()
    selected_mode = args.legacy_mode if args.legacy_mode else resolve_mode(args.profile)

    panic_monitor = EmergencyDaemon("vault.bin")
    gate_started = False

    try:
        panic_monitor.start()

        if args.action in {"store", "retrieve"}:
            gate.start()
            gate_started = True
            if not _wait_for_camera_frame():
                print("[!] Error: Camera feed did not become available.")
                return

        vault = GhostVault("vault.bin")

        if args.action == "init":
            print("\n[!] CAUTION: INITIALIZING SECURE CONTAINER")
            fake_loading("Wiping storage sectors with random entropy", 3)
            vault.format_container()
            audit_event("container_initialized")
            print("[+] GhostVault initialized. Ready for encrypted payload.")

        elif args.action == "store":
            if not args.file:
                print("[!] Error: No input file specified.")
                return

            profile_label = display_mode_label(selected_mode)
            print(f"\n--- GHOST VAULT SECURE UPLOAD [{profile_label}] ---")
            pw = getpass.getpass("[AUTH] Enter Vault Access Key: ")
            
            print(f"\n[AI GATE] Calibrating image key for {profile_label}...")
            print("[INFO] The captured object will be stored as a dedicated reference image for this profile.")
            success, msg = _register_reference_key(selected_mode)
            if not success:
                print(f"[!] Error: {msg}")
                return
            gesture_seq = gate.sequence_for_mode(selected_mode)

            with open(args.file, "rb") as f:
                data = f.read()

            fake_loading("Performing Argon2id-based key derivation", 2)
            fake_loading(f"Encrypting payload with AES-256-GCM", 1.5)
            
            vault.store(
                pw,
                data,
                gesture_seq,
                filename=os.path.basename(args.file),
                mode=selected_mode,
            )
            audit_event("payload_stored", profile=profile_label, filename=os.path.basename(args.file), bytes=len(data))
            print(f"\n[SUCCESS] Payload successfully committed to vault.")
            print(f"[MEMORIZE] Registered token for {profile_label}: {' -> '.join(gesture_seq)}")

        elif args.action == "retrieve":
            ui.show_diagnostic()
            print("\n" + "="*55)
            print(" GHOST VAULT - TACTICAL RETRIEVAL INTERFACE")
            print(" SYSTEM STATUS: ARMED / READY")
            print("="*55)
            
            pw = getpass.getpass("\n[AUTH] Master Key Required: ")
            
            print("\n[AI GATE] Requesting Biometric Verification...")
            user_gesture_seq = _collect_auth_sequence()
            
            if gate.last_match_mode == gate.MATCH_AMBIGUOUS:
                ui.show_alert("AUTH ERROR\nAMBIGUOUS KEY")
                print("[!] Authentication aborted because both registered image keys match the presented object.")
                return
            if not user_gesture_seq or user_gesture_seq[0] == gate.MATCH_NONE:
                ui.show_alert("AUTH ERROR\nKEY NOT FOUND")
                print("[!] No registered image key matched the presented object.")
                return

            fake_loading("Verifying cryptographic integrity", 3)
            
            result, filename = vault.retrieve(pw, user_gesture_seq, mode="dummy")
            accessed_mode = "dummy"

            if result is None:
                result, filename = vault.retrieve(pw, user_gesture_seq, mode="secret")
                accessed_mode = "secret"

            if result is not None:
                ui.show_alert(f"ACCESS GRANTED\n{display_mode_label(accessed_mode)}")
                
                fake_loading("Reconstructing secure data streams", 2)
                print(f"\n[ACCESS GRANTED] Decrypted {len(result)} bytes.")
                
                if args.out:
                    with open(args.out, "wb") as f:
                        f.write(result)
                    print(f"[+] Output written to: {args.out}")
                else:
                    try:
                        content = result.decode("utf-8")
                        print("-" * 40)
                        if filename:
                            print(f"filename: {filename}")
                        print(content[:500] + ("..." if len(content) > 500 else ""))
                        print("-" * 40)
                    except UnicodeDecodeError:
                        print("[INFO] Binary payload detected.")

                audit_event("payload_retrieved", profile=display_mode_label(accessed_mode), filename=filename, bytes=len(result))
                auto_purge_reason = _auto_purge_reason(accessed_mode)
                if auto_purge_reason:
                    vault.purge_other_mode(accessed_mode)
                    audit_event(
                        "alternate_profile_purged",
                        accessed_profile=display_mode_label(accessed_mode),
                        reason=auto_purge_reason,
                    )
                    if auto_purge_reason == "confirmation_disabled":
                        print("\n(SYSTEM: Alternate profile disabled by configuration.)")
                    else:
                        print("\n(SYSTEM: Alternate profile state updated.)")
                elif _confirm_purge_other_mode(accessed_mode):
                    vault.purge_other_mode(accessed_mode)
                    audit_event("alternate_profile_purged", accessed_profile=display_mode_label(accessed_mode))
                    print("\n(SYSTEM: Alternate profile disabled after explicit confirmation.)")
                else:
                    print("\n(SYSTEM: Alternate profile preserved.)")
            else:
                ui.show_alert("ACCESS DENIED\nINVALID CREDENTIALS")
                audit_event("retrieve_failed")
                print("\n[FATAL] Authentication failed. Access denied.")

        elif args.action == "brick":
            vault.silent_brick()
            audit_event("container_bricked", source="cli")
            print("[!] Brick sequence completed.")
    finally:
        panic_monitor.stop()
        if gate_started:
            gate.close()
        try:
            ui.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
