import re
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QTimer
from PyQt6.QtGui import QBrush, QColor, QIcon, QPalette, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from domain.geometry import build_bbox
from domain.models import MAX_AREAS, DownloadSettings
from infrastructure.app_settings import (
    DEFAULT_SETTINGS,
    ICON_FILE,
    create_user_settings,
)
from presentation.category_browser import CategoryBrowserWidget
from presentation.download_grid import DownloadGridWidget
from presentation.download_worker import DownloadWorker
from presentation.kml_merger import KmlMergerWidget
from presentation.theme import APP_STYLE_SHEET

MAX_CATEGORIES = 15


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
        self._selected_api_key_index = None
        self._control_enabled_states = {}
        self.saved_settings = create_user_settings()
        self.setWindowTitle("GeoShelter — Wikimapia в KML")
        self.setWindowIcon(QIcon(str(ICON_FILE)))
        self.resize(760, 850)
        self.setStyleSheet(APP_STYLE_SHEET)
        self._build_ui()
        self._load_saved_settings()
        self.api_key_timer = QTimer(self)
        self.api_key_timer.setInterval(1_000)
        self.api_key_timer.timeout.connect(self._tick_api_key_timers)
        self.api_key_timer.start()

    def _build_ui(self):
        central = QWidget()
        central_layout = QVBoxLayout(central)
        self.main_stack = QStackedWidget()
        tabs = QTabWidget()
        download_tab = QWidget()
        root = QVBoxLayout(download_tab)
        tabs.addTab(download_tab, "Загрузка мест")
        tabs.addTab(KmlMergerWidget(), "Объединение KML в KMZ")

        api_group = QGroupBox("Wikimapia")
        api_layout = QHBoxLayout(api_group)
        api_key_column = QWidget()
        api_key_form = QFormLayout(api_key_column)
        api_key_form.setContentsMargins(0, 0, 0, 0)
        categories_column = QWidget()
        categories_form = QFormLayout(categories_column)
        categories_form.setContentsMargins(0, 0, 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("WIKIMAPIA_API_KEY")
        self.api_key_input.returnPressed.connect(self._add_api_key)
        self.api_key_visibility_button = QPushButton("👁")
        self.api_key_visibility_button.setCheckable(True)
        self.api_key_visibility_button.setFixedWidth(38)
        self.api_key_visibility_button.setToolTip("Показать API-ключ")
        self.api_key_visibility_button.clicked.connect(
            self._toggle_api_key_visibility
        )
        self.add_api_key_button = QPushButton("+")
        self.add_api_key_button.setObjectName("addActionButton")
        self.add_api_key_button.setFixedWidth(42)
        self.add_api_key_button.setAccessibleName("Добавить API-ключ")
        self.add_api_key_button.setToolTip("Добавить API-ключ")
        self.add_api_key_button.clicked.connect(self._add_api_key)
        self.remove_api_key_button = QPushButton("−")
        self.remove_api_key_button.setObjectName("removeActionButton")
        self.remove_api_key_button.setFixedWidth(42)
        self.remove_api_key_button.setAccessibleName(
            "Удалить выбранный API-ключ"
        )
        self.remove_api_key_button.setToolTip("Удалить выбранный API-ключ")
        self.remove_api_key_button.clicked.connect(self._remove_api_key)
        api_key_input_row = QHBoxLayout()
        api_key_input_row.setContentsMargins(0, 0, 0, 0)
        api_key_input_row.addWidget(self.api_key_input, 1)
        api_key_input_row.addWidget(self.api_key_visibility_button)
        api_key_input_row.addWidget(self.add_api_key_button)
        api_key_input_row.addWidget(self.remove_api_key_button)
        self.api_key_list = QListWidget()
        self.api_key_list.setMaximumHeight(72)
        self.api_key_list.currentRowChanged.connect(self._select_api_key)
        api_key_container = QWidget()
        api_key_layout = QVBoxLayout(api_key_container)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.setSpacing(4)
        api_key_layout.addLayout(api_key_input_row)
        api_key_layout.addWidget(self.api_key_list)
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("ID категории")
        self.category_input.returnPressed.connect(self._add_category)
        self.add_category_button = QPushButton("+")
        self.add_category_button.setObjectName("addActionButton")
        self.add_category_button.setFixedWidth(42)
        self.add_category_button.setAccessibleName("Добавить категорию")
        self.add_category_button.setToolTip("Добавить категорию")
        self.add_category_button.clicked.connect(self._add_category)
        self.remove_category_button = QPushButton("−")
        self.remove_category_button.setObjectName("removeActionButton")
        self.remove_category_button.setFixedWidth(42)
        self.remove_category_button.setAccessibleName(
            "Удалить выбранную категорию"
        )
        self.remove_category_button.setToolTip("Удалить выбранную категорию")
        self.remove_category_button.clicked.connect(self._remove_category)
        self.category_browser_button = QPushButton("📖")
        self.category_browser_button.setToolTip("Открыть справочник категорий")
        self.category_browser_button.clicked.connect(self._open_category_browser)
        category_button_height = max(
            button.sizeHint().height()
            for button in (
                self.category_browser_button,
                self.add_category_button,
                self.remove_category_button,
            )
        )
        for button in (
            self.category_browser_button,
            self.add_category_button,
            self.remove_category_button,
        ):
            button.setFixedSize(
                42 if button in (
                    self.add_category_button,
                    self.remove_category_button,
                ) else 38,
                category_button_height,
            )
        category_input_row = QHBoxLayout()
        category_input_row.setContentsMargins(0, 0, 0, 0)
        category_input_row.addWidget(self.category_input, 1)
        category_input_row.addWidget(self.add_category_button)
        category_input_row.addWidget(self.remove_category_button)
        category_input_row.addWidget(self.category_browser_button)
        self.category_list = QListWidget()
        self.category_list.setMaximumHeight(72)
        category_container = QWidget()
        category_layout = QVBoxLayout(category_container)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(4)
        category_layout.addLayout(category_input_row)
        category_layout.addWidget(self.category_list)
        api_key_form.addRow("API-ключи:", api_key_container)
        categories_form.addRow("ID категорий:", category_container)
        api_layout.addWidget(api_key_column, 1)
        api_layout.addWidget(categories_column, 1)
        root.addWidget(api_group)

        coords_group = QGroupBox("Область поиска")
        coords_layout = QHBoxLayout(coords_group)
        coordinates_column = QWidget()
        coords_grid = QGridLayout(coordinates_column)
        coords_grid.setContentsMargins(0, 0, 0, 0)
        grid_column = QWidget()
        grid_form = QFormLayout(grid_column)
        grid_form.setContentsMargins(0, 0, 0, 0)
        self.top_point = QLineEdit()
        self.bottom_point = QLineEdit()
        coordinate_hint = "Формат: широта, долгота"
        self.top_point.setPlaceholderText(coordinate_hint)
        self.bottom_point.setPlaceholderText(coordinate_hint)
        coords_grid.addWidget(QLabel("Верхняя левая:"), 0, 0)
        coords_grid.addWidget(self.top_point, 0, 1)
        coords_grid.addWidget(QLabel("Нижняя правая:"), 1, 0)
        coords_grid.addWidget(self.bottom_point, 1, 1)
        coords_grid.addWidget(
            QLabel("Вставьте пару целиком, например: 55.838340, 49.206620"),
            2,
            0,
            1,
            2,
        )
        self.square_count = self._integer_spin(1, MAX_AREAS, 1)
        self.row_count = self._integer_spin(1, MAX_AREAS, 1)
        self.total_areas_label = QLabel()
        self.square_count.valueChanged.connect(self._update_total_areas)
        self.row_count.valueChanged.connect(self._update_total_areas)
        self.direction_button = QPushButton()
        self.direction_button.setCheckable(True)
        self.direction_button.clicked.connect(self._toggle_direction)
        self.vertical_direction_button = QPushButton()
        self.vertical_direction_button.setCheckable(True)
        self.vertical_direction_button.clicked.connect(
            self._toggle_vertical_direction
        )
        grid_form.addRow(
            "Областей по горизонтали:",
            self._area_direction_row(
                self.square_count, self.direction_button
            ),
        )
        grid_form.addRow(
            "Областей по вертикали:",
            self._area_direction_row(
                self.row_count, self.vertical_direction_button
            ),
        )
        grid_form.addRow("Всего областей:", self.total_areas_label)
        self.grid_lock_button = QPushButton()
        self.grid_lock_button.setCheckable(True)
        self.grid_lock_button.clicked.connect(self._toggle_grid_fields_lock)
        grid_form.addRow("Редактирование:", self.grid_lock_button)
        self._set_grid_fields_locked(True)
        coords_layout.addWidget(coordinates_column, 1)
        coords_layout.addWidget(grid_column, 1)
        root.addWidget(coords_group)

        request_group = QGroupBox("Параметры запроса")
        request_form = QFormLayout(request_group)
        self.max_pages = self._integer_spin(1, 1000, 1)
        self.results_per_page = self._integer_spin(1, 100, 1)
        self.request_delay = QDoubleSpinBox()
        self.request_delay.setRange(0, 60)
        self.request_delay.setDecimals(1)
        self.request_delay.setSuffix(" с")
        request_form.addRow("Максимум страниц:", self.max_pages)
        request_form.addRow("Объектов на странице:", self.results_per_page)
        request_form.addRow("Задержка:", self.request_delay)
        self.include_detailed_description = QCheckBox(
            "Загружать подробное описание"
        )
        self.include_detailed_description.setToolTip(
            "Выполняет дополнительный запрос для каждого места; "
            "загрузка займёт больше времени"
        )
        request_form.addRow("Описание:", self.include_detailed_description)
        self.request_lock_button = QPushButton()
        self.request_lock_button.setCheckable(True)
        self.request_lock_button.clicked.connect(self._toggle_request_fields_lock)
        request_form.addRow("Редактирование:", self.request_lock_button)
        self._set_request_fields_locked(True)
        self._update_total_areas()
        root.addWidget(request_group)

        output_row = QHBoxLayout()
        self.output_dir = QLineEdit()
        browse_button = QPushButton("Обзор…")
        browse_button.clicked.connect(self._choose_output_dir)
        output_row.addWidget(QLabel("Каталог KML:"))
        output_row.addWidget(self.output_dir, 1)
        output_row.addWidget(browse_button)
        root.addLayout(output_row)

        settings_buttons = QHBoxLayout()
        save_settings_button = QPushButton("Сохранить настройки")
        restore_defaults_button = QPushButton("По умолчанию")
        save_settings_button.clicked.connect(self._save_settings)
        restore_defaults_button.clicked.connect(self._restore_defaults)
        settings_buttons.addWidget(save_settings_button)
        settings_buttons.addWidget(restore_defaults_button)
        settings_buttons.addStretch()
        root.addLayout(settings_buttons)

        buttons = QHBoxLayout()
        self.start_button = QPushButton("Начать загрузку")
        self.start_button.setObjectName("primaryButton")
        self.stop_button = QPushButton("Остановить")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self._start_download)
        self.stop_button.clicked.connect(self._stop_download)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        root.addLayout(buttons)

        grid_group = QGroupBox("Сетка областей")
        grid_layout = QVBoxLayout(grid_group)
        self.download_grid = DownloadGridWidget()
        grid_layout.addWidget(self.download_grid)
        root.addWidget(grid_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Здесь появится журнал загрузки…")
        root.addWidget(self.log_view, 1)

        self.category_browser = CategoryBrowserWidget()
        self.category_browser.back_requested.connect(self._close_category_browser)
        self.category_browser.category_requested.connect(
            self._add_category_from_browser
        )
        self.category_browser.category_removal_requested.connect(
            self._remove_category_from_browser
        )
        self.main_stack.addWidget(tabs)
        self.main_stack.addWidget(self.category_browser)
        central_layout.addWidget(self.main_stack)
        self.setCentralWidget(central)

    @staticmethod
    def _integer_spin(minimum, maximum, value):
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    @staticmethod
    def _area_direction_row(count_field, direction_button):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(count_field, 44)
        layout.addWidget(direction_button, 56)
        return container

    def _update_total_areas(self, _value=None):
        changed_field = self.sender()
        if changed_field is self.square_count:
            allowed_rows = MAX_AREAS // self.square_count.value()
            if self.row_count.value() > allowed_rows:
                self.row_count.setValue(allowed_rows)
        elif changed_field is self.row_count:
            allowed_columns = MAX_AREAS // self.row_count.value()
            if self.square_count.value() > allowed_columns:
                self.square_count.setValue(allowed_columns)

        total = self.square_count.value() * self.row_count.value()
        self.total_areas_label.setText(f"{total} / {MAX_AREAS}")
        if hasattr(self, "download_grid") and self.thread is None:
            self.download_grid.set_grid(
                self.row_count.value(), self.square_count.value()
            )

    def _choose_output_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Выберите каталог",
            self.output_dir.text(),
        )
        if directory:
            self.output_dir.setText(directory)

    def _toggle_api_key_visibility(self, visible):
        self.api_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
        self.api_key_visibility_button.setText("🙈" if visible else "👁")
        self.api_key_visibility_button.setToolTip(
            "Скрыть API-ключ" if visible else "Показать API-ключ"
        )
        for index in range(self.api_key_list.count()):
            self._render_api_key_item(self.api_key_list.item(index))

    def _add_api_key(self):
        key = self.api_key_input.text().strip()
        if not key:
            QMessageBox.warning(
                self, "Неверный API-ключ", "Введите API-ключ"
            )
            return
        if key not in self._api_keys():
            self._append_api_key(key)
        self.api_key_input.clear()

    def _append_api_key(self, key):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setData(Qt.ItemDataRole.UserRole + 1, 0)
        item.setData(Qt.ItemDataRole.UserRole + 2, 100)
        item.setData(Qt.ItemDataRole.UserRole + 3, 0)
        item.setData(Qt.ItemDataRole.UserRole + 4, 0)
        self.api_key_list.addItem(item)
        self._render_api_key_item(item)
        if self._selected_api_key_index is None:
            self.api_key_list.setCurrentItem(item)

    def _remove_api_key(self):
        selected_key = self._selected_api_key()
        for item in self.api_key_list.selectedItems():
            self.api_key_list.takeItem(self.api_key_list.row(item))
        if self.api_key_list.count() == 0:
            self._selected_api_key_index = None
        elif selected_key not in self._api_keys():
            self.api_key_list.setCurrentRow(0)

    def _set_api_keys(self, values):
        self._selected_api_key_index = None
        self.api_key_list.clear()
        if isinstance(values, str):
            values = values.splitlines()
        for key in values:
            key = str(key).strip()
            if key:
                self._append_api_key(key)

    def _api_keys(self):
        return [
            self.api_key_list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.api_key_list.count())
        ]

    def _selected_api_key(self):
        if self._selected_api_key_index is None:
            return None
        item = self.api_key_list.item(self._selected_api_key_index)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _render_api_key_item(self, item):
        key = item.data(Qt.ItemDataRole.UserRole)
        visible = self.api_key_visibility_button.isChecked()
        shown_key = key if visible else self._masked_api_key(key)
        count = item.data(Qt.ItemDataRole.UserRole + 1) or 0
        limit = item.data(Qt.ItemDataRole.UserRole + 2) or 100
        seconds = item.data(Qt.ItemDataRole.UserRole + 3) or 0
        errors = item.data(Qt.ItemDataRole.UserRole + 4) or 0
        timer = f"{seconds // 60:02d}:{seconds % 60:02d}"
        selected_marker = (
            "✓  "
            if self.api_key_list.row(item) == self._selected_api_key_index
            else ""
        )
        item.setText(
            f"{selected_marker}{shown_key}  —  {count}/{limit}  •  ошибок {errors}  "
            f"•  сброс {timer}"
        )
        limit_exhausted = count >= limit and seconds > 0
        item.setToolTip(
            "Лимит API-ключа исчерпан. "
            "Ключ станет доступен после окончания таймера."
            if limit_exhausted
            else "API-ключ доступен"
        )
        item.setForeground(
            QBrush(QColor("#c62828" if limit_exhausted else "#2e7d32"))
        )

    def _tick_api_key_timers(self):
        for index in range(self.api_key_list.count()):
            item = self.api_key_list.item(index)
            seconds = item.data(Qt.ItemDataRole.UserRole + 3) or 0
            if seconds <= 0:
                continue
            seconds -= 1
            item.setData(Qt.ItemDataRole.UserRole + 3, seconds)
            if seconds == 0:
                item.setData(Qt.ItemDataRole.UserRole + 1, 0)
            self._render_api_key_item(item)

    @staticmethod
    def _masked_api_key(key):
        if len(key) <= 8:
            return "•" * len(key)
        hidden = "•" * (len(key) - 8)
        return f"{key[:4]}{hidden}{key[-4:]}"

    def _add_category(self):
        value = self.category_input.text().strip()
        try:
            category_id = int(value)
        except ValueError:
            QMessageBox.warning(self, "Неверная категория", "Введите целый ID категории")
            return
        self._add_category_id(category_id)
        self.category_input.clear()

    def _add_category_id(self, category_id: int) -> bool:
        if category_id <= 0:
            QMessageBox.warning(
                self,
                "Неверная категория",
                "ID категории должен быть больше нуля",
            )
            return False
        category_text = str(category_id)
        if self.category_list.findItems(
            category_text, Qt.MatchFlag.MatchExactly
        ):
            return True
        if self.category_list.count() >= MAX_CATEGORIES:
            QMessageBox.warning(
                self,
                "Слишком много категорий",
                f"Можно добавить не более {MAX_CATEGORIES} категорий",
            )
            return False
        self.category_list.addItem(category_text)
        return True

    def _open_category_browser(self):
        api_keys = self._api_keys()
        api_key = (
            self._selected_api_key()
            or self.api_key_input.text().strip()
            or (api_keys[0] if api_keys else "")
        )
        if not api_key:
            QMessageBox.warning(
                self,
                "Нет API-ключа",
                "Добавьте, пожалуйста, API-ключ Wikimapia",
            )
            return
        self.category_browser.open(api_key, self._category_ids())
        self.main_stack.setCurrentWidget(self.category_browser)

    def _close_category_browser(self):
        self.category_browser.cancel_request()
        self.main_stack.setCurrentIndex(0)

    def _add_category_from_browser(self, category_id: int):
        if self._add_category_id(category_id):
            self.category_browser.mark_added(category_id)

    def _remove_category_from_browser(self, category_id: int):
        category_text = str(category_id)
        for item in self.category_list.findItems(
            category_text, Qt.MatchFlag.MatchExactly
        ):
            self.category_list.takeItem(self.category_list.row(item))
        self.category_browser.mark_removed(category_id)

    def _remove_category(self):
        for item in self.category_list.selectedItems():
            self.category_list.takeItem(self.category_list.row(item))

    def _set_categories(self, values):
        self.category_list.clear()
        for value in str(values).split(","):
            value = value.strip()
            if value and self.category_list.count() < MAX_CATEGORIES:
                category_text = str(int(value))
                if not self.category_list.findItems(
                    category_text, Qt.MatchFlag.MatchExactly
                ):
                    self.category_list.addItem(category_text)

    def _category_ids(self):
        return [
            int(self.category_list.item(index).text())
            for index in range(self.category_list.count())
        ]

    def _toggle_direction(self, move_left):
        self.direction_button.setText("← Лево" if move_left else "→ Право")
        self.direction_button.setToolTip(
            "Следующие области будут добавляться слева"
            if move_left
            else "Следующие области будут добавляться справа"
        )

    def _toggle_vertical_direction(self, move_up):
        self.vertical_direction_button.setText("↑ Верх" if move_up else "↓ Низ")
        self.vertical_direction_button.setToolTip(
            "Следующие строки будут добавляться сверху"
            if move_up
            else "Следующие строки будут добавляться снизу"
        )

    def _toggle_request_fields_lock(self):
        self._set_request_fields_locked(not self.request_lock_button.isChecked())

    def _toggle_grid_fields_lock(self):
        self._set_grid_fields_locked(not self.grid_lock_button.isChecked())

    def _set_grid_fields_locked(self, locked):
        self.grid_lock_button.setChecked(not locked)
        self.grid_lock_button.setText(
            "🔒 Разблокировать" if locked else "🔓 Заблокировать"
        )
        self.grid_lock_button.setToolTip(
            "Разрешить изменение сетки"
            if locked
            else "Защитить сетку от случайного изменения"
        )
        button_symbols = (
            QAbstractSpinBox.ButtonSymbols.NoButtons
            if locked
            else QAbstractSpinBox.ButtonSymbols.PlusMinus
        )
        for field in (self.square_count, self.row_count):
            field.setReadOnly(locked)
            field.setButtonSymbols(button_symbols)
            self._set_field_locked_appearance(field, locked)
        self.direction_button.setEnabled(not locked)
        self.vertical_direction_button.setEnabled(not locked)

    def _set_request_fields_locked(self, locked):
        self.request_lock_button.setChecked(not locked)
        self.request_lock_button.setText(
            "🔒 Разблокировать" if locked else "🔓 Заблокировать"
        )
        self.request_lock_button.setToolTip(
            "Разрешить изменение параметров"
            if locked
            else "Защитить параметры от случайного изменения"
        )
        self.include_detailed_description.setEnabled(not locked)
        button_symbols = (
            QAbstractSpinBox.ButtonSymbols.NoButtons
            if locked
            else QAbstractSpinBox.ButtonSymbols.PlusMinus
        )
        for field in (
            self.max_pages,
            self.results_per_page,
            self.request_delay,
        ):
            field.setReadOnly(locked)
            field.setButtonSymbols(button_symbols)
            self._set_field_locked_appearance(field, locked)

    @staticmethod
    def _set_field_locked_appearance(field, locked):
        field.setProperty("locked", locked)
        field.style().unpolish(field)
        field.style().polish(field)
        field.update()

    def _load_saved_settings(self):
        saved_api_keys = self.saved_settings.value("api_keys", "", type=str)
        if not saved_api_keys:
            saved_api_keys = self.saved_settings.value(
                "api_key", DEFAULT_SETTINGS["api_keys"], type=str
            )
        values = {
            "api_keys": saved_api_keys,
            "categories": self.saved_settings.value(
                "categories", DEFAULT_SETTINGS["categories"], type=str
            ),
            "top_point": self.saved_settings.value(
                "top_point", DEFAULT_SETTINGS["top_point"], type=str
            ),
            "bottom_point": self.saved_settings.value(
                "bottom_point", DEFAULT_SETTINGS["bottom_point"], type=str
            ),
            "square_count": self.saved_settings.value(
                "square_count", DEFAULT_SETTINGS["square_count"], type=int
            ),
            "row_count": self.saved_settings.value(
                "row_count", DEFAULT_SETTINGS["row_count"], type=int
            ),
            "vertical_direction": self.saved_settings.value(
                "vertical_direction",
                DEFAULT_SETTINGS["vertical_direction"],
                type=str,
            ),
            "direction": self.saved_settings.value(
                "direction", DEFAULT_SETTINGS["direction"], type=str
            ),
            "max_pages": self.saved_settings.value(
                "max_pages", DEFAULT_SETTINGS["max_pages"], type=int
            ),
            "results_per_page": self.saved_settings.value(
                "results_per_page",
                DEFAULT_SETTINGS["results_per_page"],
                type=int,
            ),
            "request_delay": self.saved_settings.value(
                "request_delay", DEFAULT_SETTINGS["request_delay"], type=float
            ),
            "include_detailed_description": self.saved_settings.value(
                "include_detailed_description",
                DEFAULT_SETTINGS["include_detailed_description"],
                type=bool,
            ),
            "output_dir": self.saved_settings.value(
                "output_dir", DEFAULT_SETTINGS["output_dir"], type=str
            ),
        }
        self._apply_settings(values)

    def _apply_settings(self, values):
        self._set_api_keys(values["api_keys"])
        self._set_categories(values["categories"])
        self.top_point.setText(str(values["top_point"]))
        self.bottom_point.setText(str(values["bottom_point"]))
        self.square_count.setValue(int(values["square_count"]))
        self.row_count.setValue(int(values["row_count"]))
        move_up = str(values["vertical_direction"]) == "up"
        self.vertical_direction_button.setChecked(move_up)
        self._toggle_vertical_direction(move_up)
        move_left = str(values["direction"]) == "left"
        self.direction_button.setChecked(move_left)
        self._toggle_direction(move_left)
        self.max_pages.setValue(int(values["max_pages"]))
        self.results_per_page.setValue(int(values["results_per_page"]))
        self.request_delay.setValue(float(values["request_delay"]))
        self.include_detailed_description.setChecked(
            bool(values["include_detailed_description"])
        )
        self.output_dir.setText(str(values["output_dir"]))

    def _save_settings(self):
        try:
            self._validate_common_settings()
            self._validated_coordinates(required=False)
        except ValueError as error:
            QMessageBox.warning(self, "Проверьте параметры", str(error))
            return

        values = {
            "api_keys": "\n".join(self._api_keys()),
            "categories": ", ".join(
                str(category_id) for category_id in self._category_ids()
            ),
            "top_point": self.top_point.text().strip(),
            "bottom_point": self.bottom_point.text().strip(),
            "square_count": self.square_count.value(),
            "row_count": self.row_count.value(),
            "vertical_direction": (
                "up" if self.vertical_direction_button.isChecked() else "down"
            ),
            "direction": "left" if self.direction_button.isChecked() else "right",
            "max_pages": self.max_pages.value(),
            "results_per_page": self.results_per_page.value(),
            "request_delay": self.request_delay.value(),
            "include_detailed_description": (
                self.include_detailed_description.isChecked()
            ),
            "output_dir": self.output_dir.text().strip(),
        }
        for key, value in values.items():
            self.saved_settings.setValue(key, value)
        self.saved_settings.sync()
        self._set_grid_fields_locked(True)
        self._set_request_fields_locked(True)
        self.statusBar().showMessage("Настройки сохранены", 4_000)

    def _restore_defaults(self):
        cleared_values = {
            "categories": "",
            "top_point": "",
            "bottom_point": "",
        }
        self.saved_settings.clear()
        for key, value in cleared_values.items():
            self.saved_settings.setValue(key, value)
        self.saved_settings.sync()
        default_values = {
            **DEFAULT_SETTINGS,
            **cleared_values,
        }
        self._apply_settings(default_values)
        self._set_grid_fields_locked(True)
        self._set_request_fields_locked(True)
        self.statusBar().showMessage("Восстановлены настройки по умолчанию", 4_000)

    def _collect_settings(self):
        api_keys, categories, output_dir = self._validate_common_settings()
        top_point, bottom_point = self._validated_coordinates(required=True)

        return DownloadSettings(
            api_keys=tuple(api_keys),
            selected_api_key_index=self._selected_api_key_index or 0,
            categories=tuple(categories),
            top_point=top_point,
            bottom_point=bottom_point,
            square_count=self.square_count.value(),
            row_count=self.row_count.value(),
            vertical_direction=(
                "up" if self.vertical_direction_button.isChecked() else "down"
            ),
            direction="left" if self.direction_button.isChecked() else "right",
            max_pages=self.max_pages.value(),
            results_per_page=self.results_per_page.value(),
            request_delay=self.request_delay.value(),
            include_detailed_description=(
                self.include_detailed_description.isChecked()
            ),
            output_dir=output_dir,
        )

    def _validate_common_settings(self):
        api_keys = self._api_keys()
        if not api_keys:
            raise ValueError("Укажите хотя бы один API-ключ Wikimapia")

        categories = self._category_ids()
        if not categories:
            raise ValueError("Укажите хотя бы одну категорию")
        if len(categories) > MAX_CATEGORIES:
            raise ValueError(
                f"Можно указать не более {MAX_CATEGORIES} категорий"
            )

        output_dir_value = self.output_dir.text().strip()
        if not output_dir_value:
            raise ValueError("Выберите каталог для KML-файлов")
        output_dir = Path(output_dir_value).expanduser()
        if not output_dir.is_dir():
            raise ValueError("Каталог для KML-файлов не существует")
        return api_keys, categories, output_dir

    def _validated_coordinates(self, required):
        top_value = self.top_point.text().strip()
        bottom_value = self.bottom_point.text().strip()
        if not top_value and not bottom_value:
            if required:
                raise ValueError("Укажите координаты области поиска")
            return None
        if not top_value or not bottom_value:
            raise ValueError(
                "Укажите обе точки области или очистите оба поля"
        )
        top_point = self._parse_coordinates(
            top_value, "верхней левой точки"
        )
        bottom_point = self._parse_coordinates(
            bottom_value, "нижней правой точки"
        )
        build_bbox(top_point, bottom_point)
        return top_point, bottom_point

    @staticmethod
    def _parse_coordinates(value, field_name):
        numbers = re.findall(r"[-+]?\d+(?:[.,]\d+)?", value.strip())
        if len(numbers) != 2:
            raise ValueError(
                f"Укажите широту и долготу {field_name}, "
                "например: 55.838340, 49.206620"
            )

        latitude, longitude = (
            float(number.replace(",", ".")) for number in numbers
        )
        if not -90 <= latitude <= 90:
            raise ValueError(f"Широта {field_name} должна быть от -90 до 90")
        if not -180 <= longitude <= 180:
            raise ValueError(f"Долгота {field_name} должна быть от -180 до 180")
        return (latitude, longitude)

    def _start_download(self):
        try:
            settings = self._collect_settings()
        except ValueError as error:
            QMessageBox.warning(self, "Проверьте параметры", str(error))
            return

        self.log_view.clear()
        self._selected_api_key_index = None
        for index in range(self.api_key_list.count()):
            item = self.api_key_list.item(index)
            item.setData(Qt.ItemDataRole.UserRole + 1, 0)
            item.setData(Qt.ItemDataRole.UserRole + 2, 100)
            item.setData(Qt.ItemDataRole.UserRole + 3, 0)
            item.setData(Qt.ItemDataRole.UserRole + 4, 0)
            self._render_api_key_item(item)
        self.progress_bar.setRange(
            0,
            settings.total_jobs,
        )
        self.progress_bar.setValue(0)
        self.download_grid.set_grid(settings.row_count, settings.square_count)
        self._area_place_counts = [
            0 for _ in range(settings.square_count * settings.row_count)
        ]
        self._grid_rows = settings.row_count
        self._grid_columns = settings.square_count
        self._grid_horizontal_direction = settings.direction
        self._grid_vertical_direction = settings.vertical_direction
        self._set_download_controls_locked(True)
        self.stop_button.setEnabled(True)

        self.thread = QThread(self)
        self.worker = DownloadWorker(settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self._append_log)
        self.worker.progress.connect(self._update_progress)
        self.worker.key_status.connect(self._update_key_status)
        self.worker.key_selected.connect(self._select_api_key)
        self.worker.area_started.connect(self._area_started)
        self.worker.area_completed.connect(self._area_completed)
        self.worker.finished.connect(self._download_finished)
        self.worker.failed.connect(self._download_failed)
        self.worker.cancelled.connect(self._download_cancelled)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.worker.cancelled.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.worker.cancelled.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._thread_finished)
        self.thread.start()

    def _stop_download(self):
        if self.worker:
            self.worker.stop()
            self.stop_button.setEnabled(False)
            self.log_view.appendPlainText("Запрошена остановка…")

    def _set_download_controls_locked(self, locked):
        controls = [
            *self.findChildren(QLineEdit),
            *self.findChildren(QAbstractSpinBox),
            *self.findChildren(QPushButton),
            *self.findChildren(QListWidget),
        ]
        controls = [control for control in controls if control is not self.stop_button]
        if locked:
            self._control_enabled_states = {
                control: control.isEnabled() for control in controls
            }
            for control in controls:
                control.setEnabled(False)
        else:
            for control, was_enabled in self._control_enabled_states.items():
                control.setEnabled(was_enabled)
            self._control_enabled_states.clear()

    def _update_progress(self, value, maximum):
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)

    def _update_key_status(self, index, count, limit, seconds, errors):
        if not 0 <= index < self.api_key_list.count():
            return
        item = self.api_key_list.item(index)
        item.setData(Qt.ItemDataRole.UserRole + 1, count)
        item.setData(Qt.ItemDataRole.UserRole + 2, limit)
        item.setData(Qt.ItemDataRole.UserRole + 3, seconds)
        item.setData(Qt.ItemDataRole.UserRole + 4, errors)
        self._render_api_key_item(item)

    def _select_api_key(self, index):
        if not 0 <= index < self.api_key_list.count():
            return
        if self.api_key_list.currentRow() != index:
            self.api_key_list.setCurrentRow(index)
            return
        previous_index = self._selected_api_key_index
        self._selected_api_key_index = index
        for changed_index in {previous_index, index}:
            if (
                changed_index is not None
                and 0 <= changed_index < self.api_key_list.count()
            ):
                self._render_api_key_item(self.api_key_list.item(changed_index))

    def _area_started(self, row, column, category_id):
        display_row, display_column = self._display_area_coordinates(row, column)
        self.download_grid.mark_processing(
            display_row, display_column, category_id
        )

    def _area_completed(self, row, column, place_count):
        area_index = row * self._grid_columns + column
        self._area_place_counts[area_index] += place_count
        display_row, display_column = self._display_area_coordinates(row, column)
        self.download_grid.mark_completed(
            display_row,
            display_column,
            self._area_place_counts[area_index],
            place_count,
        )

    def _display_area_coordinates(self, row, column):
        display_row = row
        display_column = column
        if self._grid_vertical_direction == "up":
            display_row = self._grid_rows - 1 - row
        if self._grid_horizontal_direction == "left":
            display_column = self._grid_columns - 1 - column
        return display_row, display_column

    def _append_log(self, message):
        text_format = QTextCharFormat()
        stripped_message = message.strip()
        if stripped_message.startswith("Пустой KML не создан:"):
            text_format.setForeground(QColor("#c62828"))
            text_format.setFontWeight(700)
        elif stripped_message.startswith("KML создан:"):
            text_format.setForeground(QColor("#2e7d32"))
            text_format.setFontWeight(700)
        else:
            text_format.setForeground(
                self.log_view.palette().color(QPalette.ColorRole.Text)
            )

        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if not self.log_view.document().isEmpty():
            cursor.insertBlock()
        cursor.insertText(message, text_format)
        self.log_view.setTextCursor(cursor)
        self.log_view.ensureCursorVisible()

    def _download_finished(self, files, places):
        self.log_view.appendPlainText(
            f"Готово. Файлов: {files}, объектов: {places}."
        )
        QMessageBox.information(
            self,
            "Загрузка завершена",
            f"Создано KML-файлов: {files}\nСохранено объектов: {places}",
        )

    def _download_failed(self, message):
        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.download_grid.reset()
        QMessageBox.critical(self, "Ошибка загрузки", message)

    def _download_cancelled(self):
        self.log_view.appendPlainText("Загрузка остановлена.")

    def _thread_finished(self):
        self._set_download_controls_locked(False)
        self.stop_button.setEnabled(False)
        self.thread = None
        self.worker = None

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait(35_000)
        event.accept()
