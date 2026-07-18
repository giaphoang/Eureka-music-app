from __future__ import annotations

from PySide2.QtCore import QAbstractTableModel, QEvent, QModelIndex, QPropertyAnimation, Qt, Signal
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QAbstractItemView, QGraphicsOpacityEffect, QHeaderView, QTableView, QToolButton


COLUMNS = [("title", "Title"), ("artist", "Artist"), ("album", "Album"), ("genre", "Genre")]


class TrackTableModel(QAbstractTableModel):
    def __init__(self, tracks: list[dict] | None = None, include_actions: bool = False) -> None:
        super().__init__()
        self.tracks = tracks or []
        self.include_actions = include_actions

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.tracks)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS) + int(self.include_actions)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.tracks)):
            return None
        if role == Qt.DisplayRole:
            if index.column() >= len(COLUMNS):
                return ""
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
            if section >= len(COLUMNS):
                return ""
            return COLUMNS[section][1]
        return super().headerData(section, orientation, role)

    def set_include_actions(self, enabled: bool) -> None:
        self.beginResetModel()
        self.include_actions = enabled
        self.endResetModel()

    def replace_tracks(self, tracks: list[dict]) -> None:
        self.beginResetModel()
        self.tracks = tracks
        self.endResetModel()


class TrackTable(QTableView):
    track_clicked = Signal(dict)
    row_clicked = Signal(int)
    track_activated = Signal(dict)
    row_activated = Signal(int)
    overflow_requested = Signal(dict, object)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TrackTable")
        self.model_data = TrackTableModel()
        self.setModel(self.model_data)
        self._overflow_enabled = False
        self._overflow_buttons: dict[int, QToolButton] = {}
        self._overflow_effects: dict[int, QGraphicsOpacityEffect] = {}
        self._overflow_animations: dict[int, QPropertyAnimation] = {}
        self._overflow_text = "•••"
        self._overflow_icon = QIcon()
        self._overflow_accessible_template = "More options for {title}"
        self._overflow_tooltip = "More options"
        self._hovered_row = -1
        self._menu_row = -1
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.setSortingEnabled(False)
        self.setShowGrid(False)
        self.clicked.connect(self._click_index)
        self.doubleClicked.connect(self._activate_index)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)
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
        self._install_overflow_buttons()

    def set_overflow_enabled(
        self,
        enabled: bool,
        *,
        text: str = "•••",
        icon: QIcon | None = None,
        accessible_template: str = "More options for {title}",
        tooltip: str = "More options",
    ) -> None:
        self._overflow_enabled = enabled
        self._overflow_text = text
        self._overflow_icon = icon or QIcon()
        self._overflow_accessible_template = accessible_template
        self._overflow_tooltip = tooltip
        self.model_data.set_include_actions(enabled)
        if enabled:
            self.horizontalHeader().setSectionResizeMode(len(COLUMNS), QHeaderView.Fixed)
            self.setColumnWidth(len(COLUMNS), 48)
        self._install_overflow_buttons()

    def set_overflow_menu_row(self, row: int) -> None:
        previous = self._menu_row
        self._menu_row = row
        self._update_overflow_visibility(previous)
        self._update_overflow_visibility(row)

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

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.viewport():
            if event.type() == QEvent.MouseMove:
                self._set_hovered_row(self.indexAt(event.pos()).row())
            elif event.type() in {QEvent.Leave, QEvent.Wheel}:
                self._set_hovered_row(-1)
        elif isinstance(watched, QToolButton):
            row = self._row_for_overflow_button(watched)
            if event.type() == QEvent.Enter:
                self._set_hovered_row(row)
            elif event.type() == QEvent.Leave:
                self._set_hovered_row(-1)
        return super().eventFilter(watched, event)

    def _activate_index(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        row = index.row()
        if 0 <= row < len(self.model_data.tracks):
            self.row_activated.emit(row)
            self.track_activated.emit(self.model_data.tracks[row])

    def _click_index(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        if self._overflow_enabled and index.column() >= len(COLUMNS):
            return
        row = index.row()
        if 0 <= row < len(self.model_data.tracks):
            self.row_clicked.emit(row)
            self.track_clicked.emit(self.model_data.tracks[row])

    def _install_overflow_buttons(self) -> None:
        self._overflow_buttons = {}
        self._overflow_effects = {}
        self._overflow_animations = {}
        if not self._overflow_enabled:
            return
        for row, track in enumerate(self.model_data.tracks):
            button = QToolButton(self)
            button.setObjectName("TrackOverflowButton")
            button.setText(self._overflow_text)
            button.setIcon(self._overflow_icon)
            button.setToolTip(self._overflow_tooltip)
            title = track.get("title") or "song"
            button.setAccessibleName(self._overflow_accessible_template.format(title=title))
            button.setFocusPolicy(Qt.TabFocus)
            button.installEventFilter(self)
            effect = QGraphicsOpacityEffect(button)
            effect.setOpacity(0.0)
            button.setGraphicsEffect(effect)
            button.clicked.connect(lambda _checked=False, row=row: self._emit_overflow(row))
            self.setIndexWidget(self.model_data.index(row, len(COLUMNS)), button)
            self._overflow_buttons[row] = button
            self._overflow_effects[row] = effect
            self._update_overflow_visibility(row)

    def _emit_overflow(self, row: int) -> None:
        if 0 <= row < len(self.model_data.tracks):
            self.set_overflow_menu_row(row)
            self.overflow_requested.emit(self.model_data.tracks[row], self._overflow_buttons[row])

    def _set_hovered_row(self, row: int) -> None:
        if row == self._hovered_row:
            return
        previous = self._hovered_row
        self._hovered_row = row
        self._update_overflow_visibility(previous)
        self._update_overflow_visibility(row)

    def _update_overflow_visibility(self, row: int) -> None:
        button = self._overflow_buttons.get(row)
        if not button:
            return
        active = row == self._hovered_row
        button.setProperty("active", active)
        button.style().unpolish(button)
        button.style().polish(button)
        effect = self._overflow_effects.get(row)
        if not effect:
            return
        target = 1.0 if active else 0.0
        previous = self._overflow_animations.get(row)
        if previous:
            previous.stop()
        if not active:
            effect.setOpacity(0.0)
            return
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(120)
        animation.setStartValue(effect.opacity())
        animation.setEndValue(target)
        animation.start()
        self._overflow_animations[row] = animation

    def _row_for_overflow_button(self, button: QToolButton) -> int:
        for row, candidate in self._overflow_buttons.items():
            if candidate is button:
                return row
        return -1
