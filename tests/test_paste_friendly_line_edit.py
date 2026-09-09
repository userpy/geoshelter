import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from presentation.main_window import PasteFriendlyLineEdit


class PasteFriendlyLineEditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.line_edit = PasteFriendlyLineEdit()

    def _press(self, key, modifiers, text=""):
        event = QKeyEvent(QEvent.Type.KeyPress, key, modifiers, text)
        with patch.object(self.line_edit, "paste") as paste:
            self.line_edit.keyPressEvent(event)
        return paste

    def test_pastes_with_cyrillic_key_code_when_event_text_is_empty(self):
        paste = self._press(
            ord("М"), Qt.KeyboardModifier.ControlModifier
        )

        paste.assert_called_once_with()

    def test_pastes_with_cyrillic_event_text(self):
        paste = self._press(
            Qt.Key.Key_unknown,
            Qt.KeyboardModifier.ControlModifier,
            "м",
        )

        paste.assert_called_once_with()

    def test_standard_shift_insert_paste_is_not_blocked(self):
        paste = self._press(
            Qt.Key.Key_Insert, Qt.KeyboardModifier.ShiftModifier
        )

        paste.assert_called_once_with()

    def test_alt_modified_shortcut_is_not_treated_as_paste(self):
        paste = self._press(
            ord("М"),
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.AltModifier,
        )

        paste.assert_not_called()


if __name__ == "__main__":
    unittest.main()
