import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from infrastructure.app_settings import ICON_FILE
from presentation.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("GeoShelter")
    app.setWindowIcon(QIcon(str(ICON_FILE)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

