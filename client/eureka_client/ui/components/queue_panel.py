from __future__ import annotations

from PySide2.QtCore import Signal
from PySide2.QtWidgets import QLabel, QVBoxLayout, QWidget

from eureka_client.ui.components.empty_state import EmptyState
from eureka_client.ui.components.track_table import TrackTable


class QueuePanel(QWidget):
    row_requested = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("QueuePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        self.title = QLabel("Up next")
        self.title.setProperty("role", "sectionTitle")
        self.table = TrackTable()
        self.empty = EmptyState("Queue is empty", "Start playback to see upcoming tracks.")
        self.table.row_activated.connect(self.row_requested)
        layout.addWidget(self.title)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty, 1)
        self.set_queue([], -1)

    def set_queue(self, tracks: list[dict], current_index: int) -> None:
        self.table.set_tracks(tracks)
        self.table.setVisible(bool(tracks))
        self.empty.setVisible(not tracks)
        if tracks and current_index >= 0:
            self.table.select_row(current_index)
