from __future__ import annotations

import random
from pathlib import Path

from PySide2.QtCore import QObject, QUrl, Signal
from PySide2.QtMultimedia import QMediaContent, QMediaPlayer


class PlaybackController(QObject):
    track_changed = Signal(object)
    position_changed = Signal(int)
    duration_changed = Signal(int)
    state_changed = Signal(int)
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.player = QMediaPlayer(None, QMediaPlayer.StreamPlayback)
        self.queue: list[dict] = []
        self.index = -1
        self.order: list[int] = []
        self.order_position = -1
        self.shuffle = False
        self.loop_mode = "off"

        self.player.positionChanged.connect(self._forward_position_changed)
        self.player.durationChanged.connect(self._forward_duration_changed)
        self.player.stateChanged.connect(self._forward_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.error.connect(self._on_error)

    def _forward_position_changed(self, position: int) -> None:
        self.position_changed.emit(int(position))

    def _forward_duration_changed(self, duration: int) -> None:
        self.duration_changed.emit(int(duration))

    def _forward_state_changed(self, state: QMediaPlayer.State) -> None:
        self.state_changed.emit(int(state))

    def set_queue(self, tracks: list[dict], start_index: int = 0) -> None:
        selected = tracks[start_index] if tracks and 0 <= start_index < len(tracks) else None
        self.queue = [track for track in tracks if Path(track["local_path"]).is_file()]
        if not self.queue:
            self.stop()
            self.index = -1
            self.order = []
            self.order_position = -1
            return

        selected_index = 0
        if selected is not None:
            selected_key = (selected.get("server_id"), selected.get("local_path"))
            for candidate_index, candidate in enumerate(self.queue):
                candidate_key = (candidate.get("server_id"), candidate.get("local_path"))
                if candidate_key == selected_key:
                    selected_index = candidate_index
                    break

        self._rebuild_order(selected_index)
        self._load_current(autoplay=True)

    def set_shuffle(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if self.shuffle == enabled:
            return
        self.shuffle = enabled
        if self.index >= 0:
            self._rebuild_order(self.index)

    def play_track(self, track: dict) -> None:
        self.set_queue([track], 0)

    def toggle(self) -> None:
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        elif self.index >= 0:
            self.player.play()

    def stop(self) -> None:
        self.player.stop()

    def seek(self, position_ms: int) -> None:
        self.player.setPosition(max(0, position_ms))

    def next(self) -> None:
        if not self.queue:
            return
        if self.order_position + 1 < len(self.order):
            self.order_position += 1
        elif self.loop_mode == "all":
            start_index = random.randrange(len(self.queue)) if self.shuffle else 0
            self._rebuild_order(start_index)
        else:
            self.stop()
            return
        self.index = self.order[self.order_position]
        self._load_current(autoplay=True)

    def previous(self) -> None:
        if not self.queue:
            return
        if self.player.position() > 3_000:
            self.player.setPosition(0)
            return
        if self.order_position > 0:
            self.order_position -= 1
        elif self.loop_mode == "all":
            self.order_position = len(self.order) - 1
        else:
            self.player.setPosition(0)
            return
        self.index = self.order[self.order_position]
        self._load_current(autoplay=True)

    def _rebuild_order(self, start_index: int) -> None:
        if not self.queue:
            self.order = []
            self.order_position = -1
            self.index = -1
            return

        start_index = max(0, min(start_index, len(self.queue) - 1))
        if self.shuffle:
            remainder = [i for i in range(len(self.queue)) if i != start_index]
            random.shuffle(remainder)
            self.order = [start_index, *remainder]
            self.order_position = 0
        else:
            self.order = list(range(len(self.queue)))
            self.order_position = start_index
        self.index = start_index

    def _load_current(self, autoplay: bool) -> None:
        track = self.queue[self.index]
        url = QUrl.fromLocalFile(str(Path(track["local_path"]).resolve()))
        self.player.setMedia(QMediaContent(url))
        self.track_changed.emit(track)
        if autoplay:
            self.player.play()

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.EndOfMedia:
            if self.loop_mode == "one":
                self.player.setPosition(0)
                self.player.play()
            else:
                self.next()

    def _on_error(self, *_: object) -> None:
        self.error.emit(self.player.errorString() or "Audio playback error")
