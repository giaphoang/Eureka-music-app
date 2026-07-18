from __future__ import annotations

from PySide2.QtCore import QEvent, QPoint, QSize, Qt, QPropertyAnimation, Signal
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from eureka_client.ui.theme import icon_path


class SidebarPlaylistRow(QWidget):
    menu_requested = Signal(dict, object)

    def __init__(self, playlist: dict) -> None:
        super().__init__()
        self.playlist = playlist
        self.setObjectName("SidebarPlaylistRow")
        self.setMouseTracking(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(6)

        self.title = QLabel(f"{playlist['name']} ({playlist['track_count']})")
        self.title.setObjectName("SidebarPlaylistTitle")
        self.title.setTextInteractionFlags(Qt.NoTextInteraction)
        self.menu_button = QToolButton()
        self.menu_button.setObjectName("SidebarPlaylistOverflowButton")
        self.menu_button.setText("•••")
        self.menu_button.setAccessibleName(f"More options for {playlist['name']}")
        self.menu_button.setToolTip("More options")
        self.menu_button.setFocusPolicy(Qt.TabFocus)
        self.menu_button.installEventFilter(self)
        self.menu_button.clicked.connect(lambda _checked=False: self.menu_requested.emit(self.playlist, self.menu_button))

        self._opacity = QGraphicsOpacityEffect(self.menu_button)
        self._opacity.setOpacity(0.0)
        self.menu_button.setGraphicsEffect(self._opacity)
        self._animation = QPropertyAnimation(self._opacity, b"opacity", self)
        self._animation.setDuration(120)
        self._menu_open = False

        layout.addWidget(self.title, 1)
        layout.addWidget(self.menu_button)

    def set_menu_open(self, open_: bool) -> None:
        self._menu_open = open_
        self._set_button_visible(open_ or self.underMouse() or self.menu_button.hasFocus())

    def enterEvent(self, event) -> None:  # noqa: N802
        self._set_button_visible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._set_button_visible(self._menu_open or self.menu_button.hasFocus())
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802
        self._set_button_visible(True)
        super().focusInEvent(event)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.menu_button:
            if event.type() in {QEvent.Enter, QEvent.FocusIn}:
                self._set_button_visible(True)
            elif event.type() in {QEvent.Leave, QEvent.FocusOut}:
                self._set_button_visible(self._menu_open or self.underMouse())
        return super().eventFilter(watched, event)

    def _set_button_visible(self, visible: bool) -> None:
        self.menu_button.setProperty("active", visible)
        self.menu_button.style().unpolish(self.menu_button)
        self.menu_button.style().polish(self.menu_button)
        self._animation.stop()
        self._animation.setStartValue(self._opacity.opacity())
        self._animation.setEndValue(1.0 if visible else 0.0)
        self._animation.start()


class Sidebar(QWidget):
    page_requested = Signal(str)
    playlist_requested = Signal(int)
    playlist_delete_requested = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        self._buttons: dict[str, QPushButton] = {}
        self._playlists: list[dict] = []
        self._playlist_rows: dict[int, SidebarPlaylistRow] = {}
        self._playlist_menu: QMenu | None = None
        self._playlist_menu_row: SidebarPlaylistRow | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        brand = QLabel("Eureka Music")
        brand.setProperty("role", "brand")
        layout.addWidget(brand)

        self._add_nav(layout, "browse", "Browse", "home")
        self._add_nav(layout, "downloads", "Downloads", "download")
        self._add_nav(layout, "playlists", "Playlists", "list-music")
        self._add_nav(layout, "recommendations", "AI Playlist", "list")
        self._add_nav(layout, "upload", "Upload", "upload")

        label = QLabel("Playlists")
        label.setProperty("role", "sectionLabel")
        layout.addWidget(label)

        self.playlist_list = QListWidget()
        self.playlist_list.setObjectName("SidebarPlaylistList")
        self.playlist_list.currentRowChanged.connect(self._playlist_row_changed)
        self.playlist_list.viewport().installEventFilter(self)
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
        self.close_playlist_menu()
        for key, button in self._buttons.items():
            button.setChecked(key == page)

    def set_playlists(self, playlists: list[dict]) -> None:
        self.close_playlist_menu()
        self._playlists = playlists
        self._playlist_rows = {}
        self.playlist_list.blockSignals(True)
        self.playlist_list.clear()
        for playlist in playlists:
            row_widget = SidebarPlaylistRow(playlist)
            row_widget.menu_requested.connect(self._open_playlist_menu)
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 34))
            item.setData(32, playlist["id"])
            self.playlist_list.addItem(item)
            self.playlist_list.setItemWidget(item, row_widget)
            self._playlist_rows[int(playlist["id"])] = row_widget
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
        self.close_playlist_menu()
        if 0 <= row < len(self._playlists):
            self.playlist_requested.emit(int(self._playlists[row]["id"]))

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.playlist_list.viewport() and event.type() == QEvent.Wheel:
            self.close_playlist_menu()
        return super().eventFilter(watched, event)

    def close_playlist_menu(self) -> None:
        if self._playlist_menu:
            self._playlist_menu.close()
            self._playlist_menu = None
        if self._playlist_menu_row:
            self._playlist_menu_row.set_menu_open(False)
            self._playlist_menu_row = None

    def _open_playlist_menu(self, playlist: dict, button: QToolButton) -> None:
        self.close_playlist_menu()
        row = self._playlist_rows.get(int(playlist["id"]))
        if row:
            row.set_menu_open(True)
        menu = QMenu(self)
        menu.setObjectName("SidebarPlaylistMenu")
        action = menu.addAction(self.style().standardIcon(QStyle.SP_TrashIcon), "Delete playlist")
        action.triggered.connect(lambda _checked=False, playlist_id=int(playlist["id"]): self._delete_playlist(playlist_id))
        menu.aboutToHide.connect(self._playlist_menu_closed)
        self._playlist_menu = menu
        self._playlist_menu_row = row
        global_position = button.mapToGlobal(QPoint(0, button.height()))
        menu.popup(self._bounded_menu_position(menu, global_position))

    def _delete_playlist(self, playlist_id: int) -> None:
        self.playlist_delete_requested.emit(playlist_id)
        self.close_playlist_menu()

    def _playlist_menu_closed(self) -> None:
        row = self._playlist_menu_row
        button = row.menu_button if row else None
        self._playlist_menu = None
        self._playlist_menu_row = None
        if row:
            row.set_menu_open(False)
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
