from __future__ import annotations

from pathlib import Path

from PySide2.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide2.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide2.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QScrollArea, QStyle, QToolButton, QVBoxLayout, QWidget

from eureka_client.ui.components.empty_state import EmptyState
from eureka_client.ui.components.track_table import TrackTable
from eureka_client.ui.theme import icon_path


class PlaylistCoverButton(QPushButton):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PlaylistCover")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Choose playlist cover")
        self.setAccessibleName("Choose playlist cover")
        self.setFixedSize(QSize(176, 176))
        self._cover_path: Path | None = None
        self._cover = QPixmap()
        self._placeholder = QIcon(icon_path("list-music")).pixmap(QSize(52, 52))

    def set_cover_path(self, path: str | None) -> None:
        candidate = Path(path).expanduser() if path else None
        if candidate and candidate.is_file():
            self._cover_path = candidate
            self._cover = QPixmap(str(candidate))
        else:
            self._cover_path = None
            self._cover = QPixmap()
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor("#202020"))

        if not self._cover.isNull():
            scaled = self._cover.scaled(rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = max(0, (scaled.width() - rect.width()) // 2)
            y = max(0, (scaled.height() - rect.height()) // 2)
            painter.drawPixmap(rect, scaled, QRect(x, y, rect.width(), rect.height()))
        else:
            icon_rect = QRect(0, 0, 52, 52)
            icon_rect.moveCenter(rect.center())
            painter.setOpacity(0.82)
            painter.drawPixmap(icon_rect, self._placeholder)
            painter.setOpacity(1.0)

        if self.underMouse() and self.isEnabled():
            painter.fillRect(rect, QColor(0, 0, 0, 145))
            painter.setPen(QColor("#FFFFFF"))
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, "Choose photo")


class SearchResultRow(QWidget):
    add_requested = Signal(dict)

    def __init__(self, track: dict, added: bool) -> None:
        super().__init__()
        self.track = track
        self.setObjectName("PlaylistSearchResultRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        self.artwork = QLabel()
        self.artwork.setObjectName("PlaylistSearchArtwork")
        self.artwork.setFixedSize(QSize(44, 44))
        self.artwork.setAlignment(Qt.AlignCenter)
        self._set_artwork()

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        self.title = QLabel(str(track.get("title") or "Untitled"))
        self.title.setProperty("role", "searchResultTitle")
        self.artist = QLabel(str(track.get("artist") or "Unknown artist"))
        self.artist.setProperty("role", "searchResultMeta")
        text_layout.addWidget(self.title)
        text_layout.addWidget(self.artist)

        self.album = QLabel(str(track.get("album") or "Unknown album"))
        self.album.setProperty("role", "searchResultMeta")

        self.add_button = QPushButton("Add")
        self.add_button.setObjectName("PlaylistSearchAddButton")
        self.add_button.clicked.connect(self._add_clicked)

        layout.addWidget(self.artwork)
        layout.addLayout(text_layout, 2)
        layout.addWidget(self.album, 2)
        layout.addStretch()
        layout.addWidget(self.add_button)
        self.set_added(added)

    def set_added(self, added: bool) -> None:
        self.add_button.setText("Added" if added else "Add")
        self.add_button.setEnabled(not added)
        self.add_button.setProperty("state", "added" if added else "ready")
        self.add_button.style().unpolish(self.add_button)
        self.add_button.style().polish(self.add_button)

    def _add_clicked(self) -> None:
        self.set_added(True)
        self.add_requested.emit(self.track)

    def _set_artwork(self) -> None:
        for key in ("artwork_path", "album_art_path", "cover_path"):
            path = self.track.get(key)
            if path and Path(str(path)).is_file():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    self.artwork.setPixmap(pixmap.scaled(self.artwork.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                    return
        self.artwork.setPixmap(QIcon(icon_path("list-music")).pixmap(QSize(24, 24)))


class PlaylistPage(QWidget):
    create_requested = Signal()
    cover_requested = Signal()
    primary_play_requested = Signal()
    add_search_result_requested = Signal(dict)
    remove_track_requested = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PlaylistPage")
        self._downloaded_tracks: list[dict] = []
        self._playlist_track_ids: set[int] = set()
        self._search_rows: list[SearchResultRow] = []
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(120)
        self._search_timer.timeout.connect(self._apply_search)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 18)
        layout.setSpacing(10)

        self.hero = QWidget()
        self.hero.setObjectName("PlaylistHero")
        hero_layout = QHBoxLayout(self.hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(24)

        self.cover = PlaylistCoverButton()
        self.cover.clicked.connect(self.cover_requested)

        copy_layout = QVBoxLayout()
        copy_layout.setSpacing(5)
        copy_layout.addStretch()
        self.kind = QLabel("Playlist")
        self.kind.setProperty("role", "playlistKind")
        self.title = QLabel("Playlists")
        self.title.setObjectName("PlaylistTitle")
        self.title.setWordWrap(True)
        self.owner = QLabel("You")
        self.owner.setProperty("role", "playlistMeta")
        self.meta = QLabel("Choose or create a playlist")
        self.meta.setProperty("role", "playlistMeta")
        copy_layout.addWidget(self.kind)
        copy_layout.addWidget(self.title)
        copy_layout.addWidget(self.owner)
        copy_layout.addWidget(self.meta)
        copy_layout.addStretch()

        create = QPushButton("Create playlist")
        create.setProperty("role", "primary")
        create.clicked.connect(self.create_requested)

        hero_layout.addWidget(self.cover)
        hero_layout.addLayout(copy_layout, 1)
        hero_layout.addWidget(create, 0, Qt.AlignTop)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 0, 18, 0)
        content_layout.setSpacing(0)
        self.table = TrackTable()
        self.table.set_overflow_enabled(True)
        self.table.overflow_requested.connect(self._open_track_menu)
        self.table.viewport().installEventFilter(self)
        self.empty = EmptyState("No playlist selected", "Create or choose a playlist from the sidebar.")
        content_layout.addWidget(self.table, 1)
        content_layout.addWidget(self.empty, 1)

        self.search_section = QWidget()
        self.search_section.setObjectName("PlaylistSearchSection")
        search_layout = QVBoxLayout(self.search_section)
        search_layout.setContentsMargins(18, 2, 18, 0)
        search_layout.setSpacing(10)

        search_header = QHBoxLayout()
        search_header.setContentsMargins(0, 0, 0, 0)
        self.search_title = QLabel("Let’s find something for your playlist")
        self.search_title.setProperty("role", "playlistSearchTitle")
        search_header.addWidget(self.search_title)
        search_header.addStretch()

        search_box = QWidget()
        search_box.setObjectName("PlaylistSearchBox")
        search_box_layout = QHBoxLayout(search_box)
        search_box_layout.setContentsMargins(10, 0, 6, 0)
        search_box_layout.setSpacing(6)
        search_icon = QLabel()
        search_icon.setPixmap(QIcon(icon_path("search")).pixmap(QSize(16, 16)))
        self.search_input = QLineEdit()
        self.search_input.setObjectName("PlaylistLocalSearchInput")
        self.search_input.setPlaceholderText("Search downloaded songs")
        self.search_input.setFrame(False)
        self.search_input.installEventFilter(self)
        self.search_input.textChanged.connect(self._search_text_changed)
        self.clear_search_button = QToolButton()
        self.clear_search_button.setObjectName("PlaylistClearSearchButton")
        self.clear_search_button.setText("×")
        self.clear_search_button.setToolTip("Clear search")
        self.clear_search_button.clicked.connect(self.search_input.clear)
        self.clear_search_button.setVisible(False)
        search_box_layout.addWidget(search_icon)
        search_box_layout.addWidget(self.search_input, 1)
        search_box_layout.addWidget(self.clear_search_button)

        self.search_results = QScrollArea()
        self.search_results.setObjectName("PlaylistSearchResults")
        self.search_results.setWidgetResizable(True)
        self.search_results.setFrameShape(QScrollArea.NoFrame)
        self.search_results_body = QWidget()
        self.search_results_layout = QVBoxLayout(self.search_results_body)
        self.search_results_layout.setContentsMargins(0, 0, 0, 0)
        self.search_results_layout.setSpacing(6)
        self.search_results.setWidget(self.search_results_body)
        self.search_empty = EmptyState("", "")
        self.search_empty.setObjectName("PlaylistSearchEmpty")

        search_layout.addLayout(search_header)
        search_layout.addWidget(search_box)
        search_layout.addWidget(self.search_results)
        search_layout.addWidget(self.search_empty)

        playback_controls = QHBoxLayout()
        playback_controls.setContentsMargins(18, 0, 18, 0)
        self.play_button = QPushButton(QIcon(icon_path("play")), "")
        self.play_button.setObjectName("PlaylistPlayButton")
        self.play_button.setToolTip("Play playlist")
        self.play_button.setAccessibleName("Play playlist")
        self.play_button.clicked.connect(self.primary_play_requested)
        playback_controls.addWidget(self.play_button)
        playback_controls.addStretch()

        self._track_menu: QMenu | None = None
        self._track_menu_button: QToolButton | None = None

        layout.addWidget(self.hero)
        layout.addLayout(playback_controls)
        layout.addWidget(content, 1)
        layout.addWidget(self.search_section)
        self.set_tracks(None, [])
        self.set_downloaded_tracks([])

    def selected_track(self) -> dict | None:
        return self.table.selected_track()

    def set_downloaded_tracks(self, tracks: list[dict]) -> None:
        self._downloaded_tracks = list(tracks)
        self._apply_search()

    def set_tracks(self, playlist: dict | None, tracks: list[dict]) -> None:
        self._playlist_track_ids = {int(track["server_id"]) for track in tracks if track.get("server_id") is not None}
        if playlist:
            self.title.setText(str(playlist["name"]))
            self.owner.setText("You")
            self.meta.setText(self._metadata_text(tracks))
            self.cover.setEnabled(True)
            self.cover.set_cover_path(playlist.get("cover_path"))
            self.play_button.setEnabled(bool(tracks))
        else:
            self.title.setText("Playlists")
            self.owner.setText("You")
            self.meta.setText("Choose or create a playlist")
            self.cover.setEnabled(False)
            self.cover.set_cover_path(None)
            self.play_button.setEnabled(False)
            self.search_input.clear()
        self.table.set_tracks(tracks)
        self.table.setVisible(bool(tracks))
        self.empty.setVisible(not tracks)
        self.search_section.setVisible(bool(playlist))
        if playlist and not tracks:
            self.empty.set_text("Playlist is empty", "Add downloaded tracks to start listening.")
        elif not playlist:
            self.empty.set_text("No playlist selected", "Create or choose a playlist from the sidebar.")
        self._apply_search()

    def set_playing(self, playing: bool) -> None:
        icon = "pause" if playing else "play"
        label = "Pause playlist" if playing else "Play playlist"
        self.play_button.setIcon(QIcon(icon_path(icon)))
        self.play_button.setToolTip(label)
        self.play_button.setAccessibleName(label)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.search_input and event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            if self.search_input.text():
                self.search_input.clear()
            self.search_results.setVisible(False)
            self.search_empty.setVisible(False)
            return True
        if watched is self.table.viewport() and event.type() == QEvent.Wheel:
            self.close_track_menu()
        return super().eventFilter(watched, event)

    def hideEvent(self, event) -> None:  # noqa: N802
        self.close_track_menu()
        super().hideEvent(event)

    def close_track_menu(self) -> None:
        if self._track_menu:
            self._track_menu.close()
            self._track_menu = None
        self.table.set_overflow_menu_row(-1)

    def _open_track_menu(self, track: dict, button: QToolButton) -> None:
        self.close_track_menu()
        row = self.table._row_for_overflow_button(button)
        self.table.set_overflow_menu_row(row)

        menu = QMenu(self)
        menu.setObjectName("PlaylistContextMenu")
        remove_action = menu.addAction("Remove from playlist")
        remove_action.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        remove_action.triggered.connect(lambda _checked=False, track=track: self._remove_context_track(track))
        menu.aboutToHide.connect(self._track_menu_closed)
        self._track_menu = menu
        self._track_menu_button = button
        global_position = button.mapToGlobal(QPoint(0, button.height()))
        menu.popup(self._bounded_menu_position(menu, global_position))

    def _remove_context_track(self, track: dict) -> None:
        self.remove_track_requested.emit(track)
        self.close_track_menu()

    def _track_menu_closed(self) -> None:
        button = self._track_menu_button
        self._track_menu = None
        self._track_menu_button = None
        self.table.set_overflow_menu_row(-1)
        if button:
            button.setFocus()

    @staticmethod
    def _bounded_menu_position(menu: QMenu, global_position: QPoint) -> QPoint:
        screen = QApplication.screenAt(global_position) or QApplication.primaryScreen()
        if not screen:
            return global_position
        geometry = screen.availableGeometry()
        size = menu.sizeHint()
        x = min(global_position.x(), geometry.right() - size.width())
        y = min(global_position.y(), geometry.bottom() - size.height())
        return QPoint(max(geometry.left(), x), max(geometry.top(), y))

    def _search_text_changed(self, text: str) -> None:
        self.clear_search_button.setVisible(bool(text))
        self._search_timer.start()

    def _apply_search(self) -> None:
        display_query = " ".join(self.search_input.text().split())
        query = display_query.lower()
        if not display_query:
            self._set_search_result_rows([])
            self.search_results.setVisible(False)
            self.search_empty.setVisible(False)
            return

        matches = [
            track
            for track in self._downloaded_tracks
            if self._track_matches(track, query)
        ][:25]
        self._set_search_result_rows(matches)
        self.search_results.setVisible(bool(matches))
        self.search_empty.setVisible(not matches)
        if not matches:
            self.search_empty.set_text(f"No downloaded songs match “{display_query}”.")

    def set_search_result_added(self, track_id: int, added: bool) -> None:
        if added:
            self._playlist_track_ids.add(int(track_id))
        else:
            self._playlist_track_ids.discard(int(track_id))
        for row in self._search_rows:
            if int(row.track.get("server_id")) == int(track_id):
                row.set_added(added)

    def _set_search_result_rows(self, tracks: list[dict]) -> None:
        while self.search_results_layout.count():
            item = self.search_results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._search_rows = []
        for track in tracks:
            track_id = int(track["server_id"])
            row = SearchResultRow(track, track_id in self._playlist_track_ids)
            row.add_requested.connect(self.add_search_result_requested)
            self.search_results_layout.addWidget(row)
            self._search_rows.append(row)
        self.search_results_layout.addStretch()

    @staticmethod
    def _track_matches(track: dict, query: str) -> bool:
        fields = (track.get("title"), track.get("artist"), track.get("album"))
        return any(query in str(value or "").lower() for value in fields)

    @staticmethod
    def _metadata_text(tracks: list[dict]) -> str:
        count = len(tracks)
        song_text = "1 song" if count == 1 else f"{count} songs"
        total_ms = sum(int(track.get("duration_ms") or 0) for track in tracks)
        minutes = max(1, round(total_ms / 60_000)) if total_ms else 0
        if minutes:
            return f"{song_text} · {minutes} min"
        return song_text
