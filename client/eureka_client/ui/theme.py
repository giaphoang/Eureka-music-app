from __future__ import annotations

from pathlib import Path

from PySide2.QtWidgets import QApplication, QStyleFactory


RESOURCE_DIR = Path(__file__).resolve().parent / "resources"
THEME_PATH = RESOURCE_DIR / "theme.qss"


def apply_theme(app: QApplication) -> None:
    app.setStyle(QStyleFactory.create("Fusion"))
    if THEME_PATH.is_file():
        app.setStyleSheet(THEME_PATH.read_text())


def icon_path(name: str) -> str:
    return str(RESOURCE_DIR / "icons" / f"{name}.svg")
