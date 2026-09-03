import sys

from PyQt6.QtCore import QLibraryInfo, QLocale, QTranslator
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from infrastructure.app_settings import ICON_FILE
from presentation.main_window import MainWindow
from presentation.theme import apply_theme


class _RussianQtFallbackTranslator(QTranslator):
    """Supply translations missing from some Qt Russian catalogs."""

    _TRANSLATIONS = {
        "Look in:": "Папка:",
        "Files of type:": "Тип файлов:",
        "Folder": "Папка",
        "Directories": "Каталоги",
        "Directory:": "Каталог:",
        "&Choose": "&Выбрать",
        "&Cancel": "&Отмена",
    }

    def translate(self, context, source_text, disambiguation=None, n=-1):
        # ``None`` means "translation not found" and lets Qt ask the next
        # installed translator.  An empty Python string is a valid translation
        # and therefore erased labels in standard context menus.
        return self._TRANSLATIONS.get(source_text)


def _set_windows_app_id() -> None:
    """Give Windows a stable identity for the taskbar icon."""
    if sys.platform != "win32":
        return

    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "GeoShelter.GeoShelter"
    )


def _install_russian_qt_translations(app: QApplication) -> None:
    """Translate standard Qt dialogs and controls into Russian."""
    QLocale.setDefault(QLocale(QLocale.Language.Russian))
    translations_dir = QLibraryInfo.path(
        QLibraryInfo.LibraryPath.TranslationsPath
    )
    translator = QTranslator(app)
    if translator.load("qtbase_ru", translations_dir):
        app.installTranslator(translator)
        # Keep the Python wrapper alive for the whole QApplication lifetime.
        app._qt_translator = translator
    fallback_translator = _RussianQtFallbackTranslator(app)
    app.installTranslator(fallback_translator)
    app._qt_fallback_translator = fallback_translator


def main() -> int:
    _set_windows_app_id()
    app = QApplication(sys.argv)
    _install_russian_qt_translations(app)
    app.setApplicationName("GeoShelter")
    app.setWindowIcon(QIcon(str(ICON_FILE)))
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
