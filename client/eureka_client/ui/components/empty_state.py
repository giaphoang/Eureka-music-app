from __future__ import annotations

from PySide2.QtWidgets import QLabel, QVBoxLayout, QWidget


class EmptyState(QWidget):
    def __init__(self, title: str, detail: str = "") -> None:
        super().__init__()
        self.setObjectName("EmptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        self.title = QLabel(title)
        self.title.setProperty("role", "emptyTitle")
        self.detail = QLabel(detail)
        self.detail.setProperty("role", "secondary")
        self.detail.setWordWrap(True)
        layout.addStretch()
        layout.addWidget(self.title)
        layout.addWidget(self.detail)
        layout.addStretch()

    def set_text(self, title: str, detail: str = "") -> None:
        self.title.setText(title)
        self.detail.setText(detail)
