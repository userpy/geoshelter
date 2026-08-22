import json

from PyQt6.QtCore import QTimer, QUrl, QUrlQuery, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CategoryBrowserWidget(QWidget):
    back_requested = pyqtSignal()
    category_requested = pyqtSignal(int)
    category_removal_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._api_key = ""
        self._selected_categories: set[int] = set()
        self._add_buttons: dict[int, QPushButton] = {}
        self._category_rows: dict[int, QWidget] = {}
        self._request_number = 0
        self._active_reply: QNetworkReply | None = None
        self._network = QNetworkAccessManager(self)

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        back_button = QPushButton("← Назад")
        back_button.clicked.connect(self.back_requested.emit)
        title = QLabel("Справочник категорий Wikimapia")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        header.addWidget(back_button)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Поиск по названию или ID категории…"
        )
        self.search_input.setClearButtonEnabled(True)
        layout.addWidget(self.search_input)

        self.status_label = QLabel(
            "Начните вводить название категории"
        )
        self.status_label.setStyleSheet("color: #5f6368;")
        layout.addWidget(self.status_label)

        self.category_list = QListWidget()
        self.category_list.setAlternatingRowColors(True)
        layout.addWidget(self.category_list, 1)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(500)
        self._search_timer.timeout.connect(self._search)
        self.search_input.textChanged.connect(self._schedule_search)
        self.search_input.returnPressed.connect(self._search_immediately)

    def open(self, api_key: str, selected_categories: list[int]) -> None:
        self._api_key = api_key
        self.set_selected_categories(selected_categories)
        self.search_input.clear()
        self._search_timer.stop()
        self._search()
        self.search_input.setFocus()

    def cancel_request(self) -> None:
        self._search_timer.stop()
        self._request_number += 1
        if self._active_reply is not None:
            self._active_reply.abort()
            self._active_reply = None

    def set_selected_categories(self, categories: list[int]) -> None:
        self._selected_categories = set(categories)
        for category_id, button in self._add_buttons.items():
            self._update_category_row(category_id, button)

    def mark_added(self, category_id: int) -> None:
        self._selected_categories.add(category_id)
        button = self._add_buttons.get(category_id)
        if button is not None:
            self._update_category_row(category_id, button)

    def mark_removed(self, category_id: int) -> None:
        self._selected_categories.discard(category_id)
        button = self._add_buttons.get(category_id)
        if button is not None:
            self._update_category_row(category_id, button)

    def _toggle_category(self, category_id: int) -> None:
        if category_id in self._selected_categories:
            self.category_removal_requested.emit(category_id)
        else:
            self.category_requested.emit(category_id)

    def _schedule_search(self, _text: str) -> None:
        self._search_timer.start()

    def _search_immediately(self) -> None:
        self._search_timer.stop()
        self._search()

    def _search(self) -> None:
        if not self._api_key:
            self._show_error("Сначала добавьте API-ключ Wikimapia")
            return

        self._request_number += 1
        request_number = self._request_number
        if self._active_reply is not None:
            self._active_reply.abort()

        query_text = self.search_input.text().strip()
        query = QUrlQuery()
        query.addQueryItem("key", self._api_key)
        query.addQueryItem("format", "json")
        query.addQueryItem("language", "ru")
        if query_text.isdigit():
            query.addQueryItem("function", "category.getbyid")
            query.addQueryItem("id", query_text)
        else:
            query.addQueryItem("function", "category.getall")
            query.addQueryItem("count", "100")
            if query_text:
                query.addQueryItem("name", query_text)

        url = QUrl("https://api.wikimapia.org/")
        url.setQuery(query)
        request = QNetworkRequest(url)
        request.setTransferTimeout(15_000)

        self.status_label.setText("Загрузка категорий…")
        self.status_label.setStyleSheet("color: #5f6368;")
        reply = self._network.get(request)
        self._active_reply = reply
        reply.finished.connect(
            lambda: self._handle_reply(reply, request_number)
        )

    def _handle_reply(self, reply: QNetworkReply, request_number: int) -> None:
        if self._active_reply is reply:
            self._active_reply = None
        if request_number != self._request_number:
            reply.deleteLater()
            return

        if reply.error() != QNetworkReply.NetworkError.NoError:
            message = reply.errorString()
            reply.deleteLater()
            self._show_error(f"Ошибка запроса: {message}")
            return

        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            reply.deleteLater()
            self._show_error("Не удалось прочитать ответ Wikimapia")
            return
        reply.deleteLater()

        error = data.get("debug") or data.get("error")
        if error:
            message = (
                error.get("message", str(error))
                if isinstance(error, dict)
                else str(error)
            )
            if isinstance(error, dict) and error.get("code") == 1000:
                message = "недействительный API-ключ"
            self._show_error(f"Ошибка Wikimapia API: {message}")
            return

        raw_categories = data.get("categories", [])
        if isinstance(data.get("category"), dict):
            raw_categories = [data["category"]]
        categories = self._normalize_categories(raw_categories)
        self._show_categories(categories)

    @staticmethod
    def _normalize_categories(raw_categories) -> list[dict]:
        categories = []
        seen_ids = set()
        for raw in raw_categories if isinstance(raw_categories, list) else []:
            if not isinstance(raw, dict):
                continue
            try:
                category_id = int(raw["id"])
            except (KeyError, TypeError, ValueError):
                continue
            name = str(raw.get("name", "")).strip()
            if category_id <= 0 or not name or category_id in seen_ids:
                continue
            seen_ids.add(category_id)
            categories.append({"id": category_id, "name": name})
        return categories

    def _show_categories(self, categories: list[dict]) -> None:
        self.category_list.clear()
        self._add_buttons.clear()
        self._category_rows.clear()
        self.status_label.setStyleSheet("color: #5f6368;")
        for category in categories:
            category_id = category["id"]
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 4, 8, 4)
            name_label = QLabel(category["name"])
            id_label = QLabel(f"ID: {category_id}")
            id_label.setStyleSheet("color: #5f6368;")
            add_button = QPushButton()
            add_button.setFixedWidth(115)
            add_button.clicked.connect(
                lambda _checked=False, value=category_id: self._toggle_category(
                    value
                )
            )
            self._add_buttons[category_id] = add_button
            self._category_rows[category_id] = row
            self._update_category_row(category_id, add_button)

            row_layout.addWidget(name_label, 1)
            row_layout.addWidget(id_label)
            row_layout.addWidget(add_button)
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self.category_list.addItem(item)
            self.category_list.setItemWidget(item, row)

        if categories:
            self.status_label.setText(f"Найдено категорий: {len(categories)}")
        else:
            self.status_label.setText("Категории не найдены")

    def _update_category_row(
        self, category_id: int, button: QPushButton
    ) -> None:
        is_added = category_id in self._selected_categories
        button.setText("− Удалить" if is_added else "+ Добавить")
        row = self._category_rows.get(category_id)
        if row is not None:
            row.setStyleSheet(
                "background-color: #e8f5e9; border-radius: 4px;"
                if is_added
                else ""
            )

    def _show_error(self, message: str) -> None:
        self.category_list.clear()
        self._add_buttons.clear()
        self._category_rows.clear()
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #c62828;")
