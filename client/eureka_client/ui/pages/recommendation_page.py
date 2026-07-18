from __future__ import annotations

from PySide2.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide2.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from eureka_client.ui.components.empty_state import EmptyState
from eureka_client.ui.components.loading_state import LoadingState


COLUMNS = [
    ("position", "#"),
    ("title", "Title"),
    ("artist", "Artist"),
    ("album", "Album"),
    ("genre", "Genre"),
    ("prompt_similarity", "Match"),
]


class RecommendationTableModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self.tracks: list[dict] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.tracks)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.tracks)):
            return None
        track = self.tracks[index.row()]
        if role == Qt.DisplayRole:
            key = COLUMNS[index.column()][0]
            value = track.get(key)
            if key == "prompt_similarity" and value is not None:
                return f"{float(value):.2f}"
            return str(value or "")
        if role == Qt.UserRole:
            return track
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return COLUMNS[section][1]
        return super().headerData(section, orientation, role)

    def replace_tracks(self, tracks: list[dict]) -> None:
        self.beginResetModel()
        self.tracks = tracks
        self.endResetModel()


class RecommendationPage(QWidget):
    generate_requested = Signal(str, int)
    download_all_requested = Signal()
    save_playlist_requested = Signal()
    play_downloaded_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("RecommendationPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.setSpacing(10)

        prompt_row = QHBoxLayout()
        self.prompt_input = QPlainTextEdit()
        self.prompt_input.setPlaceholderText("Dreamy electronic music for late-night coding")
        self.prompt_input.setMaximumHeight(86)
        self.size_input = QSpinBox()
        self.size_input.setRange(5, 10)
        self.size_input.setValue(10)
        self.generate_button = QPushButton("Generate")
        self.generate_button.setProperty("role", "primary")
        self.generate_button.clicked.connect(self._emit_generate)
        prompt_row.addWidget(self.prompt_input, 1)
        prompt_row.addWidget(self.size_input)
        prompt_row.addWidget(self.generate_button)

        self.status = QLabel("")
        self.status.setProperty("role", "secondary")
        self.loading = LoadingState("Generating playlist")
        self.empty = EmptyState("No generated playlist", "Enter a prompt to retrieve catalog tracks.")
        self.table = QTableView()
        self.table.setObjectName("RecommendationTable")
        self.model_data = RecommendationTableModel()
        self.table.setModel(self.model_data)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for column in (0, 2, 3, 4, 5):
            header.setSectionResizeMode(column, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 48)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 180)
        self.table.setColumnWidth(4, 120)
        self.table.setColumnWidth(5, 80)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)

        actions = QHBoxLayout()
        self.download_button = QPushButton("Download all")
        self.download_button.clicked.connect(self.download_all_requested)
        self.save_button = QPushButton("Save playlist")
        self.save_button.clicked.connect(self.save_playlist_requested)
        self.play_button = QPushButton("Play downloaded")
        self.play_button.setProperty("role", "primary")
        self.play_button.clicked.connect(self.play_downloaded_requested)
        actions.addWidget(self.download_button)
        actions.addWidget(self.save_button)
        actions.addWidget(self.play_button)
        actions.addStretch()

        layout.addLayout(prompt_row)
        layout.addWidget(self.status)
        layout.addWidget(self.loading)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty, 1)
        layout.addLayout(actions)
        self.set_tracks([])
        self.set_generating(False)

    def prompt(self) -> str:
        return " ".join(self.prompt_input.toPlainText().split())

    def tracks(self) -> list[dict]:
        return list(self.model_data.tracks)

    def set_generating(self, generating: bool) -> None:
        self.loading.setVisible(generating)
        self.generate_button.setEnabled(not generating)
        self.prompt_input.setEnabled(not generating)
        self.size_input.setEnabled(not generating)
        if generating:
            self.status.setText("Generating...")

    def set_tracks(self, tracks: list[dict]) -> None:
        self.model_data.replace_tracks(tracks)
        self.table.setVisible(bool(tracks))
        self.empty.setVisible(not tracks)
        self.download_button.setEnabled(bool(tracks))
        self.save_button.setEnabled(bool(tracks))
        self.play_button.setEnabled(bool(tracks))
        self.status.setText(f"{len(tracks)} generated track(s)" if tracks else "")

    def set_error(self, message: str) -> None:
        self.set_generating(False)
        self.table.setVisible(False)
        self.empty.setVisible(True)
        self.empty.set_text("Playlist unavailable", message)
        self.status.setText("Playlist unavailable")

    def _emit_generate(self) -> None:
        self.generate_requested.emit(self.prompt(), int(self.size_input.value()))
