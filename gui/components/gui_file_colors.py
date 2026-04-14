# gui_file_colors.py - Цветовая маркировка файлов
"""
Модуль для цветовой маркировки файлов переводов.
Цвета показывают статус перевода:
- Зелёный - файл полностью переведён
- Жёлтый - частичный перевод
- Красный - есть ошибки
- Серый - не переведён
"""

import os
import xml.etree.ElementTree as ET

try:
    from gui.gui_i18n import tr
except ImportError:
    # Fallback если tr недоступен
    tr = lambda k, d=None: d or k

# Цветовая схема
FILE_COLORS = {
    "complete": "#27ae60",  # Зелёный - полностью переведён
    "partial": "#f39c12",  # Жёлтый - частичный перевод
    "error": "#e74c3c",  # Красный - есть ошибки
    "empty": "#5d6d7e",  # Тёмно-серый - не переведён (улучшен для читаемости)
    "missing": "#805f67",  # Тёмно-серый - файл отсутствует
    "dlc": "#9b59b6",  # Фиолетовый - официальное DLC
    "separate": "#3498db",  # Синий - отдельный мод-перевод
}


class FileColorMarker:
    """Класс для определения цвета файла на основе его содержимого"""

    def __init__(self):
        self._color_cache: dict[str, str] = {}

    def get_file_color(self, file_path: str, source_file_path: str | None = None) -> str:
        """
        Определить цвет файла.

        Args:
            file_path: Путь к файлу перевода
            source_file_path: Путь к исходному файлу (для сравнения)

        Returns:
            HEX цвет для файла
        """
        if file_path in self._color_cache:
            return self._color_cache[file_path]

        color = self._determine_color(file_path, source_file_path)
        self._color_cache[file_path] = color
        return color

    def _determine_color(self, file_path: str, source_file_path: str | None = None) -> str:
        """Определить цвет файла"""
        if not os.path.exists(file_path):
            return FILE_COLORS["missing"]

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Считаем записи
            total_entries = 0
            filled_entries = 0
            empty_entries = 0
            has_errors = False

            for child in root:
                if child.tag not in ("LanguageData", "Keyed"):
                    total_entries += 1
                    value = child.text or ""
                    if value.strip():
                        filled_entries += 1
                    else:
                        empty_entries += 1

            # Проверяем на ошибки XML
            if has_errors:
                return FILE_COLORS["error"]

            # Определяем статус
            if total_entries == 0:
                return FILE_COLORS["empty"]

            if filled_entries == total_entries:
                return FILE_COLORS["complete"]

            if filled_entries > 0:
                return FILE_COLORS["partial"]

            return FILE_COLORS["empty"]

        except ET.ParseError:
            return FILE_COLORS["error"]
        except Exception:
            return FILE_COLORS["error"]

    def get_file_color_info(self, file_path: str, source_file_path: str | None = None) -> dict:
        """
        Получить полную информацию о цвете файла.

        Returns:
            Словарь с информацией о статусе файла
        """
        color = self.get_file_color(file_path, source_file_path)

        status_names = {
            FILE_COLORS["complete"]: "complete",
            FILE_COLORS["partial"]: "partial",
            FILE_COLORS["error"]: "error",
            FILE_COLORS["empty"]: "empty",
            FILE_COLORS["missing"]: "missing",
            FILE_COLORS["dlc"]: "dlc",
        }

        status_descriptions = {
            "complete": tr("filecolor_complete", "Полностью переведён"),
            "partial": tr("filecolor_partial", "Частичный перевод"),
            "error": tr("filecolor_error", "Ошибка в файле"),
            "empty": tr("filecolor_empty", "Не переведён"),
            "missing": tr("filecolor_missing", "Файл отсутствует"),
            "dlc": tr("filecolor_dlc", "Официальное DLC"),
        }

        status_name = status_names.get(color, "unknown")

        return {
            "color": color,
            "status": status_name,
            "description": status_descriptions.get(status_name, "Неизвестно"),
        }

    def clear_cache(self):
        """Очистить кэш цветов"""
        self._color_cache.clear()


def apply_colors_to_tree(tree, file_paths: list[str], source_folder: str | None = None):
    """
    Применить цветовую маркировку к Treeview.

    Args:
        tree: Treeview виджет
        file_paths: Список путей к файлам
        source_folder: Папка с исходными файлами
    """
    marker = FileColorMarker()

    for item_id in tree.get_children():
        item = tree.item(item_id)
        # Получаем путь из значений
        values = item.get("values", [])
        if values:
            file_path = values[0] if isinstance(values[0], str) else str(values[0])
            full_path = os.path.join(source_folder, file_path) if source_folder else file_path

            color_info = marker.get_file_color_info(full_path)
            tree.item(item_id, tags=(color_info["status"],))

    # Настраиваем теги
    for status, color in FILE_COLORS.items():
        tree.tag_configure(status, background=color, foreground="white")


def get_color_legend() -> list[tuple[str, str]]:
    """
    Получить легенду цветов.

    Returns:
        Список кортежей (цвет, описание)
    """
    return [
        (FILE_COLORS["complete"], "✅ Полностью переведён"),
        (FILE_COLORS["partial"], "⚠️ Частичный перевод"),
        (FILE_COLORS["error"], "❌ Ошибка в файле"),
        (FILE_COLORS["empty"], "⬜ Не переведён"),
        (FILE_COLORS["missing"], "➖ Файл отсутствует"),
    ]
