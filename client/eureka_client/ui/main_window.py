from __future__ import annotations

from pathlib import Path

from PySide2.QtCore import QAbstractTableModel, QModelIndex, QThreadPool, Qt
from PySide2.QtGui import QCloseEvent
from PySide2.QtMultimedia import QMediaPlayer
from PySide2.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSplitter,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from eureka_client.api import MusicAPI
from eureka_client.db import ClientDB
from eureka_client.player import PlaybackController
from eureka_client.workers.task import Task


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
    def __init__(self) -> None:
        super().__init__()
        self.model_data = TrackTableModel()
        self.setModel(self.model_data)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2, 3):
            header.setSectionResizeMode(column, QHeaderView.Interactive)
        self.setColumnWidth(1, 220)
        self.setColumnWidth(2, 220)
        self.setColumnWidth(3, 120)
        self.verticalHeader().setVisible(False)

    def set_tracks(self, tracks: list[dict]) -> None:
        self.model_data.replace_tracks(tracks)

    def selected_track(self) -> dict | None:
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model_data.tracks[row] if 0 <= row < len(self.model_data.tracks) else None


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Eureka Music")
        self.resize(1050, 720)

        self.api = MusicAPI()
        self.db = ClientDB()
        self.player = PlaybackController()
        self.pool = QThreadPool.globalInstance()
        self.catalog_tracks: list[dict] = []
        self.catalog_offset = 0
        self.catalog_limit = 500
        self.catalog_total = 0
        self.local_tracks: list[dict] = []
        self.current_playlist_id: int | None = None

        root = QWidget()
        root_layout = QVBoxLayout(root)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._catalog_tab(), "Server catalog")
        self.tabs.addTab(self._local_tab(), "Downloaded")
        self.tabs.addTab(self._playlists_tab(), "Playlists")
        self.tabs.addTab(self._upload_tab(), "Upload")
        root_layout.addWidget(self.tabs, 1)
        root_layout.addWidget(self._player_bar())
        self.setCentralWidget(root)

        self.player.track_changed.connect(self._show_current_track)
        self.player.position_changed.connect(self._update_position)
        self.player.duration_changed.connect(self.seek_slider.setMaximum)
        self.player.state_changed.connect(self._update_play_button)
        self.player.error.connect(self._show_error)

        self.refresh_catalog()
        self.refresh_local()
        self.refresh_playlists()

    def _catalog_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search title, artist, or album")
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_catalog)
        self.search_input.returnPressed.connect(self.search_catalog)
        self.catalog_status = QLabel()
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(search_button)
        search_row.addWidget(self.catalog_status)

        self.catalog_table = TrackTable()
        download = QPushButton("Download selected")
        download.clicked.connect(self.download_selected)
        page_row = QHBoxLayout()
        self.catalog_previous = QPushButton("Previous page")
        self.catalog_previous.clicked.connect(self.previous_catalog_page)
        self.catalog_next = QPushButton("Next page")
        self.catalog_next.clicked.connect(self.next_catalog_page)
        page_row.addWidget(download)
        page_row.addStretch()
        page_row.addWidget(self.catalog_previous)
        page_row.addWidget(self.catalog_next)
        layout.addLayout(search_row)
        layout.addWidget(self.catalog_table, 1)
        layout.addLayout(page_row)
        return tab

    def _local_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.local_table = TrackTable()
        controls = QHBoxLayout()
        play = QPushButton("Play selected")
        play.clicked.connect(self.play_local_selected)
        add = QPushButton("Add to playlist")
        add.clicked.connect(self.add_local_to_playlist)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_local)
        controls.addWidget(play)
        controls.addWidget(add)
        controls.addStretch()
        controls.addWidget(refresh)
        layout.addWidget(self.local_table, 1)
        layout.addLayout(controls)
        return tab

    def _playlists_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        splitter = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.playlist_list = QListWidget()
        self.playlist_list.currentRowChanged.connect(self.load_playlist_tracks)
        create = QPushButton("Create playlist")
        create.clicked.connect(self.create_playlist)
        left_layout.addWidget(self.playlist_list, 1)
        left_layout.addWidget(create)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.playlist_table = TrackTable()
        controls = QHBoxLayout()
        play = QPushButton("Play playlist")
        play.clicked.connect(self.play_playlist)
        up = QPushButton("Move up")
        up.clicked.connect(lambda: self.move_playlist_item(-1))
        down = QPushButton("Move down")
        down.clicked.connect(lambda: self.move_playlist_item(1))
        remove = QPushButton("Remove")
        remove.clicked.connect(self.remove_playlist_item)
        controls.addWidget(play)
        controls.addWidget(up)
        controls.addWidget(down)
        controls.addWidget(remove)
        right_layout.addWidget(self.playlist_table, 1)
        right_layout.addLayout(controls)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        return tab

    def _upload_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        self.upload_path = QLineEdit()
        browse = QPushButton("Browse")
        browse.clicked.connect(self.choose_upload)
        file_row = QHBoxLayout()
        file_row.addWidget(self.upload_path, 1)
        file_row.addWidget(browse)
        file_widget = QWidget()
        file_widget.setLayout(file_row)

        self.upload_title = QLineEdit()
        self.upload_artist = QLineEdit()
        self.upload_album = QLineEdit()
        self.upload_genre = QLineEdit()
        upload = QPushButton("Upload to server")
        upload.clicked.connect(self.upload_selected)
        self.upload_progress = QProgressBar()
        self.upload_progress.setRange(0, 1)
        self.upload_progress.setValue(0)

        form.addRow("Audio file", file_widget)
        form.addRow("Title", self.upload_title)
        form.addRow("Artist", self.upload_artist)
        form.addRow("Album", self.upload_album)
        form.addRow("Genre", self.upload_genre)
        form.addRow(upload)
        form.addRow(self.upload_progress)
        return tab

    def _player_bar(self) -> QWidget:
        bar = QWidget()
        layout = QVBoxLayout(bar)
        self.now_playing = QLabel("Nothing playing")
        top = QHBoxLayout()
        previous = QPushButton("Previous")
        previous.clicked.connect(self.player.previous)
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.player.toggle)
        stop = QPushButton("Stop")
        stop.clicked.connect(self.player.stop)
        next_button = QPushButton("Next")
        next_button.clicked.connect(self.player.next)
        self.shuffle_combo = QComboBox()
        self.shuffle_combo.addItems(["Ordered", "Shuffle"])
        self.shuffle_combo.currentIndexChanged.connect(
            lambda index: self.player.set_shuffle(bool(index))
        )
        self.loop_combo = QComboBox()
        self.loop_combo.addItems(["Loop off", "Loop one", "Loop all"])
        self.loop_combo.currentIndexChanged.connect(self._change_loop)
        top.addWidget(previous)
        top.addWidget(self.play_button)
        top.addWidget(stop)
        top.addWidget(next_button)
        top.addWidget(self.shuffle_combo)
        top.addWidget(self.loop_combo)
        top.addStretch()
        self.time_label = QLabel("00:00 / 00:00")
        top.addWidget(self.time_label)

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.sliderReleased.connect(
            lambda: self.player.seek(self.seek_slider.value())
        )
        layout.addWidget(self.now_playing)
        layout.addLayout(top)
        layout.addWidget(self.seek_slider)
        return bar

    def run_task(self, task: Task, on_result=None, show_errors: bool = True) -> None:
        if on_result:
            task.signals.result.connect(on_result)
        if show_errors:
            task.signals.error.connect(self._show_error)
        self.pool.start(task)

    def search_catalog(self) -> None:
        self.catalog_offset = 0
        self.refresh_catalog()

    def previous_catalog_page(self) -> None:
        self.catalog_offset = max(0, self.catalog_offset - self.catalog_limit)
        self.refresh_catalog()

    def next_catalog_page(self) -> None:
        if self.catalog_offset + self.catalog_limit < self.catalog_total:
            self.catalog_offset += self.catalog_limit
            self.refresh_catalog()

    def refresh_catalog(self) -> None:
        self.catalog_status.setText("Loading…")
        self.catalog_previous.setEnabled(False)
        self.catalog_next.setEnabled(False)
        task = Task(
            self.api.list_tracks,
            self.search_input.text().strip(),
            self.catalog_offset,
            self.catalog_limit,
        )
        task.signals.error.connect(self._catalog_failed)
        self.run_task(task, self._catalog_loaded, show_errors=False)

    def _catalog_failed(self, message: str) -> None:
        self.catalog_status.setText("Server unavailable")
        short = message.strip().splitlines()[-1] if message else "Unknown error"
        self.statusBar().showMessage(short, 8000)
        self.catalog_previous.setEnabled(self.catalog_offset > 0)
        self.catalog_next.setEnabled(
            self.catalog_offset + self.catalog_limit < self.catalog_total
        )

    def _catalog_loaded(self, page: dict) -> None:
        self.catalog_tracks = page["items"]
        self.catalog_total = page["total"]
        self.catalog_table.set_tracks(self.catalog_tracks)
        start = self.catalog_offset + 1 if self.catalog_total else 0
        end = self.catalog_offset + len(self.catalog_tracks)
        self.catalog_status.setText(f"{start}-{end} of {self.catalog_total}")
        self.catalog_previous.setEnabled(self.catalog_offset > 0)
        self.catalog_next.setEnabled(end < self.catalog_total)

    def download_selected(self) -> None:
        track = self.catalog_table.selected_track()
        if not track:
            QMessageBox.information(self, "Download", "Select a track first.")
            return
        self.statusBar().showMessage(f"Downloading {track['title']}…")
        task = Task(self.api.download_track, track)
        task.signals.progress.connect(lambda value: self.statusBar().showMessage(f"Downloading… {value}%"))
        task.signals.result.connect(lambda path: self._download_complete(track, path))
        task.signals.finished.connect(lambda: self.statusBar().clearMessage())
        self.run_task(task)

    def _download_complete(self, track: dict, path: Path) -> None:
        self.db.upsert_download(track, str(path))
        self.refresh_local()
        QMessageBox.information(self, "Download", f"Saved to {path}")

    def refresh_local(self) -> None:
        removed = self.db.prune_missing_downloads()
        if removed:
            self.refresh_playlists()
            self.statusBar().showMessage(f"Removed {removed} missing local file(s).", 8000)
        self.local_tracks = self.db.list_downloads()
        self.local_table.set_tracks(self.local_tracks)

    def play_local_selected(self) -> None:
        track = self.local_table.selected_track()
        if track:
            index = self.local_tracks.index(track)
            self.player.set_queue(self.local_tracks, index)

    def refresh_playlists(self) -> None:
        self.playlists = self.db.list_playlists()
        self.playlist_list.clear()
        for playlist in self.playlists:
            self.playlist_list.addItem(f"{playlist['name']} ({playlist['track_count']})")
        if self.playlists:
            self.playlist_list.setCurrentRow(0)

    def create_playlist(self) -> None:
        name, ok = QInputDialog.getText(self, "New playlist", "Playlist name")
        if ok and name.strip():
            try:
                self.db.create_playlist(name)
            except Exception as exc:
                self._show_error(str(exc))
            self.refresh_playlists()

    def load_playlist_tracks(self, row: int) -> None:
        if row < 0 or row >= len(getattr(self, "playlists", [])):
            self.current_playlist_id = None
            self.playlist_tracks = []
        else:
            self.current_playlist_id = self.playlists[row]["id"]
            self.playlist_tracks = self.db.list_playlist_tracks(self.current_playlist_id)
        self.playlist_table.set_tracks(self.playlist_tracks)

    def add_local_to_playlist(self) -> None:
        track = self.local_table.selected_track()
        playlists = self.db.list_playlists()
        if not track:
            QMessageBox.information(self, "Playlist", "Select a downloaded track first.")
            return
        if not playlists:
            QMessageBox.information(self, "Playlist", "Create a playlist first.")
            return
        names = [p["name"] for p in playlists]
        name, ok = QInputDialog.getItem(self, "Add to playlist", "Playlist", names, 0, False)
        if ok:
            playlist = next(p for p in playlists if p["name"] == name)
            added = self.db.add_to_playlist(playlist["id"], track["server_id"])
            if not added:
                QMessageBox.information(
                    self,
                    "Playlist",
                    "This song is already in the playlist.",
                )
                return
            self.refresh_playlists()

    def play_playlist(self) -> None:
        if getattr(self, "playlist_tracks", None):
            self.player.set_queue(self.playlist_tracks, 0)

    def move_playlist_item(self, delta: int) -> None:
        track = self.playlist_table.selected_track()
        if track and self.current_playlist_id:
            self.db.move_playlist_item(self.current_playlist_id, track["server_id"], delta)
            self.load_playlist_tracks(self.playlist_list.currentRow())

    def remove_playlist_item(self) -> None:
        track = self.playlist_table.selected_track()
        if track and self.current_playlist_id:
            self.db.remove_from_playlist(self.current_playlist_id, track["server_id"])
            self.load_playlist_tracks(self.playlist_list.currentRow())
            self.refresh_playlists()

    def choose_upload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose audio",
            "",
            "Audio (*.mp3 *.wav *.ogg *.m4a *.flac)",
        )
        if path:
            self.upload_path.setText(path)
            if not self.upload_title.text():
                self.upload_title.setText(Path(path).stem)

    def upload_selected(self) -> None:
        path = Path(self.upload_path.text())
        if not path.is_file() or not self.upload_title.text().strip() or not self.upload_artist.text().strip():
            QMessageBox.warning(self, "Upload", "Choose a file and enter title and artist.")
            return
        metadata = {
            "title": self.upload_title.text().strip(),
            "artist": self.upload_artist.text().strip(),
            "album": self.upload_album.text().strip(),
            "genre": self.upload_genre.text().strip(),
        }
        self.upload_progress.setRange(0, 0)
        task = Task(self.api.upload_track, path, metadata)
        task.signals.result.connect(self._upload_complete)
        task.signals.finished.connect(self._upload_finished)
        self.run_task(task)

    def _upload_finished(self) -> None:
        if self.upload_progress.maximum() == 0:
            self.upload_progress.setRange(0, 1)
            self.upload_progress.setValue(0)

    def _upload_complete(self, track: dict) -> None:
        self.upload_progress.setRange(0, 1)
        self.upload_progress.setValue(1)
        self.refresh_catalog()
        QMessageBox.information(self, "Upload", f"Uploaded {track['title']}")

    def _show_current_track(self, track: dict) -> None:
        self.now_playing.setText(f"{track['title']} — {track['artist']}")

    def _update_position(self, position: int) -> None:
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(position)
        duration = self.seek_slider.maximum()
        self.time_label.setText(f"{self._format_ms(position)} / {self._format_ms(duration)}")

    def _update_play_button(self, state: int) -> None:
        self.play_button.setText("Pause" if state == QMediaPlayer.PlayingState else "Play")

    def _change_loop(self, index: int) -> None:
        self.player.loop_mode = ["off", "one", "all"][index]

    @staticmethod
    def _format_ms(value: int) -> str:
        seconds = max(0, value // 1000)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _show_error(self, message: str) -> None:
        short = message.strip().splitlines()[-1] if message else "Unknown error"
        QMessageBox.critical(self, "Eureka Music error", short)

    def shutdown(self) -> None:
        self.player.shutdown()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.shutdown()
        super().closeEvent(event)
