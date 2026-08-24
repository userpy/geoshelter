import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from infrastructure.app_settings import ICON_FILE
from presentation.main_window import MainWindow
from presentation.theme import apply_theme


def _set_windows_app_id() -> None:
    """Give Windows a stable identity for the taskbar icon."""
    if sys.platform != "win32":
        return

    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "GeoShelter.GeoShelter"
    )


def main() -> int:
    _set_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName("GeoShelter")
    app.setWindowIcon(QIcon(str(ICON_FILE)))
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
