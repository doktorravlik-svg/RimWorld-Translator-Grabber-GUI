# gui/core/tab_manager.py
"""
Управление вкладками для RimWorld Translator Grabber.

Отвечает за:
- Регистрацию всех вкладок
- Скрытие/показ вкладок
- Контекстное меню вкладок
- Сохранение состояния в конфиге
"""

import tkinter as tk
from tkinter import Menu

from gui.gui_i18n import tr


class TabManager:
    """
    Менеджер вкладок notebook.

    Args:
        notebook: ttk.Notebook
        config: Словарь конфигурации
        save_callback: Функция сохранения конфига
        log_callback: Функция логирования
    """

    def __init__(self, notebook, config: dict, save_callback, log_callback=None):
        self.notebook = notebook
        self.config = config
        self.save_callback = save_callback
        self.log_callback = log_callback

        # Все зарегистрированные вкладки: {name: widget}
        self.all_tabs: dict[str, tk.Widget] = {}
        # Скрытые вкладки
        self.hidden_tabs: set[str] = set(config.get("hidden_tabs", []))
        # Меню управления вкладками
        self.tabs_menu: Menu | None = None

    def register_tab(self, name: str, widget: tk.Widget):
        """
        Зарегистрировать вкладку.

        Args:
            name: Отображаемое имя вкладки
            widget: Виджет вкладки
        """
        self.all_tabs[name] = widget

    def register_and_add(self, name: str, widget: tk.Widget):
        """
        Зарегистрировать и добавить вкладку в notebook.

        Args:
            name: Отображаемое имя вкладки
            widget: Виджет вкладки
        """
        self.register_tab(name, widget)
        self.notebook.add(widget, text=name)

    def apply_hidden_state(self):
        """Применить сохранённое состояние скрытых вкладок"""
        for tab_name in self.hidden_tabs:
            if tab_name in self.all_tabs:
                self.notebook.hide(self.all_tabs[tab_name])

    def set_tabs_menu(self, menu: Menu):
        """
        Установить меню для управления вкладками.

        Args:
            menu: tk.Menu для управления вкладками
        """
        self.tabs_menu = menu
        self._update_tabs_menu()

    def on_tab_right_click(self, event):
        """
        Обработка правого клика на вкладке.

        Args:
            event: Событие Tkinter
        """
        current_tab = self.notebook.select()
        if not current_tab:
            return
        try:
            tab_text = self.notebook.tab(current_tab, "text")
        except (tk.TclError, KeyError):
            return

        context_menu = tk.Menu(self.notebook.master, tearoff=0)
        context_menu.add_command(
            label=f"👁 Скрыть '{tab_text}'", command=lambda: self.hide_tab(tab_text)
        )
        context_menu.add_command(
            label=tr("tab_manager_show_all_tabs", "🔄 Показать все вкладки"),
            command=self.show_all_tabs,
        )
        context_menu.post(event.x_root, event.y_root)

    def hide_tab(self, tab_name: str):
        """
        Скрыть вкладку.

        Args:
            tab_name: Имя вкладки
        """
        if tab_name not in self.all_tabs:
            return
        widget = self.all_tabs[tab_name]
        self.notebook.hide(widget)
        self.hidden_tabs.add(tab_name)
        self.config["hidden_tabs"] = list(self.hidden_tabs)
        self.save_callback()
        self._update_tabs_menu()
        if self.log_callback:
            self.log_callback(f"Вкладка скрыта: {tab_name}")

    def show_tab(self, tab_name: str):
        """
        Показать скрытую вкладку.

        Args:
            tab_name: Имя вкладки
        """
        if tab_name not in self.all_tabs:
            return
        widget = self.all_tabs[tab_name]
        self.notebook.add(widget, text=tab_name)
        self.hidden_tabs.discard(tab_name)
        self.config["hidden_tabs"] = list(self.hidden_tabs)
        self.save_callback()
        self._update_tabs_menu()
        if self.log_callback:
            self.log_callback(f"Вкладка показана: {tab_name}")

    def show_all_tabs(self):
        """Показать все вкладки"""
        for tab_name in list(self.hidden_tabs):
            self.show_tab(tab_name)
        self.hidden_tabs.clear()
        self.config["hidden_tabs"] = []
        self.save_callback()
        self._update_tabs_menu()
        if self.log_callback:
            self.log_callback("Все вкладки показаны")

    def _update_tabs_menu(self):
        """Обновить меню управления вкладками"""
        if self.tabs_menu is None:
            return
        items = self.tabs_menu.index("end")
        if items and items > 1:
            for i in range(items, 1, -1):
                self.tabs_menu.delete(i)
        self.tabs_menu.add_separator()
        for tab_name in self.all_tabs.keys():
            is_hidden = tab_name in self.hidden_tabs
            if is_hidden:
                self.tabs_menu.add_command(
                    label=f"✅ {tab_name} (скрыта)", command=lambda t=tab_name: self.show_tab(t)
                )
            else:
                self.tabs_menu.add_command(
                    label=f"   {tab_name}", command=lambda t=tab_name: self.hide_tab(t)
                )
