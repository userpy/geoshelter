import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QMessageBox, QTabWidget, QWidget

import presentation.main_window as main_window
import presentation.kml_merger as kml_merger


class MainWindowSettingsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_new_install_starts_without_categories_or_coordinates(self):
        with TemporaryDirectory() as directory:
            settings_path = str(Path(directory) / "GeoShelter.conf")
            original_factory = main_window.create_user_settings
            main_window.create_user_settings = lambda: QSettings(
                settings_path, QSettings.Format.IniFormat
            )
            try:
                window = main_window.MainWindow()
                self.assertEqual(window._category_ids(), [])
                self.assertEqual(window.top_point.text(), "")
                self.assertEqual(window.bottom_point.text(), "")
                window.close()
            finally:
                main_window.create_user_settings = original_factory

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

    def test_restore_defaults_clears_output_paths(self):
        with TemporaryDirectory() as directory:
            settings_path = str(Path(directory) / "GeoShelter.conf")
            original_main_factory = main_window.create_user_settings
            original_merger_factory = kml_merger.create_user_settings
            settings = QSettings(settings_path, QSettings.Format.IniFormat)
            main_window.create_user_settings = lambda: settings
            kml_merger.create_user_settings = lambda: settings
            try:
                window = main_window.MainWindow()
                output_dir = str(Path(directory) / "kml")
                output_file = str(Path(directory) / "result.kmz")
                window.output_dir.setText(output_dir)
                merger = window.kml_merger
                merger.output_file.setText(output_file)
                merger._save_output_file()

                window._restore_defaults()

                self.assertEqual(window.output_dir.text(), "")
                self.assertEqual(merger.output_file.text(), "")
                self.assertEqual(
                    settings.value("kml_merger/output_file", type=str), ""
                )
                window.close()

                reopened_window = main_window.MainWindow()
                self.assertEqual(reopened_window.output_dir.text(), "")
                self.assertEqual(reopened_window.kml_merger.output_file.text(), "")
                reopened_window.close()
            finally:
                main_window.create_user_settings = original_main_factory
                kml_merger.create_user_settings = original_merger_factory


if __name__ == "__main__":
    unittest.main()
