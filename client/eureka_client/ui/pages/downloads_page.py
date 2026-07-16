from __future__ import annotations

from PySide2.QtCore import Signal
from PySide2.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from eureka_client.ui.components.empty_state import EmptyState
from eureka_client.ui.components.track_table import TrackTable


class DownloadsPage(QWidget):
    play_requested = Signal()
    add_to_playlist_requested = Signal()
    refresh_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DownloadsPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 18)
        self.table = TrackTable()
        self.empty = EmptyState("No downloads yet", "Download tracks from Browse to play them offline.")

        controls = QHBoxLayout()
        play = QPushButton("Play selected")
        play.setProperty("role", "primary")
        play.clicked.connect(self.play_requested)
        add = QPushButton("Add to playlist")
        add.clicked.connect(self.add_to_playlist_requested)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_requested)
        controls.addWidget(play)
        controls.addWidget(add)
        controls.addStretch()
        controls.addWidget(refresh)

        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty, 1)
        layout.addLayout(controls)

    def selected_track(self) -> dict | None:
        return self.table.selected_track()

    def set_tracks(self, tracks: list[dict]) -> None:
        self.table.set_tracks(tracks)
        self.table.setVisible(bool(tracks))
        self.empty.setVisible(not tracks)
