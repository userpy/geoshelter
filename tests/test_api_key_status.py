import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import QApplication

import presentation.main_window as main_window


class ApiKeyStatusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_exhausted_key_stays_red_until_timer_expires(self):
        with TemporaryDirectory() as directory:
            settings_path = str(Path(directory) / "GeoShelter.conf")
            original_create_user_settings = main_window.create_user_settings
            main_window.create_user_settings = lambda: QSettings(
                settings_path, QSettings.Format.IniFormat
            )
            try:
                window = main_window.MainWindow()
                window._set_api_keys(["test-key"])
                item = window.api_key_list.item(0)

                window._update_key_status(0, 100, 100, 300, 0)
                self.assertEqual(item.foreground().color().name(), "#c62828")

                item.setData(Qt.ItemDataRole.UserRole + 3, 1)
                window._tick_api_key_timers()
                self.assertEqual(item.foreground().color().name(), "#2e7d32")
                self.assertEqual(item.data(Qt.ItemDataRole.UserRole + 1), 0)
                window.close()
            finally:
                main_window.create_user_settings = original_create_user_settings


if __name__ == "__main__":
    unittest.main()
