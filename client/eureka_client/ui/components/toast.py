from __future__ import annotations

from PySide2.QtCore import QTimer
from PySide2.QtWidgets import QLabel


class Toast(QLabel):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Toast")
        self.setVisible(False)
        self.setWordWrap(True)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, message: str, kind: str = "info", timeout_ms: int = 4500) -> None:
        self.setProperty("kind", kind)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText(message)
        self.setVisible(True)
        self._timer.start(timeout_ms)
