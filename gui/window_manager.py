"""
Window Manager - модуль управления окном и визуальными элементами.

Отвечает за:
- Статусную строку
- Прогресс-бар
- Управление темами ttkbootstrap
- Шрифты и цвета
"""

from typing import Optional
from loguru import logger


class GUIWindowManager:
    """Управление окном, статусом, прогрессом и темами."""

    def __init__(self, root, config: dict):
        """
        Args:
            root: Корневой элемент ttkbootstrap Window
            config: Словарь конфигурации
        """
        self.root = root
        self.config = config
        self._status_label = None
        self._progress_var = None
        self._progress_bar = None
        self._theme_var = None

    def set_status(self, message: str) -> None:
        """
        Устанавливает текст статусной строки.

        Args:
            message: Текст статуса
        """
        if self._status_label:
            try:
                self._status_label.config(text=message)
            except Exception:
                pass  # Виджет мог быть уничтожен

    def start_progress(self) -> None:
        """Запускает отображение прогресс-бара."""
        if self._progress_var:
            self._progress_var.set(0)
        if self._progress_bar:
            self._progress_bar.pack(fill="x", padx=5, pady=2)

    def stop_progress(self) -> None:
        """Останавливает и скрывает прогресс-бар."""
        if self._progress_bar:
            self._progress_bar.pack_forget()

    def set_progress(self, value: int) -> None:
        """
        Устанавливает значение прогресса.

        Args:
            value: Значение от 0 до 100
        """
        if self._progress_var:
            self._progress_var.set(value)

    def register_progress_widgets(self, progress_var, progress_bar) -> None:
        """
        Регистрирует виджеты прогресс-бара.

        Args:
            progress_var: Переменная для значения прогресса
            progress_bar: Виджет прогресс-бара
        """
        self._progress_var = progress_var
        self._progress_bar = progress_bar

    def register_status_label(self, label) -> None:
        """
        Регистрирует виджет статусной строки.

        Args:
            label: Виджет Label для статуса
        """
        self._status_label = label

    def register_theme_var(self, theme_var) -> None:
        """
        Регистрирует переменную темы.

        Args:
            theme_var: Переменная для текущей темы
        """
        self._theme_var = theme_var

    def apply_ttkbootstrap_theme(self, theme_name: str) -> None:
        """
        Применяет тему ttkbootstrap.

        Args:
            theme_name: Имя темы
        """
        try:
            from gui.styling.theme_manager import apply_theme
            apply_theme(self.root, theme_name)
        except Exception as e:
            logger.error(f"Ошибка применения темы: {e}")

    def get_font_tuple(self, key: str, default_family: str, default_size: int) -> tuple:
        """
        Получает настройки шрифта из конфигурации.

        Args:
            key: Ключ шрифта (например 'default_font')
            default_family: Семейство шрифта по умолчанию
            default_size: Размер шрифта по умолчанию

        Returns:
            Кортеж (family, size)
        """
        font_config = self.config.get(key, {})
        family = font_config.get("family", default_family)
        size = font_config.get("size", default_size)
        return (family, size)

    def apply_fonts(self) -> None:
        """Применяет шрифты из конфигурации ко всем виджетам."""
        try:
            from gui.styling.theme_manager import apply_fonts
            apply_fonts(self.root, self.config)
        except Exception as e:
            logger.error(f"Ошибка применения шрифтов: {e}")

    def apply_colors(self) -> None:
        """Применяет пользовательские цвета из конфигурации."""
        try:
            from gui.styling.theme_manager import apply_colors
            apply_colors(self.root, self.config)
        except Exception as e:
            logger.error(f"Ошибка применения цветов: {e}")

    def change_theme(self, theme_name: str, callback=None) -> None:
        """
        Переключает тему оформления.

        Args:
            theme_name: Имя новой темы
            callback: Callback после смены темы
        """
        try:
            from gui.styling.theme_manager import change_theme
            change_theme(self.root, theme_name)

            # Обновляем шрифты и цвета
            self.apply_fonts()
            self.apply_colors()

            if callback:
                callback(theme_name)
        except Exception as e:
            logger.error(f"Ошибка смены темы: {e}")
