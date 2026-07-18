from __future__ import annotations

from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from eureka_client.ui.components.empty_state import EmptyState
from eureka_client.ui.components.loading_state import LoadingState
from eureka_client.ui.components.track_table import TrackTable
from eureka_client.ui.theme import icon_path


class BrowsePage(QWidget):
    download_requested = Signal()
    download_track_requested = Signal(dict)
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
        self.table.set_overflow_enabled(
            True,
            text="",
            icon=QIcon(icon_path("download")),
            accessible_template="Download {title}",
            tooltip="Download",
        )
        self.table.overflow_requested.connect(lambda track, _button: self.download_track_requested.emit(track))
        self.empty = EmptyState("No tracks found", "Try a different search.")
        self.previous_button = QPushButton()
        self.previous_button.setObjectName("BrowsePreviousButton")
        self.previous_button.setProperty("role", "icon")
        self.previous_button.setIcon(QIcon(icon_path("chevron-left")))
        self.previous_button.setAccessibleName("Previous browse page")
        self.previous_button.setToolTip("Previous page")
        self.previous_button.clicked.connect(self.previous_page_requested.emit)
        self.next_button = QPushButton()
        self.next_button.setObjectName("BrowseNextButton")
        self.next_button.setProperty("role", "icon")
        self.next_button.setIcon(QIcon(icon_path("chevron-right")))
        self.next_button.setAccessibleName("Next browse page")
        self.next_button.setToolTip("Next page")
        self.next_button.clicked.connect(self.next_page_requested.emit)
        pagination = QHBoxLayout()
        pagination.setContentsMargins(0, 2, 0, 0)
        pagination.addStretch(1)
        pagination.addWidget(self.previous_button)
        pagination.addWidget(self.next_button)

        layout.addWidget(self.status)
        layout.addWidget(self.loading)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty, 1)
        layout.addLayout(pagination)
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
