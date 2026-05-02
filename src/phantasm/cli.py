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
from .face_lock import face_lock
from .gv_core import GhostVault
from .operations import doctor, export_redacted_log, verify_audit_log, verify_state

CAMERA_WARMUP_TIMEOUT = 10
REFERENCE_MATCH_TIMEOUT = 10
FACE_RESET_CONFIRMATION = "RESET FACE LOCK AND VAULT"
MODE_LABELS = {
    gate.MODES[0]: "selected local entry",
    gate.MODES[1]: "selected local entry",
}
ENTRY_SELECTOR_TO_MODE = {
    "a": gate.MODES[0],
    "b": gate.MODES[1],
    "prof" + "ile_a": gate.MODES[0],
    "prof" + "ile_b": gate.MODES[1],
}


def display_mode_label(mode):
    return MODE_LABELS.get(mode, "local entry")


def resolve_mode(entry_value):
    if entry_value not in ENTRY_SELECTOR_TO_MODE:
        raise ValueError(f"unsupported entry selector: {entry_value}")
    return ENTRY_SELECTOR_TO_MODE[entry_value]


def show_loading(message, duration=2):
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
    print(
        f"[INFO] Position the bound object for {display_mode_label(mode)}, "
        "then press Enter to capture."
    )
    input()

    success, msg = gate.capture_reference(mode)
    if not success:
        return False, msg

    print(f"[LOCAL] {display_mode_label(mode)} object cue captured. Validating match quality...")
    if not _wait_for_reference_match(expected_mode=mode):
        return (
            False,
            f"Object cue captured, but no stable match was detected for {display_mode_label(mode)}.",
        )

    return True, "Object access cue registered."


def _collect_auth_sequence():
    print("[INFO] Show the bound object to the camera, then press Enter to continue.")
    input()

    if _wait_for_reference_match():
        print("[LOCAL] Bound object matched.")
    elif gate.last_match_mode == gate.MATCH_AMBIGUOUS:
        print("[LOCAL] Ambiguous object match detected.")
    else:
        print("[LOCAL] No bound object match detected within timeout.")

    return get_gesture_sequence(length=1)


def _confirm_purge_other_mode(accessed_mode):
    if not purge_confirmation_required():
        return True

    print("\n[SAFETY] Local state is preserved by default.")

    confirmation = "CLEAR UNMATCHED LOCAL ENTRY"
    answer = input(
        f'[LOCAL STATE] Clear unmatched local entry after access? '
        f'Type "{confirmation}" to confirm: '
    ).strip()
    return answer == confirmation


def _auto_purge_reason(accessed_mode):
    if duress_mode_enabled() and accessed_mode == gate.MODES[0]:
        return "duress_access"
    if not purge_confirmation_required():
        return "confirmation_disabled"
    return None


def _prompt_store_passwords():
    open_password = getpass.getpass("[AUTH] Enter access password: ")
    restricted_recovery_password = getpass.getpass("[AUTH] Enter restricted recovery password: ")
    if not open_password:
        raise ValueError("access password must not be empty")
    if not restricted_recovery_password:
        raise ValueError("restricted recovery password must not be empty")
    if open_password == restricted_recovery_password:
        raise ValueError("access and restricted recovery passwords must be different")
    return open_password, restricted_recovery_password


def _confirm_face_lock_reset(input_func=input):
    print("\n[!] CAUTION: FACE UI LOCK RESET")
    print("[!] This clears the enrolled face lock and initializes all stored vault data.")
    print("[!] Physical object bindings are also cleared.")
    answer = input_func(f'Type "{FACE_RESET_CONFIRMATION}" to continue: ').strip()
    return answer == FACE_RESET_CONFIRMATION


def _reset_face_lock_and_container(vault):
    vault.format_container(rotate_access_key=True)
    object_success, object_message = gate.clear_references()
    face_success, face_message = face_lock.reset()
    enroll_success, enroll_message = (
        face_lock.arm_enrollment()
        if face_success
        else (False, "Face enrollment was not armed.")
    )
    audit_event("container_reinitialized", source="cli_face_reset")
    audit_event("object_bindings_cleared", source="cli_face_reset", success=object_success)
    audit_event("ui_face_lock_cleared", source="cli_face_reset", success=face_success)
    audit_event("ui_face_enrollment_armed", source="cli_face_reset", success=enroll_success)
    return (
        object_success and face_success and enroll_success,
        object_message,
        face_message,
        enroll_message,
    )


def _print_operation_report(report):
    print(f"{report['name']}: {report['status']}")
    for check in report["checks"]:
        print(f"- {check['name']}: {check['status']} - {check['message']}")


def main():
    parser = argparse.ArgumentParser(description="Phantasm - Local Protected Storage")
    parser.add_argument(
        "action",
        choices=[
            "init",
            "store",
            "retrieve",
            "brick",
            "reset-face-lock",
            "verify-state",
            "verify-audit-log",
            "doctor",
            "export-redacted-log",
        ],
        help="operation to run",
    )
    parser.add_argument(
        "--entry",
        choices=["a", "b"],
        default="a",
        help="entry selector to use",
    )
    parser.add_argument(
        "--" + "prof" + "ile",
        choices=["a", "b"],
        dest="legacy_entry",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--mode",
        dest="legacy_entry_mode",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--file", help="path to the input file")
    parser.add_argument("--out", help="path where decrypted output will be written")
    args = parser.parse_args()

    if args.action == "verify-state":
        _print_operation_report(verify_state())
        return
    if args.action == "verify-audit-log":
        _print_operation_report(verify_audit_log())
        return
    if args.action == "doctor":
        _print_operation_report(doctor())
        return
    if args.action == "export-redacted-log":
        if not args.out:
            print("[!] Error: Output path required.")
            return
        _print_operation_report(export_redacted_log(args.out))
        return

    selected_value = args.legacy_entry if args.legacy_entry else args.entry
    selected_mode = resolve_mode(selected_value)
    if args.legacy_entry_mode in gate.MODES:
        selected_mode = args.legacy_entry_mode

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
            print("\n[!] CAUTION: INITIALIZING LOCAL CONTAINER")
            show_loading("Initializing local container with random data", 3)
            vault.format_container(rotate_access_key=True)
            audit_event("container_reinitialized")
            print("[+] Local container initialized. Ready for protected entries.")

        elif args.action == "store":
            if not args.file:
                print("[!] Error: No input file specified.")
                return

            entry_label = display_mode_label(selected_mode)
            print(f"\n--- PHANTASM STORE [{entry_label}] ---")
            try:
                pw, purge_pw = _prompt_store_passwords()
            except ValueError as exc:
                print(f"[!] Error: {exc}")
                return

            print(f"\n[LOCAL] Calibrating object cue for {entry_label}...")
            print("[INFO] The captured object will be stored as the local access cue for this entry.")
            success, msg = _register_reference_key(selected_mode)
            if not success:
                print(f"[!] Error: {msg}")
                return
            gesture_seq = gate.sequence_for_mode(selected_mode)

            with open(args.file, "rb") as f:
                data = f.read()

            show_loading("Preparing cryptographic recovery", 2)
            show_loading("Encrypting payload with AES-256-GCM", 1.5)

            vault.store(
                pw,
                data,
                gesture_seq,
                filename=os.path.basename(args.file),
                mode=selected_mode,
                restricted_recovery_password=purge_pw,
            )
            audit_event(
                "payload_stored",
                entry="local_entry",
                filename=os.path.basename(args.file),
                bytes=len(data),
            )
            print("\n[SUCCESS] Protected entry saved.")
            print("[LOCAL] Bound object cue registered.")

        elif args.action == "retrieve":
            ui.show_diagnostic()
            print("\n" + "=" * 55)
            print(" PHANTASM - LOCAL RETRIEVAL")
            print(" DEVICE STATUS: READY")
            print("=" * 55)

            pw = getpass.getpass("\n[AUTH] Access password: ")

            print("\n[LOCAL] Requesting bound object verification...")
            user_gesture_seq = _collect_auth_sequence()

            if gate.last_match_mode == gate.MATCH_AMBIGUOUS:
                ui.show_alert("ACCESS ERROR\nAMBIGUOUS OBJECT")
                print("[!] Access rejected because the object match is ambiguous.")
                return
            if not user_gesture_seq or user_gesture_seq[0] == gate.MATCH_NONE:
                ui.show_alert("ACCESS ERROR\nOBJECT NOT FOUND")
                print("[!] No bound object matched.")
                return

            show_loading("Verifying protected entry", 3)

            result, filename, password_role = vault.retrieve_with_policy(
                pw,
                user_gesture_seq,
                mode=gate.MODES[0],
            )
            accessed_mode = gate.MODES[0]

            if result is None:
                result, filename, password_role = vault.retrieve_with_policy(
                    pw,
                    user_gesture_seq,
                    mode=gate.MODES[1],
                )
                accessed_mode = gate.MODES[1]

            if result is not None:
                ui.show_alert("ACCESS GRANTED")

                show_loading("Preparing recovered payload", 2)
                print(f"\n[ACCESS GRANTED] Decrypted {len(result)} bytes.")

                if args.out:
                    with open(args.out, "wb") as f:
                        f.write(result)
                    print(f"[+] Output written to: {args.out}")
                else:
                    try:
                        content = result.decode("utf-8")
                        print("-" * 40)
                        print(content[:500] + ("..." if len(content) > 500 else ""))
                        print("-" * 40)
                    except UnicodeDecodeError:
                        print("[INFO] Binary payload detected.")

                audit_event(
                    "payload_retrieved",
                    entry="local_entry",
                    filename=filename,
                    bytes=len(result),
                )
                if password_role == GhostVault.PURGE_ROLE:
                    vault.purge_other_mode(accessed_mode)
                    audit_event(
                        "restricted_local_update",
                        accessed_entry="local_entry",
                        reason="restricted_recovery",
                    )
                    print("\n(SYSTEM: Operation completed.)")
                    return

                auto_purge_reason = _auto_purge_reason(accessed_mode)
                if auto_purge_reason:
                    vault.purge_other_mode(accessed_mode)
                    audit_event(
                        "restricted_local_update",
                        accessed_entry="local_entry",
                        reason=auto_purge_reason,
                    )
                    if auto_purge_reason == "confirmation_disabled":
                        print("\n(SYSTEM: Operation completed.)")
                    else:
                        print("\n(SYSTEM: Operation completed.)")
                elif _confirm_purge_other_mode(accessed_mode):
                    vault.purge_other_mode(accessed_mode)
                    audit_event("restricted_local_update", accessed_entry="local_entry")
                    print("\n(SYSTEM: Operation completed.)")
                else:
                    print("\n(SYSTEM: Operation completed.)")
            else:
                ui.show_alert("ACCESS DENIED\nINVALID CREDENTIALS")
                audit_event("retrieve_failed")
                print("\n[!] Access failed.")

        elif args.action == "brick":
            vault.silent_brick()
            audit_event("access_path_cleared", source="cli")
            print("[!] Local access path cleared.")

        elif args.action == "reset-face-lock":
            if not _confirm_face_lock_reset():
                print("[ABORTED] Face UI lock reset cancelled.")
                return
            success, object_message, face_message, enroll_message = (
                _reset_face_lock_and_container(vault)
            )
            print("[+] Container initialized: vault.bin is empty.")
            print(f"[+] Object bindings: {object_message}")
            print(f"[+] Face UI lock: {face_message}")
            print(f"[+] Face enrollment: {enroll_message}")
            if success:
                print("[+] Reset complete. Reload /ui-lock in the WebUI to register a new face lock.")
            else:
                print("[!] Reset completed with warnings. Review the messages above.")
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
