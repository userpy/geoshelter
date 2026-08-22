from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from presentation.theme import DEEP_TEAL, MINT, PRIMARY, SOFT_MINT, TEXT


class DownloadGridWidget(QWidget):
    """Компактная карта состояния областей загрузки."""

    PENDING_COLOR = QColor(SOFT_MINT)
    PROCESSING_COLOR = QColor(MINT)
    EMPTY_COLOR = QColor("#fbc02d")
    COMPLETED_COLOR = QColor(PRIMARY)
    BORDER_COLOR = QColor(DEEP_TEAL)
    TEXT_COLOR = QColor(TEXT)
    COMPLETED_TEXT_COLOR = QColor("#FFFFFF")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = 1
        self._columns = 1
        self._states: dict[tuple[int, int], int | None] = {}
        self._processing_categories: dict[tuple[int, int], int] = {}
        self._empty_categories: dict[tuple[int, int], list[int]] = {}
        self.setMinimumHeight(90)

    def sizeHint(self) -> QSize:
        return QSize(600, 130)

    def set_grid(self, rows: int, columns: int) -> None:
        self._rows = max(1, rows)
        self._columns = max(1, columns)
        self._states.clear()
        self._processing_categories.clear()
        self._empty_categories.clear()
        self.update()

    def reset(self) -> None:
        self._states.clear()
        self._processing_categories.clear()
        self._empty_categories.clear()
        self.update()

    def mark_processing(self, row: int, column: int, category_id: int) -> None:
        if 0 <= row < self._rows and 0 <= column < self._columns:
            self._states[(row, column)] = None
            self._processing_categories[(row, column)] = category_id
            self.update()

    def mark_completed(
        self,
        row: int,
        column: int,
        place_count: int,
        category_place_count: int | None = None,
    ) -> None:
        if 0 <= row < self._rows and 0 <= column < self._columns:
            area = (row, column)
            category_id = self._processing_categories.get(area)
            if category_place_count is None:
                category_place_count = place_count
            if category_place_count == 0 and category_id is not None:
                empty_categories = self._empty_categories.setdefault(area, [])
                if category_id not in empty_categories:
                    empty_categories.append(category_id)
            self._states[(row, column)] = max(0, place_count)
            self._processing_categories.pop(area, None)
            self.update()

    def is_completed(self, row: int, column: int) -> bool:
        return (row, column) in self._states and self._states[(row, column)] is not None

    def is_processing(self, row: int, column: int) -> bool:
        return (row, column) in self._states and self._states[(row, column)] is None

    def place_count(self, row: int, column: int) -> int | None:
        if self.is_processing(row, column):
            return None
        return self._states.get((row, column))

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        area = self.rect().adjusted(4, 4, -4, -4)
        cell_width = area.width() / self._columns
        cell_height = area.height() / self._rows
        for row in range(self._rows):
            for column in range(self._columns):
                left = round(area.left() + column * cell_width)
                top = round(area.top() + row * cell_height)
                right = round(area.left() + (column + 1) * cell_width)
                bottom = round(area.top() + (row + 1) * cell_height)
                state_exists = (row, column) in self._states
                place_count = self._states.get((row, column))
                if not state_exists:
                    color = self.PENDING_COLOR
                    label = f"{row + 1}:{column + 1}\nНе обработано"
                elif place_count is None:
                    color = self.PROCESSING_COLOR
                    category_id = self._processing_categories.get((row, column))
                    label = f"В обработке\nКатегория: {category_id}"
                elif place_count == 0:
                    color = self.EMPTY_COLOR
                    categories = ", ".join(
                        str(value)
                        for value in self._empty_categories.get((row, column), [])
                    )
                    label = "Не найдено"
                    if categories:
                        label += f": {categories}"
                else:
                    color = self.COMPLETED_COLOR
                    label = (
                        f"{row + 1}:{column + 1}\n"
                        f"Добавленные места: {place_count}"
                    )
                painter.fillRect(left, top, right - left, bottom - top, color)
                painter.setPen(QPen(self.BORDER_COLOR, 1))
                painter.drawRect(left, top, right - left, bottom - top)

                if cell_width >= 65 and cell_height >= 30:
                    painter.setPen(
                        self.COMPLETED_TEXT_COLOR
                        if place_count is not None and place_count > 0
                        else self.TEXT_COLOR
                    )
                    painter.drawText(
                        left + 3,
                        top + 2,
                        right - left - 6,
                        bottom - top - 4,
                        Qt.AlignmentFlag.AlignCenter
                        | Qt.TextFlag.TextWordWrap,
                        label,
                    )
