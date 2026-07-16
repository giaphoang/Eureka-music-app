from __future__ import annotations

from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QIcon
from PySide2.QtMultimedia import QMediaPlayer
from PySide2.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QToolButton, QVBoxLayout, QWidget

from eureka_client.ui.theme import icon_path


class PlayerBar(QWidget):
    toggle_requested = Signal()
    stop_requested = Signal()
    previous_requested = Signal()
    next_requested = Signal()
    seek_requested = Signal(int)
    shuffle_changed = Signal(bool)
    loop_changed = Signal(str)
    queue_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PlayerBar")
        self._loop_modes = ["off", "one", "all"]
        self._loop_index = 0
        self._duration = 0

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(16)

        self.artwork = QLabel("EQ")
        self.artwork.setObjectName("NowPlayingArtwork")
        self.artwork.setAlignment(Qt.AlignCenter)
        root.addWidget(self.artwork)

        meta = QVBoxLayout()
        self.title = QLabel("Nothing playing")
        self.title.setProperty("role", "nowTitle")
        self.artist = QLabel("")
        self.artist.setProperty("role", "secondary")
        meta.addWidget(self.title)
        meta.addWidget(self.artist)
        root.addLayout(meta, 1)

        center = QVBoxLayout()
        controls = QHBoxLayout()
        self.shuffle_button = self._tool_button("shuffle", "Shuffle")
        self.shuffle_button.setCheckable(True)
        self.shuffle_button.toggled.connect(self.shuffle_changed)
        self.previous_button = self._button("skip-back", "Previous", self.previous_requested)
        self.play_button = self._button("play", "Play or pause", self.toggle_requested)
        self.next_button = self._button("skip-forward", "Next", self.next_requested)
        self.loop_button = self._tool_button("repeat", "Loop off")
        self.loop_button.clicked.connect(self._cycle_loop)
        controls.addStretch()
        controls.addWidget(self.shuffle_button)
        controls.addWidget(self.previous_button)
        controls.addWidget(self.play_button)
        controls.addWidget(self.next_button)
        controls.addWidget(self.loop_button)
        controls.addStretch()

        seek = QHBoxLayout()
        self.position_label = QLabel("00:00")
        self.position_label.setProperty("role", "secondary")
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.sliderReleased.connect(
            lambda: self.seek_requested.emit(self.seek_slider.value())
        )
        self.duration_label = QLabel("00:00")
        self.duration_label.setProperty("role", "secondary")
        seek.addWidget(self.position_label)
        seek.addWidget(self.seek_slider, 1)
        seek.addWidget(self.duration_label)
        center.addLayout(controls)
        center.addLayout(seek)
        root.addLayout(center, 3)

        self.stop_button = self._button("square", "Stop", self.stop_requested)
        self.queue_button = self._button("list", "Show queue", self.queue_requested)
        root.addWidget(self.stop_button)
        root.addWidget(self.queue_button)

    def _button(self, icon: str, name: str, signal: Signal) -> QPushButton:
        button = QPushButton(QIcon(icon_path(icon)), "")
        button.setProperty("role", "icon")
        button.setToolTip(name)
        button.setAccessibleName(name)
        button.clicked.connect(signal)
        return button

    def _tool_button(self, icon: str, name: str) -> QToolButton:
        button = QToolButton()
        button.setIcon(QIcon(icon_path(icon)))
        button.setProperty("role", "icon")
        button.setToolTip(name)
        button.setAccessibleName(name)
        return button

    def set_track(self, track: dict | None) -> None:
        if not track:
            self.title.setText("Nothing playing")
            self.artist.setText("")
            self.artwork.setText("EQ")
            return
        self.title.setText(str(track.get("title") or "Untitled"))
        self.artist.setText(str(track.get("artist") or "Unknown Artist"))
        seed = str(track.get("genre") or track.get("title") or "EQ")
        self.artwork.setText(seed[:2].upper())

    def set_position(self, position: int) -> None:
        self.seek_slider.blockSignals(True)
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(max(0, position))
        self.seek_slider.blockSignals(False)
        self.position_label.setText(self._format_ms(position))
        self.duration_label.setText(self._format_ms(self._duration))

    def set_duration(self, duration: int) -> None:
        self._duration = max(0, duration)
        self.seek_slider.setMaximum(self._duration)
        self.duration_label.setText(self._format_ms(self._duration))

    def set_state(self, state: int) -> None:
        playing = state == QMediaPlayer.PlayingState
        self.play_button.setIcon(QIcon(icon_path("pause" if playing else "play")))
        self.play_button.setToolTip("Pause" if playing else "Play")
        self.play_button.setAccessibleName("Pause" if playing else "Play")

    def _cycle_loop(self) -> None:
        self._loop_index = (self._loop_index + 1) % len(self._loop_modes)
        mode = self._loop_modes[self._loop_index]
        if mode == "one":
            self.loop_button.setIcon(QIcon(icon_path("repeat-1")))
            self.loop_button.setToolTip("Loop one")
        elif mode == "all":
            self.loop_button.setIcon(QIcon(icon_path("repeat")))
            self.loop_button.setToolTip("Loop all")
        else:
            self.loop_button.setIcon(QIcon(icon_path("repeat")))
            self.loop_button.setToolTip("Loop off")
        self.loop_changed.emit(mode)

    @staticmethod
    def _format_ms(value: int) -> str:
        seconds = max(0, value // 1000)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"
