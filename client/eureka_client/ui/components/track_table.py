from __future__ import annotations

from PySide2.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide2.QtWidgets import QAbstractItemView, QHeaderView, QTableView


COLUMNS = [("title", "Title"), ("artist", "Artist"), ("album", "Album"), ("genre", "Genre")]


class TrackTableModel(QAbstractTableModel):
    def __init__(self, tracks: list[dict] | None = None) -> None:
        super().__init__()
        self.tracks = tracks or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.tracks)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.tracks)):
            return None
        if role == Qt.DisplayRole:
            key = COLUMNS[index.column()][0]
            return str(self.tracks[index.row()].get(key) or "")
        if role == Qt.UserRole:
            return self.tracks[index.row()]
        if role == Qt.ToolTipRole:
            track = self.tracks[index.row()]
            return f"{track.get('title', '')}\n{track.get('artist', '')}"
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return COLUMNS[section][1]
        return super().headerData(section, orientation, role)

    def replace_tracks(self, tracks: list[dict]) -> None:
        self.beginResetModel()
        self.tracks = tracks
        self.endResetModel()


class TrackTable(QTableView):
    track_activated = Signal(dict)
    row_activated = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TrackTable")
        self.model_data = TrackTableModel()
        self.setModel(self.model_data)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.setSortingEnabled(False)
        self.setShowGrid(False)
        self.doubleClicked.connect(self._activate_index)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2, 3):
            header.setSectionResizeMode(column, QHeaderView.Interactive)
        self.setColumnWidth(1, 220)
        self.setColumnWidth(2, 220)
        self.setColumnWidth(3, 120)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(32)

    def set_tracks(self, tracks: list[dict]) -> None:
        self.model_data.replace_tracks(tracks)

    def selected_track(self) -> dict | None:
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model_data.tracks[row] if 0 <= row < len(self.model_data.tracks) else None

    def selected_row(self) -> int:
        indexes = self.selectionModel().selectedRows()
        return indexes[0].row() if indexes else -1

    def select_row(self, row: int) -> None:
        if 0 <= row < self.model_data.rowCount():
            self.selectRow(row)

    def _activate_index(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        row = index.row()
        if 0 <= row < len(self.model_data.tracks):
            self.row_activated.emit(row)
            self.track_activated.emit(self.model_data.tracks[row])
