from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide2.QtWidgets import QApplication, QLabel

from eureka_client.ui.components.player_bar import PlayerBar
from eureka_client.ui.components.queue_panel import QueuePanel
from eureka_client.ui.components.sidebar import Sidebar


def app() -> QApplication:
    instance = QApplication.instance()
    return instance or QApplication([])


def test_sidebar_navigation_and_playlist_signals() -> None:
    app()
    sidebar = Sidebar()
    pages: list[str] = []
    playlists: list[int] = []
    sidebar.page_requested.connect(pages.append)
    sidebar.playlist_requested.connect(playlists.append)
    sidebar.set_playlists([{"id": 7, "name": "Road", "track_count": 3}])

    sidebar._buttons["downloads"].click()
    sidebar.playlist_list.setCurrentRow(0)
    sidebar.set_active_page("downloads")

    assert pages == ["downloads"]
    assert playlists == [7]
    assert sidebar._buttons["downloads"].isChecked() is True
    assert sidebar._buttons["browse"].isChecked() is False


def test_player_bar_emits_controls_and_avoids_seek_feedback_loop() -> None:
    app()
    bar = PlayerBar()
    toggles: list[bool] = []
    seeks: list[int] = []
    shuffles: list[bool] = []
    loops: list[str] = []
    bar.toggle_requested.connect(lambda: toggles.append(True))
    bar.seek_requested.connect(seeks.append)
    bar.shuffle_changed.connect(shuffles.append)
    bar.loop_changed.connect(loops.append)

    bar.set_duration(10_000)
    bar.set_position(5_000)
    bar.play_button.click()
    bar.shuffle_button.click()
    bar.loop_button.click()
    bar.seek_slider.setValue(7_000)
    bar.seek_slider.sliderReleased.emit()

    assert toggles == [True]
    assert shuffles == [True]
    assert loops == ["one"]
    assert seeks == [7_000]


def test_queue_panel_uses_model_view_for_large_queue() -> None:
    app()
    panel = QueuePanel()
    tracks = [
        {"server_id": index, "title": f"Track {index}", "artist": "Artist"}
        for index in range(8000)
    ]

    panel.set_queue(tracks, 42)

    assert panel.table.model_data.rowCount() == 8000
    assert panel.table.selected_row() == 42
    assert len(panel.findChildren(QLabel)) < 10
