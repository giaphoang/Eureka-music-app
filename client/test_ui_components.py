from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide2.QtWidgets import QApplication, QLabel, QPushButton

from eureka_client.ui.components.player_bar import PlayerBar
from eureka_client.ui.components.queue_panel import QueuePanel
from eureka_client.ui.components.sidebar import Sidebar
from eureka_client.ui.components.track_table import TrackTable
from eureka_client.ui.pages.downloads_page import DownloadsPage
from eureka_client.ui.pages.recommendation_page import RecommendationPage


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
    sidebar._buttons["recommendations"].click()
    sidebar.playlist_list.setCurrentRow(0)
    sidebar.set_active_page("downloads")

    assert pages == ["downloads", "recommendations"]
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


def test_track_table_click_and_activation_are_separate_signals() -> None:
    app()
    table = TrackTable()
    track = {"server_id": 1, "title": "Song", "artist": "Artist"}
    clicked: list[dict] = []
    activated: list[dict] = []
    table.track_clicked.connect(clicked.append)
    table.track_activated.connect(activated.append)
    table.set_tracks([track])
    index = table.model_data.index(0, 0)

    table._click_index(index)

    assert clicked == [track]
    assert activated == []

    table._activate_index(index)

    assert activated == [track]


def test_downloads_page_has_no_play_selected_button() -> None:
    app()
    page = DownloadsPage()

    button_texts = [button.text() for button in page.findChildren(QPushButton)]

    assert "Play selected" not in button_texts
    assert "Add to playlist" in button_texts
    assert "Refresh" in button_texts


def test_recommendation_page_emits_prompt_size_and_uses_table_model() -> None:
    app()
    page = RecommendationPage()
    requests: list[tuple[str, int]] = []
    page.generate_requested.connect(lambda prompt, size: requests.append((prompt, size)))
    page.prompt_input.setPlainText("  dreamy   electronic focus  ")
    page.size_input.setValue(5)

    page.generate_button.click()
    page.set_tracks(
        [
            {
                "position": 1,
                "title": "Song",
                "artist": "Artist",
                "album": None,
                "genre": "Electronic",
                "prompt_similarity": 0.91,
            }
        ]
    )

    assert requests == [("dreamy electronic focus", 5)]
    assert page.model_data.rowCount() == 1
    assert page.model_data.data(page.model_data.index(0, 5)) == "0.91"
