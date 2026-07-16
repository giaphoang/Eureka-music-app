from __future__ import annotations

from pathlib import Path

from eureka_client.player import PlaybackController


class FakePlayer:
    def __init__(self) -> None:
        self.stopped = False
        self.position_value = 0

    def stop(self) -> None:
        self.stopped = True

    def position(self) -> int:
        return self.position_value

    def setPosition(self, position: int) -> None:
        self.position_value = position


def controller_without_qt_player() -> PlaybackController:
    controller = PlaybackController.__new__(PlaybackController)
    controller.player = FakePlayer()
    controller.queue = []
    controller.index = -1
    controller.order = []
    controller.order_position = -1
    controller.shuffle = False
    controller.loop_mode = "off"
    return controller


def test_set_queue_ignores_missing_files_and_keeps_selected_track(tmp_path: Path) -> None:
    existing = tmp_path / "existing.mp3"
    existing.write_bytes(b"ID3")
    missing = tmp_path / "missing.mp3"
    controller = controller_without_qt_player()
    loaded: list[bool] = []
    controller._load_current = lambda autoplay: loaded.append(autoplay)  # type: ignore[method-assign]

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


def test_set_queue_with_only_missing_files_stops_without_crashing(tmp_path: Path) -> None:
    controller = controller_without_qt_player()

    controller.set_queue([{"server_id": 1, "local_path": str(tmp_path / "missing.mp3")}], 0)

    assert controller.queue == []
    assert controller.index == -1
    assert controller.order == []
    assert controller.order_position == -1
    assert controller.player.stopped is True


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
