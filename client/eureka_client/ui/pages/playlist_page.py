from __future__ import annotations

from PySide2.QtCore import Signal
from PySide2.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from eureka_client.ui.components.empty_state import EmptyState
from eureka_client.ui.components.track_table import TrackTable


class PlaylistPage(QWidget):
    create_requested = Signal()
    play_requested = Signal()
    remove_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PlaylistPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.title = QLabel("Playlists")
        self.title.setProperty("role", "pageTitle")
        create = QPushButton("Create playlist")
        create.setProperty("role", "primary")
        create.clicked.connect(self.create_requested)
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(create)

        self.table = TrackTable()
        self.empty = EmptyState("No playlist selected", "Create or choose a playlist from the sidebar.")

        controls = QHBoxLayout()
        play = QPushButton("Play playlist")
        play.setProperty("role", "primary")
        play.clicked.connect(self.play_requested)
        remove = QPushButton("Remove")
        remove.clicked.connect(self.remove_requested)
        controls.addWidget(play)
        controls.addWidget(remove)
        controls.addStretch()

        layout.addLayout(header)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty, 1)
        layout.addLayout(controls)
        self.set_tracks(None, [])

    def selected_track(self) -> dict | None:
        return self.table.selected_track()

    def set_tracks(self, playlist: dict | None, tracks: list[dict]) -> None:
        if playlist:
            self.title.setText(str(playlist["name"]))
        else:
            self.title.setText("Playlists")
        self.table.set_tracks(tracks)
        self.table.setVisible(bool(tracks))
        self.empty.setVisible(not tracks)
        if playlist and not tracks:
            self.empty.set_text("Playlist is empty", "Add downloaded tracks to start listening.")
        elif not playlist:
            self.empty.set_text("No playlist selected", "Create or choose a playlist from the sidebar.")
