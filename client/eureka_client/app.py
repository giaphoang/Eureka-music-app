import sys

from PySide2.QtWidgets import QApplication

from eureka_client.config import ensure_dirs
from eureka_client.ui.main_window import MainWindow


def main() -> int:
    ensure_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName("Eureka Music")
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
