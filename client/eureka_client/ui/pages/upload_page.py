from __future__ import annotations

from pathlib import Path

from PySide2.QtCore import Signal
from PySide2.QtWidgets import QFormLayout, QHBoxLayout, QLineEdit, QProgressBar, QPushButton, QWidget


class UploadPage(QWidget):
    browse_requested = Signal()
    upload_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("UploadPage")
        form = QFormLayout(self)
        form.setContentsMargins(18, 18, 18, 18)

        self.upload_path = QLineEdit()
        self.upload_path.setPlaceholderText("Choose a local audio file")
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse_requested)
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
        upload.setProperty("role", "primary")
        upload.clicked.connect(self.upload_requested)
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

    def set_path(self, path: str) -> None:
        self.upload_path.setText(path)
        if path and not self.upload_title.text():
            self.upload_title.setText(Path(path).stem)

    def selected_path(self) -> Path:
        return Path(self.upload_path.text())

    def metadata(self) -> dict:
        return {
            "title": self.upload_title.text().strip(),
            "artist": self.upload_artist.text().strip(),
            "album": self.upload_album.text().strip(),
            "genre": self.upload_genre.text().strip(),
        }

    def set_uploading(self, uploading: bool) -> None:
        if uploading:
            self.upload_progress.setRange(0, 0)
        else:
            self.upload_progress.setRange(0, 1)
            self.upload_progress.setValue(0)

    def set_complete(self) -> None:
        self.upload_progress.setRange(0, 1)
        self.upload_progress.setValue(1)
