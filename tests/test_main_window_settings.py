import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QMessageBox, QTabWidget, QWidget

import presentation.main_window as main_window


class MainWindowSettingsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_saves_settings_with_empty_coordinates(self):
        with TemporaryDirectory() as directory:
            settings_path = str(Path(directory) / "GeoShelter.conf")
            original_factory = main_window.create_user_settings
            original_warning = QMessageBox.warning
            main_window.create_user_settings = lambda: QSettings(
                settings_path, QSettings.Format.IniFormat
            )
            warnings = []
            QMessageBox.warning = lambda _parent, title, text: warnings.append(
                (title, text)
            )
            try:
                window = main_window.MainWindow()
                download_content = window.findChild(
                    QWidget, "downloadContent"
                )
                self.assertIsNotNone(download_content)
                self.assertEqual(download_content.maximumWidth(), 810)
                tabs = window.findChild(QTabWidget, "mainTabs")
                self.assertIsInstance(
                    tabs.parentWidget(), main_window.CenteredPage
                )
                for request_field in (
                    window.max_pages,
                    window.results_per_page,
                    window.request_delay,
                ):
                    self.assertEqual(request_field.width(), 110)
                window._set_api_keys([])
                window._set_categories("203")
                self.assertEqual(
                    window.save_settings_button.text(),
                    "📄 Сохранить настройки",
                )
                self.assertEqual(
                    window.category_list.objectName(), "categoryIdList"
                )
                window.top_point.clear()
                window.bottom_point.clear()
                window.output_dir.setText(directory)

                window._save_settings()

                self.assertEqual(warnings, [])
                self.assertEqual(
                    window.saved_settings.value("top_point", type=str), ""
                )
                self.assertEqual(
                    window.saved_settings.value("bottom_point", type=str), ""
                )
                window._set_api_keys(["test-key"])
                with self.assertRaisesRegex(ValueError, "координаты"):
                    window._collect_settings()
                window.close()
            finally:
                main_window.create_user_settings = original_factory
                QMessageBox.warning = original_warning


if __name__ == "__main__":
    unittest.main()
