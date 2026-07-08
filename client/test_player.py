from __future__ import annotations

from pathlib import Path

from eureka_client.player import PlaybackController


class FakePlayer:
    def __init__(self) -> None:
        self.stopped = False
        self.position_value = 0
        self.media_values = []
        self.deleted_later = False
        self.playing = False
        self.paused = False

    def stop(self) -> None:
        self.stopped = True

    def play(self) -> None:
        self.playing = True

    def pause(self) -> None:
        self.paused = True

    def state(self) -> int:
        return 1 if self.playing and not self.paused else 0

    def position(self) -> int:
        return self.position_value

    def setPosition(self, position: int) -> None:
        self.position_value = position

    def setMedia(self, media: object) -> None:
        self.media_values.append(media)

    def deleteLater(self) -> None:
        self.deleted_later = True

    def errorString(self) -> str:
        return ""


def controller_without_qt_player() -> PlaybackController:
    controller = PlaybackController.__new__(PlaybackController)
    controller.player = FakePlayer()
    controller.queue = []
    controller.index = -1
    controller.order = []
    controller.order_position = -1
    controller.shuffle = False
    controller.loop_mode = "off"
    controller._shutdown = False
    return controller


def test_set_queue_ignores_missing_files_and_keeps_selected_track(tmp_path: Path) -> None:
    existing = tmp_path / "existing.mp3"
    existing.write_bytes(b"ID3")
    missing = tmp_path / "missing.mp3"
    controller = controller_without_qt_player()
    loaded: list[bool] = []
    errors: list[str] = []
    controller._load_current = lambda autoplay: loaded.append(autoplay)  # type: ignore[method-assign]
    controller._emit_error = errors.append  # type: ignore[method-assign]

    controller.set_queue(
        [
            {"server_id": 1, "local_path": str(missing)},
            {"server_id": 2, "local_path": str(existing)},
        ],
        1,
    )

    assert [track["server_id"] for track in controller.queue] == [2]
    assert controller.index == 0
    assert controller.order == [0]
    assert loaded == [True]
    assert errors == []


def test_set_queue_with_missing_selected_file_does_not_play_another_track(tmp_path: Path) -> None:
    existing = tmp_path / "existing.mp3"
    existing.write_bytes(b"ID3")
    missing = tmp_path / "missing.mp3"
    controller = controller_without_qt_player()
    loaded: list[bool] = []
    errors: list[str] = []
    controller._load_current = lambda autoplay: loaded.append(autoplay)  # type: ignore[method-assign]
    controller._emit_error = errors.append  # type: ignore[method-assign]

    controller.set_queue(
        [
            {"server_id": 1, "local_path": str(missing)},
            {"server_id": 2, "local_path": str(existing)},
        ],
        0,
    )

    assert controller.queue == []
    assert controller.index == -1
    assert controller.order == []
    assert controller.order_position == -1
    assert controller.player.stopped is True
    assert loaded == []
    assert errors == [f"Local audio file is missing: {missing}"]


def test_set_queue_with_only_missing_files_stops_without_crashing(tmp_path: Path) -> None:
    controller = controller_without_qt_player()
    errors: list[str] = []
    controller._emit_error = errors.append  # type: ignore[method-assign]
    missing = tmp_path / "missing.mp3"

    controller.set_queue([{"server_id": 1, "local_path": str(missing)}], 0)

    assert controller.queue == []
    assert controller.index == -1
    assert controller.order == []
    assert controller.order_position == -1
    assert controller.player.stopped is True
    assert errors == [f"Local audio file is missing: {missing}"]


def test_manual_order_next_previous_and_loop_all() -> None:
    controller = controller_without_qt_player()
    controller.queue = [{"server_id": 1}, {"server_id": 2}]
    controller._rebuild_order(0)
    loaded: list[int] = []
    controller._load_current = lambda autoplay: loaded.append(controller.index)  # type: ignore[method-assign]

    controller.next()
    assert controller.index == 1
    assert loaded == [1]

    controller.next()
    assert controller.index == 1
    assert controller.player.stopped is True

    controller.player.stopped = False
    controller.loop_mode = "all"
    controller.next()
    assert controller.index == 0
    assert loaded[-1] == 0

    controller.previous()
    assert controller.index == 1
    assert loaded[-1] == 1


def test_shuffle_order_contains_each_track_once() -> None:
    controller = controller_without_qt_player()
    controller.queue = [{"server_id": 1}, {"server_id": 2}, {"server_id": 3}]
    controller.shuffle = True

    controller._rebuild_order(1)

    assert controller.order[0] == 1
    assert sorted(controller.order) == [0, 1, 2]
    assert controller.order_position == 0


def test_shutdown_stops_clears_media_and_is_idempotent() -> None:
    controller = controller_without_qt_player()
    controller.queue = [{"server_id": 1}]
    controller.index = 0
    controller.order = [0]
    controller.order_position = 0

    controller.shutdown()
    controller.shutdown()

    assert controller._shutdown is True
    assert controller.queue == []
    assert controller.index == -1
    assert controller.order == []
    assert controller.order_position == -1
    assert controller.player.stopped is True
    assert len(controller.player.media_values) == 1
    assert controller.player.deleted_later is True


def test_set_queue_after_shutdown_does_not_load_track(tmp_path: Path) -> None:
    existing = tmp_path / "existing.mp3"
    existing.write_bytes(b"ID3")
    controller = controller_without_qt_player()
    loaded: list[bool] = []
    controller._load_current = lambda autoplay: loaded.append(autoplay)  # type: ignore[method-assign]

    controller.shutdown()
    controller.set_queue([{"server_id": 1, "local_path": str(existing)}], 0)

    assert loaded == []
    assert controller.queue == []
