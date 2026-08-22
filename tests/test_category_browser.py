import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from presentation.category_browser import CategoryBrowserWidget


class CategoryBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_normalizes_and_deduplicates_api_categories(self):
        categories = CategoryBrowserWidget._normalize_categories(
            [
                {"id": 203, "name": "школа", "amount": 10},
                {"id": "203", "name": "образование"},
                {"id": 287, "name": "больница"},
                {"id": "bad", "name": "неверная запись"},
            ]
        )

        self.assertEqual(
            categories,
            [
                {"id": 203, "name": "школа"},
                {"id": 287, "name": "больница"},
            ],
        )

    def test_added_category_is_green_and_can_be_removed(self):
        browser = CategoryBrowserWidget()
        browser.set_selected_categories([203])
        browser._show_categories([{"id": 203, "name": "школа"}])

        button = browser._add_buttons[203]
        row = browser._category_rows[203]
        self.assertEqual(button.text(), "− Удалить")
        self.assertIn("#e8f5e9", row.styleSheet())

        removed = []
        browser.category_removal_requested.connect(removed.append)
        button.click()
        self.assertEqual(removed, [203])

        browser.mark_removed(203)
        self.assertEqual(button.text(), "+ Добавить")
        self.assertEqual(row.styleSheet(), "")


if __name__ == "__main__":
    unittest.main()
