# gui/core/i18n_manager.py
"""
Менеджер интернационализации (i18n).

Отвечает за:
- Применение языка ко всему UI
- Обновление текстов виджетов без пересоздания
- Перестроение меню и вкладок при смене языка
- Уведомление диалогов о смене языка

Пример использования:
    manager = I18nManager(root, notebook, status_bar, config, log_fn)
    manager.apply_language("en")
    manager.register_widget(label, "tab_translation")
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

import ttkbootstrap as ttk
from gui.core.i18n_updater import (
    build_translation_map,
    setup_auto_update,
    update_all_widgets_in_container,
)
from gui.gui_i18n import i18n


class I18nManager:
    """
    Централизованный менеджер управления языком интерфейса.

    Args:
        root: Главное окно приложения
        notebook: Notebook с вкладками
        status_bar: Панель статуса (опционально)
        config: Словарь конфигурации
        log_fn: Функция логирования (опционально)
    """

    def __init__(
        self,
        root: tk.Tk,
        notebook: ttk.Notebook,
        status_bar: Any | None = None,
        config: dict | None = None,
        log_fn: Callable[[str], None] | None = None,
    ):
        self.root = root
        self.notebook = notebook
        self.status_bar = status_bar
        self.config = config or {}
        self.log_fn = log_fn
        self._registered_widgets: list[tuple[Any, str, str]] = []

        # Список названий вкладок для перестроения
        self._tab_i18n_keys = [
            "tab_translation",
            "tab_verification",
            "tab_duplicates",
            "tab_settings",
            "tab_mods",
            "tab_filters",
            "tab_dependencies",
            "tab_editor",
            "tab_log",
        ]
        self._tab_default_texts = [
            "🌐 Перевод",
            "✅ Верификация",
            "🔄 Дубликаты",
            "⚙️ Настройки",
            "📦 Моды",
            "📝 Фильтры",
            "🔗 Зависимости",
            "✏️ Редактор",
            "📋 Лог",
        ]

    def initialize(self) -> None:
        """Инициализировать систему автоматического обновления переводов"""
        build_translation_map()

        if self.notebook:
            setup_auto_update(self.notebook)
        if self.status_bar:
            setup_auto_update(self.status_bar)

    def load_saved_language(self) -> None:
        """Загрузить сохранённый язык и применить"""
        # Сбрасываем на ru по умолчанию перед загрузкой
        i18n.current_language = "ru"

        saved = self.config.get("ui_language", "ru")
        if saved and saved != i18n.current_language:
            if i18n.set_language(saved):
                self.apply_language()
                self._log(f"Загружен язык: {i18n.get_language_name(saved)}")

    def save_current_language(self) -> None:
        """Сохранить текущий язык в конфигурацию"""
        self.config["ui_language"] = i18n.current_language
        try:
            from config.config_manager import get_config_manager

            config_mgr = get_config_manager()
            config_mgr.set("ui_language", i18n.current_language)
        except OSError:
            pass

    def apply_language(self) -> None:
        """
        Применить язык к интерфейсу — обновление текстов без пересоздания UI.
        """
        try:
            # Перестраиваем карту переводов для текущего языка
            build_translation_map()

            # Запоминаем текущую вкладку
            try:
                current_tab = self.notebook.index("current")
            except Exception:
                current_tab = 0

            # Обновляем заголовок окна
            self._update_window_title()

            # Перестраиваем меню с новым языком
            self._rebuild_menu()

            # Обновляем названия вкладок
            self._rebuild_tabs()

            # Обновляем статус-бар
            self._apply_language_to_statusbar()

            # Автоматически обновляем все виджеты внутри вкладок
            updated = update_all_widgets_in_container(self.notebook)
            if updated > 0:
                self._log(f"Обновлено {updated} элементов перевода")

            # Возвращаемся на ту же вкладку
            try:
                self.notebook.select(current_tab)
            except Exception:
                pass

            # Отправляем сигнал всем диалогам о смене языка
            self._notify_dialogs_language_change()

            self._log("Язык: " + i18n.get_language_name(i18n.current_language))

        except Exception as e:
            print("Ошибка применения языка:", e)
            import traceback

            traceback.print_exc()

    def _update_window_title(self) -> None:
        """Обновить заголовок окна"""
        try:
            self.root.title(i18n.tr("gui_root_title", "RimWorld Translator Grabber V2+"))
        except Exception:
            pass

    def _rebuild_menu(self) -> None:
        """
        Перестроить главное меню с новым языком.
        Вызывает callback из главного окна.
        """
        # Этот метод вызывает внешний rebuild через callback
        # чтобы избежать циклических импортов
        if hasattr(self, "_rebuild_menu_callback"):
            try:
                self._rebuild_menu_callback()
            except Exception as e:
                print("Ошибка перестроения меню:", e)

    def set_rebuild_menu_callback(self, callback: Callable[[], None]) -> None:
        """Установить callback для перестроения меню"""
        self._rebuild_menu_callback = callback

    def _rebuild_tabs(self) -> None:
        """Обновить названия всех вкладок"""
        try:
            tab_count = self.notebook.index("end")

            for i, (key, default) in enumerate(zip(self._tab_i18n_keys, self._tab_default_texts)):
                if i < tab_count:
                    try:
                        name = i18n.tr(key, default)
                        self.notebook.tab(i, text=name)
                    except Exception:
                        pass

        except Exception as e:
            print("Ошибка перестройки вкладок:", e)

    def _apply_language_to_statusbar(self) -> None:
        """Обновить тексты в статус-баре"""
        if not self.status_bar:
            return

        try:
            if hasattr(self.status_bar, "status_label"):
                self.status_bar.status_label.config(text=i18n.tr("status_ready", "Готов"))
            if hasattr(self.status_bar, "mods_label"):
                self.status_bar.mods_label.config(text=i18n.tr("mods_count_zero", "Модов: 0"))
            if hasattr(self.status_bar, "translated_label"):
                self.status_bar.translated_label.config(
                    text=i18n.tr("translated_count_zero", "Переведено: 0")
                )
            if hasattr(self.status_bar, "errors_label"):
                self.status_bar.errors_label.config(text=i18n.tr("errors_count_zero", "Ошибок: 0"))
            if hasattr(self.status_bar, "warnings_label"):
                self.status_bar.warnings_label.config(
                    text=i18n.tr("warnings_count_zero", "Предупреждений: 0")
                )
            if hasattr(self.status_bar, "last_action_label"):
                self.status_bar.last_action_label.config(
                    text=i18n.tr("last_action_none", "Последнее: -")
                )
        except Exception:
            pass

    def _notify_dialogs_language_change(self) -> None:
        """Уведомить все открытые диалоги о смене языка"""
        try:
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.event_generate("<<LanguageChanged>>")
        except Exception:
            pass

    def register_widget(self, widget: Any, i18n_key: str, default_text: str) -> None:
        """
        Зарегистрировать виджет для быстрого обновления (без сканирования дерева).

        Args:
            widget: Tkinter виджет
            i18n_key: Ключ перевода
            default_text: Текст по умолчанию
        """
        self._registered_widgets.append((widget, i18n_key, default_text))
        try:
            widget.config(text=i18n.tr(i18n_key, default_text))
        except Exception:
            pass

    def update_registered_widgets(self) -> int:
        """
        Обновить текст всех зарегистрированных виджетов.
        Это намного быстрее, чем сканирование всего дерева.
        """
        count = 0
        for widget, key, default in self._registered_widgets:
            try:
                new_text = i18n.tr(key, default)
                if widget.cget("text") != new_text:
                    widget.config(text=new_text)
                    count += 1
            except Exception:
                pass
        return count

    def update_widget_text(self, widget: Any) -> bool:
        """
        Обновить текст конкретного виджета.

        Args:
            widget: Зарегистрированный виджет

        Returns:
            True если текст обновлён, False если нет
        """
        try:
            if hasattr(widget, "_i18n_key"):
                key = widget._i18n_key
                default = getattr(widget, "_i18n_default", widget.cget("text"))
                new_text = i18n.tr(key, default)
                widget.config(text=new_text)
                return True
        except Exception:
            pass
        return False

    def _log(self, message: str) -> None:
        """Логировать сообщение"""
        if self.log_fn:
            self.log_fn(message)
