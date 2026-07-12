from __future__ import annotations

from PySide2.QtCore import Signal
from PySide2.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from eureka_client.ui.components.empty_state import EmptyState
from eureka_client.ui.components.loading_state import LoadingState
from eureka_client.ui.components.track_table import TrackTable


class BrowsePage(QWidget):
    download_requested = Signal()
    previous_page_requested = Signal()
    next_page_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("BrowsePage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.setSpacing(10)

        self.status = QLabel("Catalog")
        self.status.setProperty("role", "secondary")
        self.loading = LoadingState("Loading catalog")
        self.table = TrackTable()
        self.empty = EmptyState("No tracks found", "Try a different search.")

        controls = QHBoxLayout()
        self.download_button = QPushButton("Download selected")
        self.download_button.setProperty("role", "primary")
        self.download_button.clicked.connect(self.download_requested)
        self.previous_button = QPushButton("Previous page")
        self.previous_button.clicked.connect(self.previous_page_requested)
        self.next_button = QPushButton("Next page")
        self.next_button.clicked.connect(self.next_page_requested)
        controls.addWidget(self.download_button)
        controls.addStretch()
        controls.addWidget(self.previous_button)
        controls.addWidget(self.next_button)

        layout.addWidget(self.status)
        layout.addWidget(self.loading)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty, 1)
        layout.addLayout(controls)
        self.set_loading(False)

    def selected_track(self) -> dict | None:
        return self.table.selected_track()

    def set_loading(self, loading: bool) -> None:
        self.loading.setVisible(loading)
        if loading:
            self.empty.setVisible(False)

    def set_page(self, tracks: list[dict], total: int, offset: int, limit: int) -> None:
        self.set_loading(False)
        self.table.set_tracks(tracks)
        self.table.setVisible(bool(tracks))
        self.empty.setVisible(not tracks)
        start = offset + 1 if total else 0
        end = offset + len(tracks)
        self.status.setText(f"{start}-{end} of {total}")
        self.previous_button.setEnabled(offset > 0)
        self.next_button.setEnabled(end < total)

    def set_error(self, message: str) -> None:
        self.set_loading(False)
        self.table.setVisible(False)
        self.empty.setVisible(True)
        self.empty.set_text("Server unavailable", message)
        self.status.setText("Server unavailable")
        self.previous_button.setEnabled(False)
        self.next_button.setEnabled(False)
