from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from typing import Callable


class WebUIService:
    """Manages the WebUI subprocess and inactivity auto-kill timer."""

    _instance: WebUIService | None = None
    _lock = threading.Lock()

    def __new__(cls) -> WebUIService:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_service()
            return cls._instance

    def _init_service(self) -> None:
        self._process: subprocess.Popen | None = None
        self._timer: threading.Timer | None = None
        self._timeout_seconds = 600  # 10 minutes
        self._on_timeout_cb: Callable[[], None] | None = None
        self._start_time: float | None = None

    def set_timeout_callback(self, callback: Callable[[], None]) -> None:
        """Set a callback to be executed when the WebUI is auto-killed."""
        self._on_timeout_cb = callback

    def is_running(self) -> bool:
        """Check if the WebUI process is currently running."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def start(self, host: str = "127.0.0.1", port: int = 8000) -> bool:
        """Start the WebUI subprocess."""
        if self.is_running():
            return True

        env = os.environ.copy()
        env["PHASMID_HOST"] = host
        env["PHASMID_PORT"] = str(port)

        # Run as a module to ensure imports work correctly
        cmd = [sys.executable, "-m", "phasmid.web_server"]

        try:
            self._process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._start_time = time.time()
            self.reset_timer()
            return True
        except Exception:
            return False

    def stop(self) -> None:
        """Stop the WebUI subprocess and cancel the timer."""
        self._cancel_timer()
        if self._process:
            try:
                # Use process group to ensure all child processes are killed
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
            except Exception:
                try:
                    self._process.terminate()
                except Exception:
                    pass
            self._process = None
        self._start_time = None

    def reset_timer(self) -> None:
        """Reset the inactivity timer if the WebUI is running."""
        self._cancel_timer()
        if self.is_running():
            self._timer = threading.Timer(self._timeout_seconds, self._handle_timeout)
            self._timer.daemon = True
            self._timer.start()

    def _cancel_timer(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _handle_timeout(self) -> None:
        """Triggered when the inactivity timer expires."""
        if self.is_running():
            self.stop()
            if self._on_timeout_cb:
                self._on_timeout_cb()

    @property
    def uptime_seconds(self) -> float:
        """Return the number of seconds the WebUI has been running."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time
