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
                missing_status = window.api_key_status_label.text()
                self.assertIn("⚠ Отсутствует", missing_status)
                self.assertIn("#d4a000", missing_status)
                self.assertIn("font-weight: 700", missing_status)
                window._set_api_keys(["test-key"])
                item = window.api_key_list.item(0)

                self.assertIs(
                    window.api_key_list.parentWidget(),
                    window.api_key_manager_page,
                )
                self.assertEqual(
                    window.api_key_manager_button.text(),
                    "🔑 Менеджер API-ключей",
                )
                window.api_key_manager_button.click()
                self.assertIs(
                    window.main_stack.currentWidget(),
                    window.api_key_manager_container,
                )
                window._close_api_key_manager()
                self.assertEqual(window.main_stack.currentIndex(), 0)

                window._update_progress(3, 10)
                self.assertEqual(window.main_progress_bar.maximum(), 10)
                self.assertEqual(window.main_progress_bar.value(), 3)
                self.assertEqual(window.progress_bar.value(), 3)

                window._update_key_status(0, 100, 100, 300, 0)
                self.assertEqual(item.foreground().color().name(), "#c62828")
                self.assertEqual(
                    window.api_key_status_label.text(),
                    "Статус ключа: Лимит исчерпан",
                )

                item.setData(Qt.ItemDataRole.UserRole + 3, 1)
                window._tick_api_key_timers()
                self.assertEqual(item.foreground().color().name(), "#2e7d32")
                self.assertEqual(item.data(Qt.ItemDataRole.UserRole + 1), 0)
                active_status = window.api_key_status_label.text()
                self.assertIn("✓ Активен", active_status)
                self.assertIn("#2e7d32", active_status)
                self.assertIn("font-weight: 700", active_status)
                window.close()
            finally:
                main_window.create_user_settings = original_create_user_settings


if __name__ == "__main__":
    unittest.main()
