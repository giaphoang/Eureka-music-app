from __future__ import annotations

from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from eureka_client.ui.theme import icon_path


class TopBar(QWidget):
    search_submitted = Signal(str)
    back_requested = Signal()
    forward_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TopBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        self.back_button = QPushButton(QIcon(icon_path("chevron-left")), "")
        self.back_button.setProperty("role", "icon")
        self.back_button.setToolTip("Back")
        self.back_button.setAccessibleName("Back")
        self.back_button.setEnabled(False)
        self.back_button.clicked.connect(self.back_requested)

        self.forward_button = QPushButton(QIcon(icon_path("chevron-right")), "")
        self.forward_button.setProperty("role", "icon")
        self.forward_button.setToolTip("Forward")
        self.forward_button.setAccessibleName("Forward")
        self.forward_button.setEnabled(False)
        self.forward_button.clicked.connect(self.forward_requested)

        self.title = QLabel("Browse")
        self.title.setProperty("role", "pageTitle")

        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("Search title, artist, or album")
        self.search_input.returnPressed.connect(self._submit_search)

        search_button = QPushButton(QIcon(icon_path("search")), "")
        search_button.setProperty("role", "icon")
        search_button.setToolTip("Search")
        search_button.setAccessibleName("Search")
        search_button.clicked.connect(self._submit_search)

        layout.addWidget(self.back_button)
        layout.addWidget(self.forward_button)
        layout.addWidget(self.title)
        layout.addStretch()
        layout.addWidget(self.search_input, 0)
        layout.addWidget(search_button)

    def set_title(self, title: str) -> None:
        self.title.setText(title)

    def set_search_visible(self, visible: bool) -> None:
        self.search_input.setVisible(visible)

    def search_text(self) -> str:
        return self.search_input.text().strip()

    def focus_search(self) -> None:
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _submit_search(self) -> None:
        self.search_submitted.emit(self.search_text())
