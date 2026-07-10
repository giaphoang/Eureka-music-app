from __future__ import annotations

from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from eureka_client.ui.theme import icon_path


class Sidebar(QWidget):
    page_requested = Signal(str)
    playlist_requested = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        self._buttons: dict[str, QPushButton] = {}
        self._playlists: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        brand = QLabel("Eureka Music")
        brand.setProperty("role", "brand")
        layout.addWidget(brand)

        self._add_nav(layout, "browse", "Browse", "home")
        self._add_nav(layout, "downloads", "Downloads", "download")
        self._add_nav(layout, "playlists", "Playlists", "list-music")
        self._add_nav(layout, "upload", "Upload", "upload")

        label = QLabel("Playlists")
        label.setProperty("role", "sectionLabel")
        layout.addWidget(label)

        self.playlist_list = QListWidget()
        self.playlist_list.setObjectName("SidebarPlaylistList")
        self.playlist_list.currentRowChanged.connect(self._playlist_row_changed)
        layout.addWidget(self.playlist_list, 1)
        layout.addStretch()
        self.set_active_page("browse")

    def _add_nav(self, layout: QVBoxLayout, page: str, text: str, icon: str) -> None:
        button = QPushButton(QIcon(icon_path(icon)), text)
        button.setProperty("role", "nav")
        button.setCheckable(True)
        button.setToolTip(text)
        button.setAccessibleName(text)
        button.clicked.connect(lambda checked=False, page=page: self.page_requested.emit(page))
        self._buttons[page] = button
        layout.addWidget(button)

    def set_active_page(self, page: str) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == page)

    def set_playlists(self, playlists: list[dict]) -> None:
        self._playlists = playlists
        self.playlist_list.blockSignals(True)
        self.playlist_list.clear()
        for playlist in playlists:
            item = QListWidgetItem(f"{playlist['name']} ({playlist['track_count']})")
            item.setData(32, playlist["id"])
            self.playlist_list.addItem(item)
        self.playlist_list.blockSignals(False)

    def select_playlist(self, playlist_id: int | None) -> None:
        self.playlist_list.blockSignals(True)
        if playlist_id is None:
            self.playlist_list.setCurrentRow(-1)
        else:
            for row, playlist in enumerate(self._playlists):
                if playlist["id"] == playlist_id:
                    self.playlist_list.setCurrentRow(row)
                    break
        self.playlist_list.blockSignals(False)

    def _playlist_row_changed(self, row: int) -> None:
        if 0 <= row < len(self._playlists):
            self.playlist_requested.emit(int(self._playlists[row]["id"]))
