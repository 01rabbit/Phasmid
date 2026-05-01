import os
import secrets
import time
import threading
from .audit import audit_event
from .bridge_ui import ui
from .config import PANIC_TOKEN_NAME, PANIC_TRIGGER_NAME, state_dir as default_state_dir
from .gv_core import GhostVault

class EmergencyDaemon:
    def __init__(self, vault_path="vault.bin", state_dir=None):
        self.vault = GhostVault(vault_path)
        self.state_dir = state_dir or default_state_dir()
        os.makedirs(self.state_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(self.state_dir, 0o700)
        except OSError:
            pass
        self.trigger_file = os.path.join(self.state_dir, PANIC_TRIGGER_NAME)
        self.token_file = os.path.join(self.state_dir, PANIC_TOKEN_NAME)
        self.panic_token = self._load_or_create_panic_token()
        self._stop_event = threading.Event()
        self._thread = None

    def _load_or_create_panic_token(self):
        if os.path.exists(self.token_file):
            with open(self.token_file, "r", encoding="utf-8") as handle:
                return handle.read().strip()

        token = secrets.token_urlsafe(32)
        with open(self.token_file, "w", encoding="utf-8") as handle:
            handle.write(token)
        try:
            os.chmod(self.token_file, 0o600)
        except OSError:
            pass
        return token

    def _authorized_trigger_present(self):
        if not os.path.exists(self.trigger_file):
            return False

        try:
            with open(self.trigger_file, "r", encoding="utf-8") as handle:
                supplied = handle.read().strip()
        except OSError:
            return False

        if secrets.compare_digest(supplied, self.panic_token):
            return True

        print(f"[EMERGENCY] Ignoring invalid panic trigger: {self.trigger_file}")
        try:
            os.remove(self.trigger_file)
        except OSError:
            pass
        return False

    def _watch_loop(self):
        print(f"[EMERGENCY] Monitoring for '{self.trigger_file}'...")
        while not self._stop_event.is_set():
            if self._authorized_trigger_present():
                print("\n[!!!] PANIC TRIGGER DETECTED! Executing Silent Brick...")
                ui.show_alert("EMERGENCY BRICK\nEXECUTING...")
                
                try:
                    self.vault.silent_brick()
                    audit_event("container_bricked", source="panic_trigger")
                    print("[!!!] Container successfully sanitized.")
                    os.remove(self.trigger_file)
                except Exception as e:
                    print(f"[ERROR] Brick failed: {e}")
                
                ui.show_alert("SYSTEM WIPED.\nREBOOT REQUIRED.")
                time.sleep(3)
                # End the process after a panic event so the cleared state is not reused.
                os._exit(1)
            time.sleep(1)

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._watch_loop, daemon=True)
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2)
