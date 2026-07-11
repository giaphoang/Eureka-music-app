from __future__ import annotations

from pathlib import Path

from PySide2.QtCore import QThreadPool, Qt
from PySide2.QtGui import QCloseEvent, QKeySequence
from PySide2.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QShortcut,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from eureka_client.api import MusicAPI
from eureka_client.db import ClientDB
from eureka_client.player import PlaybackController
from eureka_client.ui.components import PlayerBar, QueuePanel, Sidebar, Toast, TopBar
from eureka_client.ui.pages import BrowsePage, DownloadsPage, PlaylistPage, UploadPage
from eureka_client.workers.task import Task


PAGE_TITLES = {
    "browse": "Browse",
    "downloads": "Downloads",
    "playlists": "Playlists",
    "upload": "Upload",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Eureka Music")
        self.resize(1180, 760)

        self.api = MusicAPI()
        self.db = ClientDB()
        self.player = PlaybackController()
        self.pool = QThreadPool.globalInstance()
        self.catalog_tracks: list[dict] = []
        self.catalog_offset = 0
        self.catalog_limit = 500
        self.catalog_total = 0
        self.local_tracks: list[dict] = []
        self.playlists: list[dict] = []
        self.playlist_tracks: list[dict] = []
        self.current_playlist_id: int | None = None
        self.current_queue: list[dict] = []
        self.current_page = "browse"
        self._catalog_request_id = 0

        root = QWidget()
        root.setObjectName("AppRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.top_bar = TopBar()
        self.toast = Toast()
        self.player_bar = PlayerBar()
        self.queue_panel = QueuePanel()
        self.queue_panel.setVisible(False)

        self.stack = QStackedWidget()
        self.stack.setObjectName("MainSurface")
        self.browse_page = BrowsePage()
        self.downloads_page = DownloadsPage()
        self.playlist_page = PlaylistPage()
        self.upload_page = UploadPage()
        self.pages = {
            "browse": self.browse_page,
            "downloads": self.downloads_page,
            "playlists": self.playlist_page,
            "upload": self.upload_page,
        }
        for page in self.pages.values():
            self.stack.addWidget(page)

        center = QWidget()
        center.setObjectName("MainSurface")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        center_layout.addWidget(self.top_bar)
        center_layout.addWidget(self.toast)
        center_layout.addWidget(self.stack, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(center)
        splitter.addWidget(self.queue_panel)
        splitter.setSizes([220, 820, 280])
        splitter.setStretchFactor(1, 1)

        root_layout.addWidget(splitter, 1)
        root_layout.addWidget(self.player_bar)
        self.setCentralWidget(root)

        self._connect_signals()
        self._install_shortcuts()
        self.show_page("browse")
        self.refresh_catalog()
        self.refresh_local()
        self.refresh_playlists()

    def _connect_signals(self) -> None:
        self.sidebar.page_requested.connect(self.show_page)
        self.sidebar.playlist_requested.connect(self.show_playlist)

        self.top_bar.search_submitted.connect(self.search_catalog)

        self.browse_page.download_requested.connect(self.download_selected)
        self.browse_page.previous_page_requested.connect(self.previous_catalog_page)
        self.browse_page.next_page_requested.connect(self.next_catalog_page)

        self.downloads_page.add_to_playlist_requested.connect(self.add_local_to_playlist)
        self.downloads_page.refresh_requested.connect(self.refresh_local)
        self.downloads_page.table.track_clicked.connect(self.play_track_from_downloads)
        self.downloads_page.table.track_activated.connect(self.play_track_from_downloads)

        self.playlist_page.create_requested.connect(self.create_playlist)
        self.playlist_page.play_requested.connect(self.play_playlist)
        self.playlist_page.move_up_requested.connect(lambda: self.move_playlist_item(-1))
        self.playlist_page.move_down_requested.connect(lambda: self.move_playlist_item(1))
        self.playlist_page.remove_requested.connect(self.remove_playlist_item)
        self.playlist_page.table.track_activated.connect(self.play_playlist_from_track)

        self.upload_page.browse_requested.connect(self.choose_upload)
        self.upload_page.upload_requested.connect(self.upload_selected)

        self.player_bar.toggle_requested.connect(self.player.toggle)
        self.player_bar.stop_requested.connect(self.player.stop)
        self.player_bar.previous_requested.connect(self.player.previous)
        self.player_bar.next_requested.connect(self.player.next)
        self.player_bar.seek_requested.connect(self.player.seek)
        self.player_bar.shuffle_changed.connect(self.player.set_shuffle)
        self.player_bar.loop_changed.connect(self._change_loop)
        self.player_bar.queue_requested.connect(self.toggle_queue)
        self.queue_panel.row_requested.connect(self.play_queue_row)

        self.player.track_changed.connect(self._show_current_track)
        self.player.position_changed.connect(self.player_bar.set_position)
        self.player.duration_changed.connect(self.player_bar.set_duration)
        self.player.state_changed.connect(self.player_bar.set_state)
        self.player.error.connect(self._show_error)

    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence.Find, self, activated=self.top_bar.focus_search)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=lambda: self.show_page("downloads"))
        QShortcut(QKeySequence("Ctrl+U"), self, activated=lambda: self.show_page("upload"))
        QShortcut(QKeySequence("Ctrl+Right"), self, activated=self.player.next)
        QShortcut(QKeySequence("Ctrl+Left"), self, activated=self.player.previous)
        QShortcut(QKeySequence("Escape"), self, activated=self._escape)
        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self._space_toggle)

    def _space_toggle(self) -> None:
        focus = self.focusWidget()
        if focus and focus.metaObject().className() in {"QLineEdit", "QTextEdit", "QPlainTextEdit"}:
            return
        self.player.toggle()

    def _escape(self) -> None:
        if self.queue_panel.isVisible():
            self.queue_panel.setVisible(False)
        elif self.toast.isVisible():
            self.toast.hide()

    def run_task(self, task: Task, on_result=None, show_errors: bool = True) -> None:
        if on_result:
            task.signals.result.connect(on_result)
        if show_errors:
            task.signals.error.connect(self._show_error)
        self.pool.start(task)

    def show_page(self, page: str) -> None:
        if page not in self.pages:
            return
        self.current_page = page
        self.stack.setCurrentWidget(self.pages[page])
        self.sidebar.set_active_page(page)
        self.top_bar.set_title(PAGE_TITLES[page])
        self.top_bar.set_search_visible(page == "browse")
        if page == "downloads":
            self.refresh_local()
        elif page == "playlists":
            self.refresh_playlists()

    def show_playlist(self, playlist_id: int) -> None:
        self.current_playlist_id = playlist_id
        self.show_page("playlists")
        self.load_playlist_tracks_by_id(playlist_id)

    def search_catalog(self, query: str | None = None) -> None:
        self.catalog_offset = 0
        if query is not None:
            self.top_bar.search_input.setText(query)
        self.show_page("browse")
        self.refresh_catalog()

    def previous_catalog_page(self) -> None:
        self.catalog_offset = max(0, self.catalog_offset - self.catalog_limit)
        self.refresh_catalog()

    def next_catalog_page(self) -> None:
        if self.catalog_offset + self.catalog_limit < self.catalog_total:
            self.catalog_offset += self.catalog_limit
            self.refresh_catalog()

    def refresh_catalog(self) -> None:
        self._catalog_request_id += 1
        request_id = self._catalog_request_id
        self.browse_page.set_loading(True)
        task = Task(
            self.api.list_tracks,
            self.top_bar.search_text(),
            self.catalog_offset,
            self.catalog_limit,
        )
        task.signals.error.connect(
            lambda message, request_id=request_id: self._catalog_failed(message, request_id)
        )
        self.run_task(
            task,
            lambda page, request_id=request_id: self._catalog_loaded(page, request_id),
            show_errors=False,
        )

    def _catalog_failed(self, message: str, request_id: int) -> None:
        if request_id != self._catalog_request_id:
            return
        short = self._short_error(message)
        self.browse_page.set_error(short)
        self.toast.show_message(short, "error")

    def _catalog_loaded(self, page: dict, request_id: int) -> None:
        if request_id != self._catalog_request_id:
            return
        self.catalog_tracks = page["items"]
        self.catalog_total = page["total"]
        self.browse_page.set_page(
            self.catalog_tracks,
            self.catalog_total,
            self.catalog_offset,
            self.catalog_limit,
        )

    def download_selected(self) -> None:
        track = self.browse_page.selected_track()
        if not track:
            self.toast.show_message("Select a track first.", "info")
            return
        self.toast.show_message(f"Downloading {track['title']}...", "info", 60_000)
        task = Task(self.api.download_track, track)
        task.signals.progress.connect(
            lambda value: self.toast.show_message(f"Downloading... {value}%", "info", 60_000)
        )
        task.signals.result.connect(lambda path: self._download_complete(track, path))
        task.signals.finished.connect(lambda: None)
        self.run_task(task)

    def _download_complete(self, track: dict, path: Path) -> None:
        self.db.upsert_download(track, str(path))
        self.refresh_local()
        self.toast.show_message(f"Downloaded {track['title']}", "success")

    def refresh_local(self) -> None:
        removed = self.db.prune_missing_downloads()
        if removed:
            self.refresh_playlists()
            self.toast.show_message(f"Removed {removed} missing local file(s).", "info")
        self.local_tracks = self.db.list_downloads()
        self.downloads_page.set_tracks(self.local_tracks)

    def play_track_from_downloads(self, track: dict) -> None:
        index = self.local_tracks.index(track)
        self._set_playback_queue(self.local_tracks, index)

    def refresh_playlists(self) -> None:
        selected = self.current_playlist_id
        self.playlists = self.db.list_playlists()
        self.sidebar.set_playlists(self.playlists)
        self.sidebar.select_playlist(selected)
        if selected and any(playlist["id"] == selected for playlist in self.playlists):
            self.load_playlist_tracks_by_id(selected)
        elif not self.playlists:
            self.current_playlist_id = None
            self.playlist_tracks = []
            self.playlist_page.set_tracks(None, [])

    def create_playlist(self) -> None:
        name, ok = QInputDialog.getText(self, "New playlist", "Playlist name")
        if ok and name.strip():
            try:
                playlist_id = self.db.create_playlist(name)
                self.current_playlist_id = playlist_id
                self.toast.show_message(f"Created playlist {name.strip()}", "success")
            except Exception as exc:
                self._show_error(str(exc))
            self.refresh_playlists()

    def load_playlist_tracks_by_id(self, playlist_id: int) -> None:
        self.current_playlist_id = playlist_id
        playlist = next((item for item in self.playlists if item["id"] == playlist_id), None)
        self.playlist_tracks = self.db.list_playlist_tracks(playlist_id)
        self.playlist_page.set_tracks(playlist, self.playlist_tracks)
        self.sidebar.select_playlist(playlist_id)

    def add_local_to_playlist(self) -> None:
        track = self.downloads_page.selected_track()
        playlists = self.db.list_playlists()
        if not track:
            self.toast.show_message("Select a downloaded track first.", "info")
            return
        if not playlists:
            self.toast.show_message("Create a playlist first.", "info")
            return
        names = [p["name"] for p in playlists]
        name, ok = QInputDialog.getItem(self, "Add to playlist", "Playlist", names, 0, False)
        if ok:
            playlist = next(p for p in playlists if p["name"] == name)
            added = self.db.add_to_playlist(playlist["id"], track["server_id"])
            if not added:
                self.toast.show_message("This song is already in the playlist.", "info")
                return
            self.toast.show_message(f"Added to {name}", "success")
            self.current_playlist_id = playlist["id"]
            self.refresh_playlists()

    def play_playlist(self) -> None:
        if self.playlist_tracks:
            self._set_playback_queue(self.playlist_tracks, 0)
        else:
            self.toast.show_message("Playlist is empty.", "info")

    def play_playlist_from_track(self, track: dict) -> None:
        if track in self.playlist_tracks:
            self._set_playback_queue(self.playlist_tracks, self.playlist_tracks.index(track))

    def move_playlist_item(self, delta: int) -> None:
        track = self.playlist_page.selected_track()
        if track and self.current_playlist_id:
            self.db.move_playlist_item(self.current_playlist_id, track["server_id"], delta)
            self.load_playlist_tracks_by_id(self.current_playlist_id)

    def remove_playlist_item(self) -> None:
        track = self.playlist_page.selected_track()
        if track and self.current_playlist_id:
            self.db.remove_from_playlist(self.current_playlist_id, track["server_id"])
            self.load_playlist_tracks_by_id(self.current_playlist_id)
            self.refresh_playlists()
            self.toast.show_message("Removed from playlist.", "success")

    def choose_upload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose audio",
            "",
            "Audio (*.mp3 *.wav *.ogg *.m4a *.flac)",
        )
        if path:
            self.upload_page.set_path(path)

    def upload_selected(self) -> None:
        path = self.upload_page.selected_path()
        metadata = self.upload_page.metadata()
        if not path.is_file() or not metadata["title"] or not metadata["artist"]:
            self.toast.show_message("Choose a file and enter title and artist.", "error")
            return
        self.upload_page.set_uploading(True)
        self.toast.show_message("Uploading track...", "info", 60_000)
        task = Task(self.api.upload_track, path, metadata)
        task.signals.result.connect(self._upload_complete)
        task.signals.finished.connect(self._upload_finished)
        self.run_task(task)

    def _upload_finished(self) -> None:
        self.upload_page.set_uploading(False)

    def _upload_complete(self, track: dict) -> None:
        self.upload_page.set_complete()
        self.refresh_catalog()
        self.toast.show_message(f"Uploaded {track['title']}", "success")

    def _set_playback_queue(self, tracks: list[dict], index: int) -> None:
        self.current_queue = list(tracks)
        self.queue_panel.set_queue(self.current_queue, index)
        self.player.set_queue(self.current_queue, index)

    def play_queue_row(self, row: int) -> None:
        if 0 <= row < len(self.current_queue):
            self._set_playback_queue(self.current_queue, row)

    def toggle_queue(self) -> None:
        self.queue_panel.setVisible(not self.queue_panel.isVisible())

    def _show_current_track(self, track: dict) -> None:
        self.player_bar.set_track(track)
        index = -1
        for row, candidate in enumerate(self.current_queue):
            if candidate is track or (
                candidate.get("server_id") == track.get("server_id")
                and candidate.get("local_path") == track.get("local_path")
            ):
                index = row
                break
        self.queue_panel.set_queue(self.current_queue, index)

    def _change_loop(self, mode: str) -> None:
        self.player.loop_mode = mode

    def _show_error(self, message: str) -> None:
        self.toast.show_message(self._short_error(message), "error", 8000)

    @staticmethod
    def _short_error(message: str) -> str:
        return message.strip().splitlines()[-1] if message else "Unknown error"

    def shutdown(self) -> None:
        self.player.shutdown()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.shutdown()
        super().closeEvent(event)
