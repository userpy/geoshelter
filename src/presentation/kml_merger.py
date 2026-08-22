from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from application.merge_kml import category_from_filename, merge_kml_by_category
from infrastructure.app_settings import create_user_settings

SOURCE_CATEGORY_ROLE = int(Qt.ItemDataRole.UserRole) + 1


class KmlMergerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = create_user_settings()
        self._build_ui()
        self._load_category_mappings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        description = QLabel(
            "Добавьте KML-файлы. Файлы с одинаковой категорией будут "
            "собраны в одну папку внутри KMZ. Категорию можно изменить двойным щелчком "
            "или назначить сразу всем выделенным строкам."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        buttons = QHBoxLayout()
        add_button = QPushButton("Добавить KML…")
        remove_button = QPushButton("Удалить выбранные")
        clear_button = QPushButton("Очистить")
        add_button.clicked.connect(self._add_files)
        remove_button.clicked.connect(self._remove_selected)
        clear_button.clicked.connect(lambda: self.table.setRowCount(0))
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        buttons.addWidget(clear_button)
        buttons.addStretch()
        layout.addLayout(buttons)

        category_row = QHBoxLayout()
        self.selected_category_input = QLineEdit()
        self.selected_category_input.setPlaceholderText(
            "ID или название категории"
        )
        apply_category_button = QPushButton("Добавить к выделенным")
        apply_category_button.clicked.connect(self._apply_category_to_selected)
        self.selected_category_input.returnPressed.connect(
            self._apply_category_to_selected
        )
        category_row.addWidget(QLabel("Категория:"))
        category_row.addWidget(self.selected_category_input, 1)
        category_row.addWidget(apply_category_button)
        layout.addLayout(category_row)

        mapping_group = QGroupBox("Названия категорий")
        mapping_layout = QVBoxLayout(mapping_group)
        mapping_inputs = QHBoxLayout()
        self.category_id_input = QLineEdit()
        self.category_id_input.setPlaceholderText("ID, например 2390")
        self.category_name_input = QLineEdit()
        self.category_name_input.setPlaceholderText("Название категории")
        add_mapping_button = QPushButton("+")
        add_mapping_button.setFixedWidth(38)
        add_mapping_button.setToolTip("Добавить соответствие")
        add_mapping_button.clicked.connect(self._add_category_mapping)
        remove_mapping_button = QPushButton("−")
        remove_mapping_button.setFixedWidth(38)
        remove_mapping_button.setToolTip("Удалить выбранные соответствия")
        remove_mapping_button.clicked.connect(self._remove_category_mappings)
        self.category_name_input.returnPressed.connect(self._add_category_mapping)
        mapping_inputs.addWidget(QLabel("ID:"))
        mapping_inputs.addWidget(self.category_id_input)
        mapping_inputs.addWidget(QLabel("Название:"))
        mapping_inputs.addWidget(self.category_name_input, 1)
        mapping_inputs.addWidget(add_mapping_button)
        mapping_inputs.addWidget(remove_mapping_button)
        mapping_layout.addLayout(mapping_inputs)

        self.category_mapping_table = QTableWidget(0, 2)
        self.category_mapping_table.setHorizontalHeaderLabels(
            ["ID категории", "Название"]
        )
        self.category_mapping_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.category_mapping_table.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )
        self.category_mapping_table.setMaximumHeight(130)
        mapping_header = self.category_mapping_table.horizontalHeader()
        mapping_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        mapping_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        mapping_layout.addWidget(self.category_mapping_table)

        mapping_buttons = QHBoxLayout()
        apply_mappings_button = QPushButton("Применить к указанным файлам")
        apply_mappings_button.clicked.connect(self._apply_category_mappings)
        save_mappings_button = QPushButton("Сохранить категории")
        save_mappings_button.clicked.connect(self._save_category_mappings)
        mapping_buttons.addWidget(apply_mappings_button)
        mapping_buttons.addWidget(save_mappings_button)
        mapping_buttons.addStretch()
        mapping_layout.addLayout(mapping_buttons)
        layout.addWidget(mapping_group)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["KML-файл", "Категория"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        output_row = QHBoxLayout()
        self.output_file = QLineEdit(str(Path.cwd() / "places.kmz"))
        browse_button = QPushButton("Обзор…")
        browse_button.clicked.connect(self._choose_output)
        output_row.addWidget(QLabel("Итоговый KMZ:"))
        output_row.addWidget(self.output_file, 1)
        output_row.addWidget(browse_button)
        layout.addLayout(output_row)

        merge_button = QPushButton("Создать KMZ")
        merge_button.clicked.connect(self._merge)
        layout.addWidget(merge_button, 0, Qt.AlignmentFlag.AlignLeft)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите KML-файлы", str(Path.cwd()), "KML (*.kml)"
        )
        existing = {
            self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            for row in range(self.table.rowCount())
        }
        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        for filename in files:
            path = Path(filename)
            if str(path) in existing:
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            file_item = QTableWidgetItem(path.name)
            file_item.setToolTip(str(path))
            file_item.setData(Qt.ItemDataRole.UserRole, str(path))
            file_item.setData(
                SOURCE_CATEGORY_ROLE, category_from_filename(path)
            )
            file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, file_item)
            self.table.setItem(row, 1, QTableWidgetItem(category_from_filename(path)))
            existing.add(str(path))
        self.table.setSortingEnabled(sorting_enabled)

    def _remove_selected(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def _apply_category_to_selected(self):
        category = self.selected_category_input.text().strip()
        if not category:
            QMessageBox.warning(self, "Категория не указана", "Введите категорию")
            return
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if not rows:
            QMessageBox.warning(
                self, "Места не выбраны", "Выделите одну или несколько строк"
            )
            return
        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        for row in rows:
            self.table.item(row, 1).setText(category)
        self.table.setSortingEnabled(sorting_enabled)
        self.selected_category_input.clear()

    def _add_category_mapping(self):
        category_id = self.category_id_input.text().strip()
        category_name = self.category_name_input.text().strip()
        if not category_id or not category_name:
            QMessageBox.warning(
                self,
                "Не все данные указаны",
                "Введите ID и название категории",
            )
            return
        if not category_id.isdigit():
            QMessageBox.warning(
                self, "Неверный ID", "ID категории должен состоять из цифр"
            )
            return

        for row in range(self.category_mapping_table.rowCount()):
            if self.category_mapping_table.item(row, 0).text() == category_id:
                self.category_mapping_table.item(row, 1).setText(category_name)
                break
        else:
            row = self.category_mapping_table.rowCount()
            self.category_mapping_table.insertRow(row)
            id_item = QTableWidgetItem(category_id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.category_mapping_table.setItem(row, 0, id_item)
            self.category_mapping_table.setItem(row, 1, QTableWidgetItem(category_name))
        self.category_id_input.clear()
        self.category_name_input.clear()
        self.category_id_input.setFocus()

    def _remove_category_mappings(self):
        rows = sorted(
            {index.row() for index in self.category_mapping_table.selectedIndexes()},
            reverse=True,
        )
        for row in rows:
            self.category_mapping_table.removeRow(row)

    def _load_category_mappings(self):
        count = self.settings.beginReadArray("kml_merger/category_mappings")
        for index in range(count):
            self.settings.setArrayIndex(index)
            category_id = str(self.settings.value("id", "")).strip()
            category_name = str(self.settings.value("name", "")).strip()
            if not category_id or not category_name:
                continue
            row = self.category_mapping_table.rowCount()
            self.category_mapping_table.insertRow(row)
            id_item = QTableWidgetItem(category_id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.category_mapping_table.setItem(row, 0, id_item)
            self.category_mapping_table.setItem(row, 1, QTableWidgetItem(category_name))
        self.settings.endArray()

    def _save_category_mappings(self):
        self.settings.beginWriteArray("kml_merger/category_mappings")
        saved = 0
        for row in range(self.category_mapping_table.rowCount()):
            category_id = self.category_mapping_table.item(row, 0).text().strip()
            category_name = self.category_mapping_table.item(row, 1).text().strip()
            if not category_id or not category_name:
                continue
            self.settings.setArrayIndex(saved)
            self.settings.setValue("id", category_id)
            self.settings.setValue("name", category_name)
            saved += 1
        self.settings.endArray()
        self.settings.sync()
        QMessageBox.information(
            self,
            "Категории сохранены",
            f"Сохранено категорий: {saved}",
        )

    def _apply_category_mappings(self):
        mappings = {
            self.category_mapping_table.item(row, 0).text().strip():
            self.category_mapping_table.item(row, 1).text().strip()
            for row in range(self.category_mapping_table.rowCount())
        }
        mappings = {category_id: name for category_id, name in mappings.items() if name}
        if not mappings:
            QMessageBox.warning(
                self, "Нет категорий", "Добавьте хотя бы одну пару ID — название"
            )
            return

        changed = 0
        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        for row in range(self.table.rowCount()):
            category_id = self.table.item(row, 0).data(SOURCE_CATEGORY_ROLE)
            if category_id in mappings:
                self.table.item(row, 1).setText(mappings[category_id])
                changed += 1
        self.table.setSortingEnabled(sorting_enabled)
        QMessageBox.information(
            self,
            "Названия применены",
            f"Обновлено файлов: {changed}",
        )

    def _choose_output(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить KMZ", self.output_file.text(), "KMZ (*.kmz)"
        )
        if filename:
            self.output_file.setText(
                filename if filename.lower().endswith(".kmz") else f"{filename}.kmz"
            )

    def _merge(self):
        output = Path(self.output_file.text().strip()).expanduser()
        if output.suffix.lower() != ".kmz":
            output = output.with_suffix(".kmz")
            self.output_file.setText(str(output))
        if output.exists() and QMessageBox.question(
            self, "Заменить файл?", f"{output.name} уже существует. Заменить?"
        ) != QMessageBox.StandardButton.Yes:
            return
        sources = [
            (
                Path(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)),
                self.table.item(row, 1).text(),
            )
            for row in range(self.table.rowCount())
        ]
        try:
            categories, features = merge_kml_by_category(sources, output)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Не удалось создать KMZ", str(error))
            return
        QMessageBox.information(
            self,
            "KMZ создан",
            f"Сохранено: {output}\nКатегорий: {categories}\nОбъектов: {features}",
        )
