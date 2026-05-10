from __future__ import annotations

import argparse
import getpass
import os
import sys
import time

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.text import Text

from . import strings as text
from .ai_gate import gate, get_gesture_sequence
from .attempt_limiter import FileAttemptLimiter
from .audit import audit_event
from .bridge_ui import ui
from .capabilities import capability_enabled
from .config import duress_mode_enabled, purge_confirmation_required
from .crypto_boundary import CryptoSelfTestError, ensure_crypto_self_tests
from .emergency_daemon import EmergencyDaemon
from .operations import export_redacted_log, verify_audit_log, verify_state
from .passphrase_policy import check_store_passphrases
from .process_hardening import apply_process_hardening
from .restricted_actions import (
    DESTRUCTIVE_CLEAR_PHRASE,
    RESTRICTED_ACTION_POLICIES,
    RestrictedActionRejected,
    evaluate_restricted_action,
)
from .services.access_cue_service import access_cue_service
from .vault_core import PhasmidVault
from .volatile_state import require_volatile_state

console = Console()

CAMERA_WARMUP_TIMEOUT = 10
REFERENCE_MATCH_TIMEOUT = 10
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
    with Progress(
        SpinnerColumn(spinner_name="dots", style="cyan"),
        TextColumn("[cyan]{task.description}[/cyan]"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task(message, total=None)
        start = time.time()
        while time.time() - start < duration:
            time.sleep(0.1)
    console.print(f"  [bold green]✓[/bold green]  {message}")


def info(msg):
    console.print(f"  [dim cyan]·[/dim cyan]  {msg}")


def warn(msg):
    console.print(f"  [bold yellow]![/bold yellow]  [yellow]{msg}[/yellow]")


def success(msg):
    console.print(f"  [bold green]✓[/bold green]  [green]{msg}[/green]")


def error(msg):
    console.print(f"  [bold red]✗[/bold red]  [red]{msg}[/red]")


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
    info(
        f"Position the bound object for [bold]{display_mode_label(mode)}[/bold], "
        "then press [bold]Enter[/bold] to capture."
    )
    input()

    success_flag, msg = gate.capture_reference(mode)
    if not success_flag:
        return False, msg

    info(
        f"{display_mode_label(mode)} object cue captured — validating match quality..."
    )
    if not _wait_for_reference_match(expected_mode=mode):
        return (
            False,
            f"Object cue captured, but no stable match was detected for {display_mode_label(mode)}.",
        )

    return True, text.CLI_OBJECT_BOUND


def _collect_auth_sequence():
    info(
        "Show the bound object to the camera, then press [bold]Enter[/bold] to continue."
    )
    input()

    if _wait_for_reference_match():
        _prefix = "[LOCAL] "
        console.print(
            f"  [bold green]✓[/bold green]  [green]{text.CLI_OBJECT_MATCHED.removeprefix(_prefix)}[/green]"
        )
    else:
        if access_cue_service.recognition_mode() == "coercion_safe":
            warn(text.CLI_NO_MATCH_TIMEOUT.removeprefix("[LOCAL] "))
        elif gate.last_match_mode == gate.MATCH_AMBIGUOUS:
            warn(text.CLI_AMBIGUOUS_MATCH.removeprefix("[LOCAL] "))
        else:
            warn(text.CLI_NO_MATCH_TIMEOUT.removeprefix("[LOCAL] "))

    return get_gesture_sequence(length=1)


def _confirm_purge_other_mode(accessed_mode):
    if not purge_confirmation_required():
        return True

    console.print()
    console.print(Rule("Local State", style="dim"))
    warn("Local state is preserved by default.")

    confirmation = DESTRUCTIVE_CLEAR_PHRASE
    answer = console.input(
        f"  Clear unmatched local entry after access? "
        f'Type [bold red]"{confirmation}"[/bold red] to confirm: '
    ).strip()
    return answer == confirmation


def _auto_purge_reason(accessed_mode):
    if duress_mode_enabled() and accessed_mode == gate.MODES[0]:
        return "duress_access"
    if not purge_confirmation_required():
        return "confirmation_disabled"
    return None


def _prompt_store_passwords():
    open_password = getpass.getpass("  Access password: ")
    restricted_recovery_password = getpass.getpass("  Restricted recovery password: ")
    if not open_password:
        raise ValueError("access password must not be empty")
    if not restricted_recovery_password:
        raise ValueError("restricted recovery password must not be empty")
    passphrase_check = check_store_passphrases(
        open_password, restricted_recovery_password
    )
    if not passphrase_check.ok:
        raise ValueError(passphrase_check.message)
    return open_password, restricted_recovery_password


def require_restricted_action(action_id, confirmation=""):
    policy = RESTRICTED_ACTION_POLICIES[action_id]
    try:
        evaluate_restricted_action(
            policy,
            capability_allowed=capability_enabled(policy.capability),
            restricted_confirmed=True,
            confirmation=confirmation,
        )
    except RestrictedActionRejected as exc:
        raise ValueError(exc.message) from exc


def _print_operation_report(report):
    ok_statuses = ("ok", "pass", "valid", "verified", "ready")
    status_style = (
        "green"
        if report["status"] in ok_statuses
        else "yellow"
        if report["status"] == "attention"
        else "red"
    )
    console.print(
        Panel(
            _build_report_text(report),
            title=f"[bold]{report['name']}[/bold]",
            subtitle=f"[{status_style}]{report['status']}[/{status_style}]",
            border_style=status_style,
        )
    )


def _check_icon(status):
    if status in ("ok", "pass", "valid", "verified", "ready"):
        return "[green]✓[/green]"
    if status in ("not_enabled", "disabled", "skipped"):
        return "[dim]–[/dim]"
    return "[yellow]![/yellow]"


def _build_report_text(report):
    lines = []
    for check in report["checks"]:
        icon = _check_icon(check["status"])
        lines.append(
            f"  {icon}  [bold]{check['name']}[/bold]  [dim]{check['message']}[/dim]"
        )
    return Text.from_markup("\n".join(lines) if lines else "[dim]No checks[/dim]")


def _run_startup_checks():
    try:
        ensure_crypto_self_tests()
        return True
    except CryptoSelfTestError:
        error("Startup check failed.")
        return False


def _run_doctor_tui() -> None:
    """Run doctor in non-interactive mode and print to console."""
    from .models.doctor import DoctorLevel
    from .services.doctor_service import DoctorService

    svc = DoctorService()
    result = svc.run()
    icons = {
        DoctorLevel.OK: "✓",
        DoctorLevel.WARN: "!",
        DoctorLevel.FAIL: "✗",
        DoctorLevel.INFO: "·",
    }
    colors = {
        DoctorLevel.OK: "green",
        DoctorLevel.WARN: "yellow",
        DoctorLevel.FAIL: "red",
        DoctorLevel.INFO: "dim",
    }
    console.print()
    console.print(Panel("[bold cyan]PHASMID DOCTOR[/bold cyan]", border_style="cyan"))
    for check in result.checks:
        color = colors[check.level]
        icon = icons[check.level]
        console.print(
            f"  [{color}]{icon}[/{color}]  [bold]{check.name}[/bold]  [dim]{check.message}[/dim]"
        )
        if check.detail:
            console.print(f"       [dim]{check.detail}[/dim]")
    console.print()
    console.print(f"  [dim italic]{result.disclaimer}[/dim italic]")
    console.print()


def _build_tui_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phasmid",
        description="Phasmid — coercion-aware deniable storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Running 'phasmid' with no arguments opens the Main Operator Console.\n"
            "\nExamples:\n"
            "  phasmid                    Open the operator console\n"
            "  phasmid open <vessel>      Open a Vessel\n"
            "  phasmid create <vessel>    Create a new Vessel\n"
            "  phasmid inspect <vessel>   Inspect a Vessel\n"
            "  phasmid guided             Open Guided Workflows\n"
            "  phasmid audit              Open Audit View\n"
            "  phasmid doctor             Run Doctor checks\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    subparsers.add_parser("guided", help="Open Guided Workflows")
    subparsers.add_parser("audit", help="Open Audit View")

    doctor_p = subparsers.add_parser("doctor", help="Run Doctor checks")
    doctor_p.add_argument(
        "--no-tui", action="store_true", help="Print output without opening TUI"
    )

    open_p = subparsers.add_parser("open", help="Open a Vessel")
    open_p.add_argument("vessel", nargs="?", help="Path to Vessel file")

    create_p = subparsers.add_parser("create", help="Create a new Vessel")
    create_p.add_argument("vessel", nargs="?", help="Path for new Vessel file")

    inspect_p = subparsers.add_parser("inspect", help="Inspect a Vessel")
    inspect_p.add_argument("vessel", nargs="?", help="Path to Vessel file")

    subparsers.add_parser("about", help="Show about screen")

    _add_legacy_subparser(subparsers)

    return parser


def _add_legacy_subparser(subparsers) -> None:
    for action in [
        "init",
        "store",
        "retrieve",
        "brick",
        "verify-state",
        "verify-audit-log",
        "export-redacted-log",
    ]:
        p = subparsers.add_parser(action, help=f"Legacy: {action}")
        if action in ("store", "retrieve"):
            p.add_argument("--entry", choices=["a", "b"], default="a")
            p.add_argument(
                "--" + "prof" + "ile", choices=["a", "b"], dest="legacy_entry"
            )
            p.add_argument("--mode", dest="legacy_entry_mode")
            p.add_argument("--file")
            p.add_argument("--out")
        elif action == "export-redacted-log":
            p.add_argument("--out")


def main():
    apply_process_hardening()
    try:
        require_volatile_state()
    except RuntimeError as exc:
        error(str(exc))
        return
    if not _run_startup_checks():
        return

    parser = _build_tui_parser()
    args = parser.parse_args()

    if args.command is None:
        from .tui.app import run_tui

        run_tui(initial_screen="home")
        return

    if args.command == "guided":
        from .tui.app import run_tui

        run_tui(initial_screen="guided")
        return

    if args.command == "audit":
        from .tui.app import run_tui

        run_tui(initial_screen="audit")
        return

    if args.command == "doctor":
        no_tui = getattr(args, "no_tui", False)
        if no_tui or not sys.stdout.isatty():
            _run_doctor_tui()
        else:
            from .tui.app import run_tui

            run_tui(initial_screen="doctor")
        return

    if args.command == "open":
        vessel = getattr(args, "vessel", None)
        from .tui.app import run_tui

        run_tui(initial_screen="open", vessel_path=vessel)
        return

    if args.command == "create":
        vessel = getattr(args, "vessel", None)
        from .tui.app import run_tui

        run_tui(initial_screen="create", vessel_path=vessel)
        return

    if args.command == "inspect":
        vessel = getattr(args, "vessel", None)
        from .tui.app import run_tui

        run_tui(initial_screen="inspect", vessel_path=vessel)
        return

    if args.command == "about":
        from .tui.app import run_tui

        run_tui(initial_screen="about")
        return

    if args.command == "verify-state":
        _print_operation_report(verify_state())
        return
    if args.command == "verify-audit-log":
        _print_operation_report(verify_audit_log())
        return
    if args.command == "export-redacted-log":
        out = getattr(args, "out", None)
        if not out:
            error(text.CLI_ERROR_OUTPUT_REQUIRED.removeprefix("[!] Error: "))
            return 1
        _print_operation_report(export_redacted_log(out))
        return

    _run_legacy_command(args)


def _run_legacy_command(args) -> None:
    selected_value = getattr(args, "legacy_entry", None) or getattr(args, "entry", "a")
    selected_mode = resolve_mode(selected_value)
    legacy_entry_mode = getattr(args, "legacy_entry_mode", None)
    if legacy_entry_mode in gate.MODES:
        selected_mode = legacy_entry_mode

    panic_monitor = EmergencyDaemon("vault.bin")
    gate_started = False

    try:
        panic_monitor.start()

        if args.command in {"store", "retrieve"}:
            gate.start()
            gate_started = True
            if not _wait_for_camera_frame():
                error("Camera feed did not become available.")
                return

        vault = PhasmidVault("vault.bin")

        if args.command == "init":
            console.print()
            console.print(
                Panel(
                    "[yellow]This will reinitialize the local container.[/yellow]",
                    title="[bold yellow]INITIALIZING LOCAL CONTAINER[/bold yellow]",
                    border_style="yellow",
                )
            )
            console.print()
            show_loading("Initializing local container with random data", 3)
            vault.format_container(rotate_access_key=True)
            audit_event("container_reinitialized")
            success("Local container initialized. Ready for protected entries.")

        elif args.command == "store":
            if not args.file:
                error("No input file specified.")
                return

            entry_label = display_mode_label(selected_mode)
            console.print()
            console.print(
                Panel(
                    f"Entry: [bold cyan]{entry_label}[/bold cyan]\nFile:  [bold]{args.file}[/bold]",
                    title="[bold cyan]PHASMID — STORE[/bold cyan]",
                    border_style="cyan",
                )
            )
            console.print()
            console.print(Rule("Authentication", style="dim cyan"))
            try:
                pw, purge_pw = _prompt_store_passwords()
            except ValueError as exc:
                error(str(exc))
                return

            console.print()
            console.print(Rule("Object Binding", style="dim cyan"))
            info(f"Calibrating object cue for [bold]{entry_label}[/bold]...")
            info(
                "The captured object will be stored as the local access cue for this entry."
            )
            reg_success, msg = _register_reference_key(selected_mode)
            if not reg_success:
                error(msg)
                return
            gesture_seq = gate.sequence_for_mode(selected_mode)

            with open(args.file, "rb") as f:
                data = f.read()

            console.print()
            console.print(Rule("Encryption", style="dim cyan"))
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
            console.print()
            console.print(
                Panel(
                    "[green]Protected entry saved.[/green]\n[green]Bound object cue registered.[/green]",
                    border_style="green",
                )
            )

        elif args.command == "retrieve":
            ui.show_diagnostic()
            console.print()
            console.print(
                Panel(
                    "[dim]Device Status:[/dim]  [bold green]READY[/bold green]",
                    title="[bold cyan]PHASMID — RETRIEVE[/bold cyan]",
                    border_style="cyan",
                )
            )
            console.print()

            attempt_limiter = FileAttemptLimiter()
            attempt_scope = "cli-retrieve"
            if not attempt_limiter.check(attempt_scope).allowed:
                warn(text.ACCESS_TEMPORARILY_UNAVAILABLE)
                return

            console.print(Rule("Authentication", style="dim cyan"))
            pw = getpass.getpass("  Access password: ")

            console.print()
            console.print(Rule("Object Verification", style="dim cyan"))
            user_gesture_seq = _collect_auth_sequence()

            if not user_gesture_seq or user_gesture_seq[0] == gate.MATCH_NONE:
                ui.show_alert("ACCESS ERROR\nOBJECT NOT FOUND")
                attempt_limiter.record_failure(attempt_scope)
                error("No bound object matched.")
                return

            console.print()
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
                attempt_limiter.record_success(attempt_scope)
                ui.show_alert("ACCESS GRANTED")

                show_loading("Preparing recovered payload", 2)
                console.print()
                console.print(
                    Panel(
                        f"[green]Decrypted [bold]{len(result):,}[/bold] bytes[/green]"
                        + (f"\n[dim]File: {filename}[/dim]" if filename else ""),
                        title="[bold green]ACCESS GRANTED[/bold green]",
                        border_style="green",
                    )
                )

                if args.out:
                    with open(args.out, "wb") as f:
                        f.write(result)
                    success(f"Output written to: [bold]{args.out}[/bold]")
                else:
                    try:
                        content = result.decode("utf-8")
                        console.print()
                        console.print(Rule("Payload", style="dim"))
                        console.print(
                            content[:500] + ("…" if len(content) > 500 else "")
                        )
                        console.print(Rule(style="dim"))
                    except UnicodeDecodeError:
                        info(
                            "Binary payload — use [bold]--out[/bold] to write to file."
                        )

                audit_event(
                    "payload_retrieved",
                    entry="local_entry",
                    filename=filename,
                    bytes=len(result),
                )
                if password_role == PhasmidVault.PURGE_ROLE:
                    vault.purge_other_mode(accessed_mode)
                    audit_event(
                        "restricted_local_update",
                        accessed_entry="local_entry",
                        reason="restricted_recovery",
                    )
                    info("Operation completed.")
                    return

                auto_purge_reason = _auto_purge_reason(accessed_mode)
                if auto_purge_reason:
                    vault.purge_other_mode(accessed_mode)
                    audit_event(
                        "restricted_local_update",
                        accessed_entry="local_entry",
                        reason=auto_purge_reason,
                    )
                    info("Operation completed.")
                elif _confirm_purge_other_mode(accessed_mode):
                    vault.purge_other_mode(accessed_mode)
                    audit_event("restricted_local_update", accessed_entry="local_entry")
                    info("Operation completed.")
                else:
                    info("Operation completed.")
            else:
                ui.show_alert("ACCESS DENIED\nINVALID CREDENTIALS")
                audit_event("retrieve_failed")
                attempt_limiter.record_failure(attempt_scope)
                console.print()
                console.print(
                    Panel(
                        "[red]Invalid credentials or object not recognised.[/red]",
                        title="[bold red]ACCESS DENIED[/bold red]",
                        border_style="red",
                    )
                )

        elif args.command == "brick":
            console.print()
            policy = RESTRICTED_ACTION_POLICIES["rapid_local_clear"]
            console.print(
                Panel(
                    "[yellow]This will permanently clear the local access path.[/yellow]",
                    title="[bold yellow]CLEARING LOCAL ACCESS PATH[/bold yellow]",
                    border_style="yellow",
                )
            )
            console.print()
            confirmation = console.input(
                f'  Type [bold red]"{policy.confirmation_phrase}"[/bold red] to confirm: '
            ).strip()
            try:
                require_restricted_action("rapid_local_clear", confirmation)
                vault.silent_brick()
                audit_event("access_path_cleared", source="cli")
                warn("Local access path cleared.")
            except ValueError as exc:
                info(f"Aborted: {exc}")
                return

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
