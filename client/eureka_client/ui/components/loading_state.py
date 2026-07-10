from __future__ import annotations

from PySide2.QtWidgets import QLabel, QHBoxLayout, QWidget


class LoadingState(QWidget):
    def __init__(self, text: str = "Loading") -> None:
        super().__init__()
        self.setObjectName("LoadingState")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.label = QLabel(text)
        self.label.setProperty("role", "secondary")
        layout.addWidget(self.label)
        layout.addStretch()

    def set_text(self, text: str) -> None:
        self.label.setText(text)
