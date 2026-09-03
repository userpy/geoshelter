"""GeoShelter's application-wide visual theme."""

from pathlib import Path

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication


# Core palette, based on the four reference swatches.
PRIMARY = "#08A88A"
AQUA = "#3BC9B4"
MINT = "#63CBBE"
DEEP_TEAL = "#006B5B"

# Supporting shades keep text readable while preserving the teal character.
BACKGROUND = "#F1F9F7"
SURFACE = "#FFFFFF"
SOFT_MINT = "#E1F5F1"
INPUT_BACKGROUND = "#FAFEFD"
BORDER = "#8AD7CB"
TAB_BORDER_SUBTLE = "1px solid rgba(138, 215, 203, 0.2)"
BORDER_TRANSPARENT = "rgba(138, 215, 203, 0.2)"
TEXT = "#123D37"
MUTED_TEXT = "#55766F"
DISABLED_BACKGROUND = "#DDEBE8"
DISABLED_TEXT = "#78918C"

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"
PLUS_ICON = (ASSET_DIR / "spin_plus.svg").as_posix()
MINUS_ICON = (ASSET_DIR / "spin_minus.svg").as_posix()


APP_STYLE_SHEET = f"""
QMainWindow, QDialog {{
    background-color: {BACKGROUND};
}}

QWidget {{
    color: {TEXT};
    font-size: 13px;
}}

QScrollArea#downloadScrollArea {{
    background-color: {BACKGROUND};
    border: none;
}}

QGroupBox {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_TRANSPARENT};
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: 600;
    color: {DEEP_TEAL};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 2px 9px;
    background-color: {SURFACE};
    border: 1px solid {BORDER_TRANSPARENT};
    border-radius: 7px;
}}

QGroupBox#wikimapiaGroup {{
    margin-top: 0;
    padding-top: 0;
}}

QLabel#wikimapiaTitle {{
    color: {DEEP_TEAL};
    font-size: 17px;
    font-weight: 700;
}}

QLabel#wikimapiaSubtitle {{
    color: {MUTED_TEXT};
    font-size: 11px;
}}

QLabel#pageTitle {{
    color: {DEEP_TEAL};
    font-size: 17px;
    font-weight: 700;
}}

QLineEdit,
QSpinBox,
QDoubleSpinBox,
QPlainTextEdit,
QListWidget,
QTableWidget {{
    background-color: {INPUT_BACKGROUND};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 7px;
    selection-background-color: {AQUA};
    selection-color: {DEEP_TEAL};
}}

QLineEdit:hover,
QSpinBox:hover,
QDoubleSpinBox:hover,
QPlainTextEdit:hover,
QListWidget:hover,
QTableWidget:hover {{
    border-color: {MINT};
}}

QLineEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QPlainTextEdit:focus,
QListWidget:focus,
QTableWidget:focus {{
    border: 2px solid {PRIMARY};
    padding: 4px 6px;
}}

QLineEdit:disabled,
QSpinBox:disabled,
QDoubleSpinBox:disabled,
QPlainTextEdit:disabled,
QListWidget:disabled,
QTableWidget:disabled {{
    background-color: {DISABLED_BACKGROUND};
    color: {DISABLED_TEXT};
}}

QSpinBox::up-button,
QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 28px;
    background-color: {PRIMARY};
    border: 1px solid {DEEP_TEAL};
    border-top-right-radius: 5px;
}}

QSpinBox::up-button:hover,
QDoubleSpinBox::up-button:hover {{
    background-color: {AQUA};
}}

QSpinBox::up-button:pressed,
QDoubleSpinBox::up-button:pressed {{
    background-color: {DEEP_TEAL};
}}

QSpinBox::down-button,
QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 28px;
    background-color: {PRIMARY};
    border: 1px solid {DEEP_TEAL};
    border-bottom-right-radius: 5px;
}}

QSpinBox::down-button:hover,
QDoubleSpinBox::down-button:hover {{
    background-color: {AQUA};
}}

QSpinBox::down-button:pressed,
QDoubleSpinBox::down-button:pressed {{
    background-color: {DEEP_TEAL};
}}

QSpinBox::up-arrow,
QDoubleSpinBox::up-arrow {{
    image: url("{PLUS_ICON}");
    width: 12px;
    height: 12px;
}}

QSpinBox::down-arrow,
QDoubleSpinBox::down-arrow {{
    image: url("{MINUS_ICON}");
    width: 12px;
    height: 12px;
}}

QLineEdit[locked="true"],
QSpinBox[locked="true"],
QDoubleSpinBox[locked="true"] {{
    background-color: #E3E7E6;
    color: #6F7D79;
    border-color: #C2CBC8;
}}

QLineEdit[locked="true"]:hover,
QSpinBox[locked="true"]:hover,
QDoubleSpinBox[locked="true"]:hover,
QLineEdit[locked="true"]:focus,
QSpinBox[locked="true"]:focus,
QDoubleSpinBox[locked="true"]:focus {{
    background-color: #E3E7E6;
    color: #6F7D79;
    border: 1px solid #C2CBC8;
    padding: 5px 7px;
}}

QPushButton {{
    background-color: {SOFT_MINT};
    color: {DEEP_TEAL};
    border: 1px solid {MINT};
    border-radius: 5px;
    padding: 6px 12px;
    font-weight: 600;
}}

QPushButton#categoryToggleButton {{
    border: 1px solid {MINT};
    border-radius: 0;
}}

QPushButton:hover {{
    background-color: {MINT};
    border-color: {PRIMARY};
}}

QPushButton:pressed,
QPushButton:checked {{
    background-color: {DEEP_TEAL};
    color: white;
    border-color: {DEEP_TEAL};
}}

QPushButton:disabled {{
    background-color: {DISABLED_BACKGROUND};
    color: {DISABLED_TEXT};
    border-color: #C7DCD7;
}}

QPushButton#addActionButton,
QPushButton#removeActionButton {{
    min-width: 40px;
    min-height: 30px;
    padding: 0;
    font-size: 20px;
    font-weight: 700;
}}

QPushButton#addActionButton,
QPushButton#removeActionButton {{
    background-color: {SOFT_MINT};
    color: {DEEP_TEAL};
    border: 1px solid {MINT};
}}

QPushButton#addActionButton:hover,
QPushButton#removeActionButton:hover {{
    background-color: {MINT};
    color: {DEEP_TEAL};
    border-color: {PRIMARY};
}}

QPushButton#addActionButton:pressed,
QPushButton#removeActionButton:pressed {{
    background-color: {DEEP_TEAL};
    color: white;
    border-color: {DEEP_TEAL};
}}

QPushButton#addActionButton:disabled,
QPushButton#removeActionButton:disabled {{
    background-color: {DISABLED_BACKGROUND};
    color: {DISABLED_TEXT};
    border-color: #C7DCD7;
}}

QPushButton#primaryButton {{
    background-color: {PRIMARY};
    color: white;
    border: 1px solid {DEEP_TEAL};
    padding: 7px 16px;
}}

QPushButton#primaryButton:hover {{
    background-color: {AQUA};
    color: {DEEP_TEAL};
}}

QPushButton#primaryButton:pressed {{
    background-color: {DEEP_TEAL};
    color: white;
}}

QPushButton#primaryButton:disabled {{
    background-color: #A9D9D0;
    color: #EDF8F6;
    border-color: #9AC8C0;
}}

QTabWidget::pane {{
    background-color: {BACKGROUND};
    border: {TAB_BORDER_SUBTLE};
    border-radius: 0;
    top: -1px;
}}

QTabBar::tab {{
    background-color: {SOFT_MINT};
    color: {DEEP_TEAL};
    border: {TAB_BORDER_SUBTLE};
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}

QTabBar::tab:hover {{
    background-color: {MINT};
}}

QTabBar::tab:selected {{
    background-color: {DEEP_TEAL};
    color: white;
    border-color: {DEEP_TEAL};
}}

QHeaderView::section {{
    background-color: {DEEP_TEAL};
    color: white;
    border: none;
    border-right: 1px solid {PRIMARY};
    padding: 6px 8px;
    font-weight: 600;
}}

QAbstractItemView {{
    background-color: {INPUT_BACKGROUND};
    alternate-background-color: {SOFT_MINT};
    gridline-color: {BORDER};
    outline: none;
}}

QAbstractItemView::item {{
    padding: 4px;
}}

QListWidget#categoryList::item {{
    padding: 0;
}}

QListWidget#categoryList QScrollBar:vertical,
QListWidget#categoryIdList QScrollBar:vertical,
QScrollArea#downloadScrollArea QScrollBar:vertical {{
    background-color: {SOFT_MINT};
    margin-right: 2px;
}}

QListWidget#categoryList QScrollBar::handle:vertical,
QListWidget#categoryIdList QScrollBar::handle:vertical,
QScrollArea#downloadScrollArea QScrollBar::handle:vertical {{
    background-color: {PRIMARY};
    min-height: 24px;
}}

QListWidget#categoryList QScrollBar::handle:vertical:hover,
QListWidget#categoryIdList QScrollBar::handle:vertical:hover,
QScrollArea#downloadScrollArea QScrollBar::handle:vertical:hover {{
    background-color: {DEEP_TEAL};
}}

QListWidget#categoryList QScrollBar::add-line:vertical,
QListWidget#categoryList QScrollBar::sub-line:vertical,
QListWidget#categoryIdList QScrollBar::add-line:vertical,
QListWidget#categoryIdList QScrollBar::sub-line:vertical,
QScrollArea#downloadScrollArea QScrollBar::add-line:vertical,
QScrollArea#downloadScrollArea QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
}}

QListWidget#categoryList QScrollBar::add-page:vertical,
QListWidget#categoryList QScrollBar::sub-page:vertical,
QListWidget#categoryIdList QScrollBar::add-page:vertical,
QListWidget#categoryIdList QScrollBar::sub-page:vertical,
QScrollArea#downloadScrollArea QScrollBar::add-page:vertical,
QScrollArea#downloadScrollArea QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QAbstractItemView::item:selected {{
    background-color: {AQUA};
    color: {DEEP_TEAL};
}}

QProgressBar {{
    min-height: 18px;
    background-color: {SOFT_MINT};
    color: {DEEP_TEAL};
    border: 1px solid {BORDER};
    border-radius: 7px;
    text-align: center;
    font-weight: 600;
}}

QProgressBar::chunk {{
    border-radius: 6px;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 {PRIMARY}, stop: 0.52 {AQUA}, stop: 1 {MINT}
    );
}}

QCheckBox {{
    spacing: 7px;
}}

QCheckBox:disabled {{
    color: {DISABLED_TEXT};
}}

QToolTip {{
    background-color: {DEEP_TEAL};
    color: white;
    border: 1px solid {AQUA};
    padding: 4px;
}}

QMenu {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px;
}}

QMenu::item {{
    background-color: transparent;
    color: {TEXT};
    padding: 5px 24px 5px 8px;
}}

QMenu::item:selected {{
    background-color: {SOFT_MINT};
    color: {DEEP_TEAL};
}}

QMenu::item:disabled {{
    color: {DISABLED_TEXT};
}}

QMenu::separator {{
    background-color: {BORDER};
    height: 1px;
    margin: 4px 6px;
}}
"""


def apply_theme(app: QApplication) -> None:
    """Apply a predictable cross-platform base style and GeoShelter colors."""
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BACKGROUND))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(INPUT_BACKGROUND))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(SOFT_MINT))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(SOFT_MINT))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(DEEP_TEAL))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(PRIMARY))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(DISABLED_TEXT))
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor(DISABLED_TEXT),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        QColor(DISABLED_TEXT),
    )
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLE_SHEET)
