from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide2.QtCore import QEvent, Qt
from PySide2.QtGui import QKeyEvent
from PySide2.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton

from eureka_client.ui.components.player_bar import PlayerBar
from eureka_client.ui.components.queue_panel import QueuePanel
from eureka_client.ui.components.sidebar import Sidebar
from eureka_client.ui.components.track_table import TrackTable
from eureka_client.ui.components.top_bar import TopBar
from eureka_client.ui import main_window as main_window_module
from eureka_client.ui.pages.browse_page import BrowsePage
from eureka_client.ui.pages.downloads_page import DownloadsPage
from eureka_client.ui.pages.playlist_page import PlaylistPage
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


def test_sidebar_playlist_overflow_menu_requests_delete() -> None:
    app_instance = app()
    sidebar = Sidebar()
    deleted: list[int] = []
    sidebar.playlist_delete_requested.connect(deleted.append)
    sidebar.set_playlists(
        [
            {"id": 7, "name": "Road", "track_count": 3},
            {"id": 8, "name": "Night", "track_count": 2},
        ]
    )
    sidebar.resize(240, 320)
    sidebar.show()
    app_instance.processEvents()

    row = sidebar._playlist_rows[7]
    assert row.menu_button.accessibleName() == "More options for Road"
    assert row.menu_button.focusPolicy() == Qt.TabFocus

    row.menu_button.click()
    assert sidebar._playlist_menu is not None
    assert [action.text() for action in sidebar._playlist_menu.actions()] == ["Delete playlist"]

    first_menu = sidebar._playlist_menu
    sidebar._playlist_rows[8].menu_button.click()
    assert sidebar._playlist_menu is not first_menu
    assert sidebar._playlist_menu_row is sidebar._playlist_rows[8]

    sidebar._playlist_menu.actions()[0].trigger()
    assert deleted == [8]
    assert sidebar._playlist_menu is None


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


def test_track_table_overflow_visibility_depends_only_on_row_hover() -> None:
    app()
    table = TrackTable()
    table.set_overflow_enabled(True)
    table.set_tracks(
        [
            {"server_id": 1, "title": "Song", "artist": "Artist"},
            {"server_id": 2, "title": "Other", "artist": "Artist"},
        ]
    )
    first = table._overflow_buttons[0]
    second = table._overflow_buttons[1]

    table.set_overflow_menu_row(0)
    first.setFocus()
    table._update_overflow_visibility(0)

    assert first.property("active") is False

    table._set_hovered_row(0)
    assert first.property("active") is True
    assert second.property("active") is False

    table._set_hovered_row(1)
    assert first.property("active") is False
    assert first.graphicsEffect().opacity() == 0.0
    assert second.property("active") is True

    table._set_hovered_row(-1)
    assert second.property("active") is False
    assert second.graphicsEffect().opacity() == 0.0


def test_downloads_page_uses_row_overflow_add_to_playlist_menu() -> None:
    app_instance = app()
    page = DownloadsPage()
    track = {"server_id": 1, "title": "Song", "artist": "Artist"}
    added: list[tuple[dict, int]] = []
    created: list[dict] = []
    page.add_track_to_playlist_requested.connect(lambda track, playlist_id: added.append((track, playlist_id)))
    page.create_playlist_with_track_requested.connect(created.append)
    page.set_playlists(
        [
            {"id": 7, "name": "Road", "track_count": 3},
            {"id": 8, "name": "Night", "track_count": 2},
        ]
    )
    page.set_tracks([track])
    page.table.resize(640, 160)
    page.table.show()
    app_instance.processEvents()

    button_texts = [button.text() for button in page.findChildren(QPushButton)]
    overflow = page.table._overflow_buttons[0]
    overflow.click()

    assert "Play selected" not in button_texts
    assert "Add to playlist" not in button_texts
    assert "Refresh" not in button_texts
    assert page._track_menu is not None
    assert [action.text() for action in page._track_menu.actions()] == ["Add to playlist"]
    assert page._track_menu.actions()[0].icon().isNull() is True

    submenu = page._track_menu.actions()[0].menu()
    assert submenu is not None
    assert [action.text() for action in submenu.actions()[1:]] == ["New playlist", "", "Road", "Night", "No playlists found"]
    assert submenu.actions()[-1].isVisible() is False

    search = submenu.findChild(QLineEdit)
    assert search is not None
    assert search.placeholderText() == "Find a playlist"
    search.setText("nig")
    assert submenu.actions()[3].isVisible() is False
    assert submenu.actions()[4].isVisible() is True

    submenu.actions()[4].trigger()
    assert added == [(track, 8)]
    assert page._track_menu is None

    overflow.click()
    submenu = page._track_menu.actions()[0].menu()
    submenu.actions()[1].trigger()
    assert created == [track]
    assert page._track_menu is None


def test_downloads_page_search_filters_downloaded_songs_only() -> None:
    app()
    page = DownloadsPage()
    page.set_tracks(
        [
            {"server_id": 1, "title": "Pepper", "artist": "Artist", "album": "Album"},
            {"server_id": 2, "title": "Focus", "artist": "Coder", "album": "Dream State"},
        ]
    )

    page.set_search_query(" dream ")

    assert page.table.model_data.rowCount() == 1
    assert page.table.model_data.tracks[0]["server_id"] == 2

    page.set_search_query("missing")
    assert page.table.model_data.rowCount() == 0
    assert page.empty.title.text() == "No downloaded songs found"


def test_browse_page_uses_hover_download_row_buttons() -> None:
    app()
    page = BrowsePage()
    track = {"server_id": 1, "title": "Song", "artist": "Artist"}
    downloads: list[dict] = []
    page.download_track_requested.connect(downloads.append)
    page.set_page([track], total=1, offset=0, limit=500)

    button_texts = [button.text() for button in page.findChildren(QPushButton)]
    overflow = page.table._overflow_buttons[0]
    overflow.click()

    assert "Download selected" not in button_texts
    assert page.table.model_data.columnCount() == 5
    assert overflow.accessibleName() == "Download Song"
    assert downloads == [track]


def test_browse_page_exposes_previous_and_next_pagination_buttons() -> None:
    app()
    page = BrowsePage()
    track = {"server_id": 1, "title": "Song", "artist": "Artist"}
    previous_requests: list[bool] = []
    next_requests: list[bool] = []
    page.previous_page_requested.connect(lambda: previous_requests.append(True))
    page.next_page_requested.connect(lambda: next_requests.append(True))

    page.set_page([track], total=12, offset=0, limit=1)

    assert page.previous_button.accessibleName() == "Previous browse page"
    assert page.next_button.accessibleName() == "Next browse page"
    assert page.previous_button.isEnabled() is False
    assert page.next_button.isEnabled() is True

    page.next_button.click()
    assert next_requests == [True]

    page.set_page([track], total=12, offset=11, limit=1)

    assert page.previous_button.isEnabled() is True
    assert page.next_button.isEnabled() is False

    page.previous_button.click()
    assert previous_requests == [True]


def test_top_bar_hides_search_button_with_input_and_has_no_nav_chevrons() -> None:
    app()
    top_bar = TopBar()

    top_bar.set_search_visible(False)

    assert top_bar.search_input.isHidden() is True
    assert top_bar.search_button.isHidden() is True
    assert top_bar.layout().indexOf(top_bar.back_button) == -1
    assert top_bar.layout().indexOf(top_bar.forward_button) == -1


def test_playlist_page_hero_hides_move_buttons_and_emits_cover_and_row_click() -> None:
    app()
    page = PlaylistPage()
    track = {"server_id": 1, "title": "Song", "artist": "Artist", "duration_ms": 120_000}
    clicked: list[dict] = []
    cover_requests: list[bool] = []
    play_requests: list[bool] = []
    page.table.track_clicked.connect(clicked.append)
    page.cover_requested.connect(lambda: cover_requests.append(True))
    page.primary_play_requested.connect(lambda: play_requests.append(True))
    assert page.play_button.isEnabled() is False
    page.set_tracks({"id": 4, "name": "Mix"}, [track])

    button_texts = [button.text() for button in page.findChildren(QPushButton)]
    page.cover.click()
    page.play_button.click()
    page.table._click_index(page.table.model_data.index(0, 0))

    assert page.title.text() == "Mix"
    assert page.kind.text() == "Playlist"
    assert page.meta.text() == "1 song · 2 min"
    assert "Move up" not in button_texts
    assert "Move down" not in button_texts
    assert page.play_button.text() == ""
    assert page.play_button.objectName() == "PlaylistPlayButton"
    assert page.play_button.accessibleName() == "Play playlist"
    assert page.play_button.isEnabled() is True
    assert "Remove" not in button_texts
    assert cover_requests == [True]
    assert play_requests == [True]
    assert clicked == [track]


def test_playlist_page_overflow_menu_removes_track_association() -> None:
    app_instance = app()
    page = PlaylistPage()
    track = {"server_id": 1, "title": "Song", "artist": "Artist"}
    second_track = {"server_id": 2, "title": "Other", "artist": "Artist"}
    removed: list[dict] = []
    page.remove_track_requested.connect(removed.append)
    page.set_tracks({"id": 4, "name": "Mix"}, [track, second_track])
    page.table.resize(640, 160)
    page.table.show()
    app_instance.processEvents()

    button = page.table._overflow_buttons[0]
    assert button.accessibleName() == "More options for Song"
    assert button.focusPolicy() == Qt.TabFocus

    button.click()

    assert page._track_menu is not None
    assert [action.text() for action in page._track_menu.actions()] == ["Remove from playlist"]
    assert page.table._menu_row == 0

    first_menu = page._track_menu
    page.table._overflow_buttons[1].click()
    assert page._track_menu is not first_menu
    assert page.table._menu_row == 1

    page._track_menu.actions()[0].trigger()

    assert removed == [second_track]
    assert page._track_menu is None
    assert page.table._menu_row == -1


def test_playlist_page_searches_downloaded_songs_and_adds_selected_result() -> None:
    app()
    page = PlaylistPage()
    downloads = [
        {"server_id": 1, "title": "Pepper", "artist": "Butthole Surfers", "album": "Electriclarryland"},
        {"server_id": 2, "title": "Focus", "artist": "Coder", "album": "Dream State", "duration_ms": 185_000},
        {"server_id": 3, "title": "Workout", "artist": "Band", "album": "Energy"},
    ]
    added: list[dict] = []
    page.add_search_result_requested.connect(added.append)
    page.set_tracks({"id": 4, "name": "Mix"}, [])
    page.set_downloaded_tracks(downloads)

    page.search_input.setText(" dream ")
    page._apply_search()
    row = page._search_rows[0]
    row.add_button.click()

    assert page.search_title.text() == "Let’s find something for your playlist"
    assert page.search_input.placeholderText() == "Search downloaded songs"
    assert page.search_results.isHidden() is False
    assert len(page._search_rows) == 1
    assert row.title.text() == "Focus"
    assert row.artist.text() == "Coder"
    assert row.album.text() == "Dream State"
    assert row.add_button.text() == "Added"
    assert row.add_button.isEnabled() is False
    assert added == [downloads[1]]

    page.set_tracks({"id": 4, "name": "Mix"}, [downloads[1]])
    assert page.search_input.text() == " dream "
    assert page._search_rows[0].add_button.text() == "Added"
    assert page._search_rows[0].add_button.isEnabled() is False

    page.search_input.setText("  ")
    page._apply_search()
    assert page.search_results.isHidden() is True
    assert page.search_empty.isHidden() is True


def test_playlist_page_search_clear_escape_and_empty_state() -> None:
    app()
    page = PlaylistPage()
    page.set_tracks({"id": 4, "name": "Mix"}, [])
    page.set_downloaded_tracks([{"server_id": 1, "title": "Pepper", "artist": "Artist", "album": "Album"}])

    page.search_input.setText("missing")
    page._apply_search()

    assert page.clear_search_button.isHidden() is False
    assert page.search_results.isHidden() is True
    assert page.search_empty.isHidden() is False
    assert page.search_empty.title.text() == "No downloaded songs match “missing”."

    page.clear_search_button.click()
    assert page.search_input.text() == ""

    page.search_input.setText("pepper")
    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    handled = page.eventFilter(page.search_input, event)

    assert handled is True
    assert page.search_input.text() == ""
    assert page.search_results.isHidden() is True


def test_playlist_primary_button_tracks_play_pause_state() -> None:
    app()
    page = PlaylistPage()
    page.set_tracks({"id": 4, "name": "Mix"}, [{"server_id": 1, "title": "Song"}])

    page.set_playing(True)
    assert page.play_button.accessibleName() == "Pause playlist"

    page.set_playing(False)
    assert page.play_button.accessibleName() == "Play playlist"


def test_playlist_cover_storage_replaces_previous_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(main_window_module, "PLAYLIST_COVER_DIR", tmp_path / "covers")
    first = tmp_path / "first.png"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    first_cover = main_window_module.MainWindow._store_playlist_cover(9, first)
    second_cover = main_window_module.MainWindow._store_playlist_cover(9, second)

    assert first_cover.name == "playlist_9.png"
    assert second_cover.name == "playlist_9.jpg"
    assert not first_cover.exists()
    assert second_cover.read_bytes() == b"second"
    assert sorted(path.name for path in (tmp_path / "covers").glob("playlist_9.*")) == ["playlist_9.jpg"]


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
