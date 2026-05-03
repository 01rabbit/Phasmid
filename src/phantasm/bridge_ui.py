import cv2
import numpy as np


class GhostUI:
    """
    Whisplay HAT (ST7789) UI Simulator for macOS
    """

    def __init__(self):
        self.width = 240
        self.height = 240
        self.canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.window_name = "Whisplay HAT Simulator"

    def clear(self):
        self.canvas.fill(0)

    def draw_text(self, text, pos, color=(0, 255, 0), size=0.5):
        cv2.putText(self.canvas, text, pos, cv2.FONT_HERSHEY_SIMPLEX, size, color, 1)

    def show_diagnostic(self):
        self.clear()
        self.draw_text("SYSTEM DIAGNOSTIC", (20, 40), color=(0, 255, 255), size=0.6)
        self.draw_text("------------------", (20, 60))
        self.draw_text("CPU: 34%  TEMP: 42C", (20, 90))
        self.draw_text("RAM: 128/512MB", (20, 120))
        self.draw_text("VAULT: MOUNTED", (20, 150), color=(0, 255, 0))
        self.draw_text("STATUS: STANDBY", (20, 180))
        self.refresh()

    def show_alert(self, message):
        self.clear()
        # Red alert frame.
        cv2.rectangle(self.canvas, (10, 10), (230, 230), (0, 0, 255), 2)
        self.draw_text("!!! ALERT !!!", (60, 60), color=(0, 0, 255), size=0.7)
        lines = message.split("\n")
        for i, line in enumerate(lines):
            self.draw_text(line, (20, 100 + i * 30), color=(255, 255, 255), size=0.5)
        self.refresh()

    def refresh(self):
        cv2.imshow(self.window_name, self.canvas)
        cv2.waitKey(1)

    def close(self):
        cv2.destroyWindow(self.window_name)


# Shared UI instance.
ui = GhostUI()
