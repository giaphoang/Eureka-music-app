from __future__ import annotations

from PySide2.QtCore import QPoint, Signal
from PySide2.QtWidgets import QApplication, QLineEdit, QMenu, QVBoxLayout, QWidget, QWidgetAction

from eureka_client.ui.components.empty_state import EmptyState
from eureka_client.ui.components.track_table import TrackTable


class DownloadsPage(QWidget):
    add_track_to_playlist_requested = Signal(dict, int)
    create_playlist_with_track_requested = Signal(dict)
    refresh_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DownloadsPage")
        self._playlists: list[dict] = []
        self._tracks: list[dict] = []
        self._search_query = ""
        self._track_menu: QMenu | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 18)
        self.table = TrackTable()
        self.table.set_overflow_enabled(
            True,
            accessible_template="More options for {title}",
            tooltip="More options",
        )
        self.table.overflow_requested.connect(self._open_track_menu)
        self.empty = EmptyState("No downloads yet", "Download tracks from Browse to play them offline.")

        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty, 1)

    def selected_track(self) -> dict | None:
        return self.table.selected_track()

    def set_playlists(self, playlists: list[dict]) -> None:
        self._playlists = list(playlists)

    def set_tracks(self, tracks: list[dict]) -> None:
        self._tracks = list(tracks)
        self._apply_filter()

    def set_search_query(self, query: str) -> None:
        self._search_query = " ".join(query.split()).lower()
        self._apply_filter()

    def close_track_menu(self) -> None:
        if self._track_menu:
            self._track_menu.close()
            self._track_menu = None

    def hideEvent(self, event) -> None:  # noqa: N802
        self.close_track_menu()
        super().hideEvent(event)

    def _open_track_menu(self, track: dict, button) -> None:
        self.close_track_menu()
        menu = QMenu(self)
        menu.setObjectName("DownloadsTrackMenu")
        submenu = QMenu("Add to playlist", menu)
        submenu.setObjectName("DownloadsPlaylistSubmenu")
        self._populate_playlist_submenu(submenu, track)
        menu.addMenu(submenu)
        menu.aboutToHide.connect(lambda: setattr(self, "_track_menu", None))
        self._track_menu = menu
        global_position = button.mapToGlobal(QPoint(0, button.height()))
        menu.popup(self._bounded_menu_position(menu, global_position))

    def _apply_filter(self) -> None:
        if self._search_query:
            tracks = [track for track in self._tracks if self._matches_search(track, self._search_query)]
        else:
            tracks = list(self._tracks)
        self.table.set_tracks(tracks)
        self.table.setVisible(bool(tracks))
        self.empty.setVisible(not tracks)
        if self._tracks and self._search_query and not tracks:
            self.empty.set_text("No downloaded songs found", "Try a different local search.")
        else:
            self.empty.set_text("No downloads yet", "Download tracks from Browse to play them offline.")

    @staticmethod
    def _matches_search(track: dict, query: str) -> bool:
        fields = (track.get("title"), track.get("artist"), track.get("album"))
        return any(query in str(value or "").lower() for value in fields)

    def _populate_playlist_submenu(self, menu: QMenu, track: dict) -> None:
        menu.clear()
        search = QLineEdit()
        search.setObjectName("DownloadsPlaylistSearchInput")
        search.setPlaceholderText("Find a playlist")
        search_action = QWidgetAction(menu)
        search_action.setDefaultWidget(search)
        menu.addAction(search_action)

        new_action = menu.addAction("New playlist")
        new_action.triggered.connect(lambda _checked=False, track=track: self._create_playlist(track))
        menu.addSeparator()

        playlist_actions = []
        for playlist in self._playlists:
            action = menu.addAction(str(playlist["name"]))
            action.triggered.connect(
                lambda _checked=False, track=track, playlist_id=int(playlist["id"]): self._add_to_playlist(track, playlist_id)
            )
            playlist_actions.append((playlist, action))
        empty = menu.addAction("No playlists found")
        empty.setEnabled(False)
        empty.setVisible(not playlist_actions)
        search.textChanged.connect(lambda text: self._filter_playlist_actions(text, playlist_actions, empty))

    @staticmethod
    def _filter_playlist_actions(text: str, playlist_actions: list[tuple[dict, object]], empty_action) -> None:
        query = " ".join(text.split()).lower()
        shown = 0
        for playlist, action in playlist_actions:
            visible = query in str(playlist.get("name") or "").lower()
            action.setVisible(visible)
            shown += int(visible)
        empty_action.setVisible(shown == 0)

    def _add_to_playlist(self, track: dict, playlist_id: int) -> None:
        self.add_track_to_playlist_requested.emit(track, playlist_id)
        self.close_track_menu()

    def _create_playlist(self, track: dict) -> None:
        self.create_playlist_with_track_requested.emit(track)
        self.close_track_menu()

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
