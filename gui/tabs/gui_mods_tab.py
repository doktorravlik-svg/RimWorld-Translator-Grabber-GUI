import logging
import os
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from config.mods_config import ModsConfigManager, get_active_mods
from gui.components.gui_file_colors import FILE_COLORS, FileColorMarker
from gui.constants import (
    PAD_BTN_X,
    PAD_FRAME_X,
    PAD_FRAME_Y,
    PAD_LABEL_X,
    PAD_TREE_X,
    PAD_TREE_Y,
    PAD_X,
    PAD_Y,
)
from gui.gui_i18n import tr
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip


class ModsManagerTab(ttk.Frame):
    def __init__(self, parent, mods_folder: str = "", on_change=None, log_callback=None):
        super().__init__(parent)
        self.mods_folder = mods_folder
        self.on_change = on_change
        self.log_callback = log_callback  # ✅ НОВОЕ: callback для логирования
        self.mods_manager = ModsConfigManager()
        self.color_marker = FileColorMarker()
        # Данные модов
        self.mods_data: list[dict] = []
        self.filtered_mods: list[dict] = []
        # Переменные для фильтрации
        self.search_var = tk.StringVar()
        self.show_active_var = tk.BooleanVar(value=True)
        self.show_inactive_var = tk.BooleanVar(value=True)
        self.show_translation_var = tk.BooleanVar(value=True)
        self.show_regular_var = tk.BooleanVar(value=True)
        # ✅ НОВОЕ: Фильтр для модов с ошибками
        self.show_errors_var = tk.BooleanVar(value=True)
        self._setup_ui()
        # Загружаем моды после инициализации
        self._load_mods()
        # Привязываем событие показа вкладки для обновления списка
        self.bind("<Map>", self._on_tab_shown)
        self._tab_shown_once = False

    def _log(self, message):
        """Логирование через callback или fallback в print"""
        if self.log_callback:
            try:
                self.log_callback(message)
            except (AttributeError, Exception):
                # Callback может быть недоступен во время __init__
                print(f"[ModsManager] {message}")
        else:
            print(f"[ModsManager] {message}")

    def _setup_ui(self):
        """Настройка интерфейса"""
        # Панель поиска и фильтров
        filter_frame = ttk.LabelFrame(self, text=tr("mods_filters", "🔍 Фильтры"))
        filter_frame.pack(fill="x", padx=PAD_FRAME_X, pady=PAD_FRAME_Y)

        # Поиск
        search_frame = ttk.Frame(filter_frame)
        search_frame.pack(fill="x", padx=PAD_X, pady=PAD_Y)
        ttk.Label(search_frame, text=tr("mods_search", "🔍 Поиск:")).pack(
            side="left", padx=PAD_LABEL_X
        )
        self.search_entry = ttk.Entry(
            search_frame, textvariable=self.search_var, width=40, bootstyle="info"
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=PAD_X)
        self.search_entry.bind("<KeyRelease>", self._on_filter_change_debounced)
        ToolTip(self.search_entry, "Введите текст для поиска модов")
        # Кнопка очистки поиска
        btn_clear = ttk.Button(
            search_frame, text="✕", width=3, command=self._clear_search, bootstyle="secondary"
        )
        btn_clear.pack(side="left")
        ToolTip(btn_clear, "Очистить поиск")

        # Чекбоксы фильтров
        checks_frame = ttk.Frame(filter_frame)
        checks_frame.pack(fill="x", padx=PAD_X, pady=PAD_Y)
        chk_active = ttk.Checkbutton(
            checks_frame,
            text=tr("mods_filter_active", "✅ Активные"),
            variable=self.show_active_var,
            command=self._apply_filters,
        )
        chk_active.pack(side="left", padx=PAD_X)
        ToolTip(chk_active, "Показать активные моды")

        chk_inactive = ttk.Checkbutton(
            checks_frame,
            text=tr("mods_filter_inactive", "⬜ Отключенные"),
            variable=self.show_inactive_var,
            command=self._apply_filters,
        )
        chk_inactive.pack(side="left", padx=PAD_X)
        ToolTip(chk_inactive, "Показать отключенные моды")

        chk_trans = ttk.Checkbutton(
            checks_frame,
            text=tr("mods_filter_translations", "🌐 Переводы"),
            variable=self.show_translation_var,
            command=self._apply_filters,
        )
        chk_trans.pack(side="left", padx=PAD_X)
        ToolTip(chk_trans, "Показать моды-переводы")

        chk_regular = ttk.Checkbutton(
            checks_frame,
            text=tr("mods_filter_regular", "📦 Обычные"),
            variable=self.show_regular_var,
            command=self._apply_filters,
        )
        chk_regular.pack(side="left", padx=PAD_X)
        ToolTip(chk_regular, "Показать обычные моды")

        chk_errors = ttk.Checkbutton(
            checks_frame,
            text=tr("mods_filter_errors", "⚠️ С ошибками"),
            variable=self.show_errors_var,
            command=self._apply_filters,
        )
        chk_errors.pack(side="left", padx=PAD_X)
        ToolTip(chk_errors, "Показать моды с ошибками")

        # Кнопки действий
        btn_frame = ttk.Frame(filter_frame)
        btn_frame.pack(fill="x", padx=PAD_X, pady=PAD_Y)
        btn_enable = ttk.Button(
            btn_frame, text=tr("mods_enable_all", "✅ Включить все"), command=self._enable_all
        )
        btn_enable.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_enable, "Включить все моды")

        btn_disable = ttk.Button(
            btn_frame, text=tr("mods_disable_all", "⬜ Отключить все"), command=self._disable_all
        )
        btn_disable.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_disable, "Отключить все моды")

        btn_refresh = ttk.Button(
            btn_frame, text=tr("mods_refresh", "🔄 Обновить список"), command=self._refresh_mods
        )
        btn_refresh.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_refresh, "Обновить список модов")

        btn_save = ttk.Button(
            btn_frame, text=tr("mods_save", "💾 Сохранить"), command=self._save_config
        )
        btn_save.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_save, "Сохранить конфигурацию модов")

        self.stats_label = ttk.Label(filter_frame, text=tr("mods_loading", "Загрузка..."))
        self.stats_label.pack(anchor="w", padx=PAD_X, pady=PAD_Y)

        # Дерево модов
        tree_frame = ttk.LabelFrame(self, text=tr("mods_list", "📋 Список модов"))
        tree_frame.pack(fill="both", expand=True, padx=PAD_TREE_X, pady=PAD_TREE_Y)

        # ✅ ИСПОЛЬЗУЕМ переиспользуемый компонент ScrollableTree
        from gui.components.scrollable_tree import ScrollableTree

        columns = ("active", "name", "type", "version", "author")
        self.tree_widget = ScrollableTree(
            tree_frame,
            columns=columns,
            headings={
                "#0": tr("mods_package_id", "Package ID"),
                "active": tr("mods_status", "Статус"),
                "name": tr("mods_name", "Название"),
                "type": tr("mods_type", "Тип"),
                "version": tr("mods_version", "Версия"),
                "author": tr("mods_author", "Автор"),
            },
            column_widths={
                "#0": 200,
                "active": 60,
                "name": 200,
                "type": 80,
                "version": 80,
                "author": 150,
            },
            show="tree headings",
            selectmode="extended",
        )
        # ✅ Упаковываем ScrollableTree
        self.tree_widget.pack(fill="both", expand=True)
        self.tree_widget.tree.heading("#0", command=lambda: self._sort_by("mod_id"))
        self.tree_widget.tree.heading("active", command=lambda: self._sort_by("is_active"))
        self.tree_widget.tree.heading("name", command=lambda: self._sort_by("name"))
        self.tree_widget.tree.heading("type", command=lambda: self._sort_by("is_translation"))
        self.tree_widget.tree.heading("version", command=lambda: self._sort_by("version"))
        self.tree_widget.tree.heading("author", command=lambda: self._sort_by("author"))
        self.sort_column = None
        self.sort_reverse = False

        self.tree_widget.tree.bind("<Double-1>", self._toggle_selected)

        # Псевдоним для обратной совместимости
        self.tree = self.tree_widget.tree
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(
            label=tr("mods_context_enable", "✅ Включить"),
            command=lambda: self._set_selected_active(True),
        )
        self.context_menu.add_command(
            label=tr("mods_context_disable", "⬜ Отключить"),
            command=lambda: self._set_selected_active(False),
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label=tr("mods_context_copy_id", "📋 Копировать ID"), command=self._copy_mod_id
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label=tr("mods_context_open_folder", "📂 Открыть папку мода"),
            command=self._open_mod_folder,
        )
        self.tree.bind("<Button-3>", self._show_context_menu)

    def _load_mods(self, force_rescan=False):
        self.mods_data.clear()
        if not self.mods_folder:
            self.stats_label.config(text=tr("mods_folder_not_set", "Папка с модами не указана"))
            self._update_tree()
            return
        if not os.path.exists(self.mods_folder):
            self.stats_label.config(
                text=tr("mods_folder_not_exist", "Папка не существует:") + f" {self.mods_folder}"
            )
            self._update_tree()
            return

        # ✅ ИСПОЛЬЗУЕМ КЭШИРОВАНИЕ
        from utils.mod_cache import scan_mods_with_cache

        self._log(f"Загрузка модов из: {self.mods_folder}")

        # Получаем список модов из кэша или сканируем
        mod_paths = scan_mods_with_cache(self.mods_folder, force_rescan=force_rescan)

        active_mods = get_active_mods()
        # ✅ Создаем множество с нижним регистром для регистронезависимого сравнения
        active_mods_lower = {mod_id.lower() for mod_id in active_mods}
        self._log(f"Активных модов в конфиге: {len(active_mods)}")

        # ✅ НОВОЕ: Счётчик проблемных модов
        mods_with_errors = 0

        for mod_path in mod_paths:
            item = os.path.basename(mod_path)
            if not os.path.isdir(mod_path):
                continue

            # Ищем About.xml — проверяем стандартное расположение и подпапки версий
            about_path = self._find_about_xml(mod_path)

            if about_path:
                # Парсим About.xml
                mod_info = self._parse_about(about_path, mod_path)
                mod_info["has_about"] = True
                mod_info["parse_error"] = False
            else:
                # ✅ НОВОЕ: Создаём запись для мода без About.xml
                self._log(f"⚠️ Нет About.xml: {item}")
                mod_info = {
                    "mod_id": item,
                    "name": f"⚠️ {item} (нет About.xml)",
                    "path": mod_path,
                    "version": "?",
                    "author": "?",
                    "is_translation": False,
                    "parent_mod_id": None,
                    "is_active": item.lower() in active_mods_lower,
                    "has_about": False,
                    "parse_error": True,
                }
                mods_with_errors += 1

            # ✅ Регистронезависимое сравнение packageId
            mod_info["is_active"] = mod_info.get("is_active", False) or (
                mod_info["mod_id"].lower() in active_mods_lower
            )
            mods_count = len(self.mods_data) + 1
            safe_name = mod_info["name"].encode("ascii", "replace").decode("ascii")
            self._log(f"[{mods_count}] {safe_name} active={mod_info['is_active']}")
            self.mods_data.append(mod_info)

        # Сортируем по имени
        self.mods_data.sort(key=lambda x: x.get("name", "").lower())
        self._log(f"Total mods: {len(self.mods_data)}")
        if mods_with_errors > 0:
            self._log(f"⚠️ Модов с проблемами: {mods_with_errors}")
        self._apply_filters()

    def _find_about_xml(self, mod_path: str) -> str | None:
        """
        Ищет About.xml в папке мода.

        Проверяет:
        1. mod_path/About/About.xml (стандарт)
        2. mod_path/{1.6,1.5,1.4,1.3}/About/About.xml (версионные)
        3. mod_path/About.xml (в корне)

        Returns:
            Путь к About.xml или None
        """
        variants = [
            os.path.join(mod_path, "About", "About.xml"),
        ]

        # Проверяем подпапки версий
        for version in ["1.6", "1.5", "1.4", "1.3", "1.2"]:
            variants.append(os.path.join(mod_path, version, "About", "About.xml"))

        # Проверяем корень
        variants.append(os.path.join(mod_path, "About.xml"))

        for variant in variants:
            if os.path.exists(variant):
                return variant

        return None

    def _parse_about(self, about_path: str, mod_path: str) -> dict:
        """Парсить About.xml"""
        import xml.etree.ElementTree as ET

        info = {
            "mod_id": os.path.basename(mod_path),
            "name": os.path.basename(mod_path),
            "path": mod_path,
            "version": "",
            "author": "",
            "is_translation": False,
            "parent_mod_id": None,
        }
        try:
            tree = ET.parse(about_path)
            root = tree.getroot()
            for field in ["packageId", "name", "author", "version"]:
                elem = root.find(field)
                if elem is not None and elem.text:
                    key = "mod_id" if field == "packageId" else field
                    info[key] = elem.text.strip()
            target_mod = root.find("targetMod")
            if target_mod is not None:
                target_id = target_mod.find("packageId")
                if target_id is not None and target_id.text:
                    info["is_translation"] = True
                    info["parent_mod_id"] = target_id.text.strip()
        except ET.ParseError as e:
            logging.getLogger(__name__).warning(f"Ошибка парсинга {about_path}: {e}")
            # ✅ НОВОЕ: При ошибке парсинга помечаем мод как проблемный
            info["parse_error"] = True
            info["name"] = f"⚠️ {info['name']} (ошибка XML)"
        except Exception as e:
            logging.getLogger(__name__).error(f"Неожиданная ошибка при парсинге {about_path}: {e}")
            info["parse_error"] = True
            info["name"] = f"⚠️ {info['name']} (ошибка)"
        return info

    def _apply_filters(self, event=None):
        """Применить фильтры"""
        search_text = self.search_var.get().lower()
        self.filtered_mods.clear()
        for mod in self.mods_data:
            # Фильтр по поиску
            if search_text:
                if (
                    search_text not in mod.get("name", "").lower()
                    and search_text not in mod.get("mod_id", "").lower()
                ):
                    continue
            # ✅ НОВОЕ: Фильтр по ошибкам
            if mod.get("parse_error", False) and not self.show_errors_var.get():
                continue
            # Фильтр по статусу
            if mod["is_active"] and not self.show_active_var.get():
                continue
            if not mod["is_active"] and not self.show_inactive_var.get():
                continue
            if mod["is_translation"] and not self.show_translation_var.get():
                continue
            if not mod["is_translation"] and not self.show_regular_var.get():
                continue
            self.filtered_mods.append(mod)
        self._update_tree()
        self._update_stats()

    def _update_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for status, color in FILE_COLORS.items():
            self.tree.tag_configure(status, background=color, foreground="white")
        self.tree.tag_configure("active_mod", background="#2d5016", foreground="white")
        self.tree.tag_configure("inactive_mod", background="#3a3a3a", foreground="gray")
        # ✅ НОВОЕ: Тег для модов с ошибками
        self.tree.tag_configure("error_mod", background="#5c2020", foreground="#ff9999")

        for mod in self.filtered_mods:
            has_error = mod.get("parse_error", False)
            status = "✅" if mod["is_active"] else "⬜"

            if has_error:
                # ✅ Мод с ошибкой — особый стиль
                mod_type = "⚠️ Ошибка"
                tag = "error_mod"
            else:
                mod_type = (
                    tr("mods_type_translation", "🌐 Перевод")
                    if mod["is_translation"]
                    else tr("mods_type_regular", "📦 Обычный")
                )
                if mod["is_active"]:
                    tag = "active_mod"
                else:
                    tag = "inactive_mod"
            self.tree.insert(
                "",
                "end",
                text=mod["mod_id"],
                values=(
                    status,
                    mod["name"],
                    mod_type,
                    mod.get("version", ""),
                    mod.get("author", ""),
                ),
                tags=(tag,),
            )

    def _update_stats(self):
        """Обновить статистику"""
        total = len(self.mods_data)
        active = sum(1 for m in self.mods_data if m["is_active"])
        translations = sum(1 for m in self.mods_data if m["is_translation"])
        with_errors = sum(1 for m in self.mods_data if m.get("parse_error", False))
        filtered = len(self.filtered_mods)
        self.stats_label.config(
            text=tr("mods_stats", "Всего:")
            + f" {total} | "
            + tr("mods_stats_active", "Активных:")
            + f" {active} | "
            + tr("mods_stats_translations", "Переводов:")
            + f" {translations} | "
            + tr("mods_stats_errors", "Ошибок:")
            + f" {with_errors} | "
            + tr("mods_stats_shown", "Показано:")
            + f" {filtered}"
        )

    def _toggle_selected(self, event):
        """Переключить статус выбранных модов"""
        selection = self.tree.selection()
        if not selection:
            return
        for item_id in selection:
            item = self.tree.item(item_id)
            mod_id = item["text"]
            for mod in self.mods_data:
                if mod["mod_id"] == mod_id:
                    mod["is_active"] = not mod["is_active"]
                    break
        self._update_tree()
        self._update_stats()

    def _set_selected_active(self, active: bool):
        selection = self.tree.selection()
        if not selection:
            return
        for item_id in selection:
            item = self.tree.item(item_id)
            mod_id = item["text"]
            for mod in self.mods_data:
                if mod["mod_id"] == mod_id:
                    mod["is_active"] = active
                    break
        self._update_tree()
        self._update_stats()

    def _enable_all(self):
        for mod in self.mods_data:
            mod["is_active"] = True
        self._update_tree()
        self._update_stats()

    def _disable_all(self):
        for mod in self.mods_data:
            mod["is_active"] = False
        self._update_tree()
        self._update_stats()

    def _save_config(self):
        active_mods = {mod["mod_id"] for mod in self.mods_data if mod["is_active"]}
        from mods_config import get_active_mods, set_active_mods

        previous_active_mods = get_active_mods()
        try:
            if set_active_mods(active_mods):
                logging.getLogger(__name__).info(
                    f"Успешно сохранено {len(active_mods)} активных модов"
                )
                messagebox.showinfo(
                    tr("mods_save_success_title", "Успех"),
                    tr("mods_save_success", "Сохранено")
                    + f" {len(active_mods)} "
                    + tr("mods_save_success_suffix", "активных модов"),
                )
                if self.on_change:
                    self.on_change()
            else:
                raise Exception("set_active_mods вернул False")
        except Exception as e:
            logging.getLogger(__name__).error(f"Ошибка сохранения конфигурации: {e}")
            # Пытаемся откатить изменения
            try:
                set_active_mods(previous_active_mods)
                logging.getLogger(__name__).info("Выполнен откат к предыдущей конфигурации")
            except Exception as rollback_error:
                logging.getLogger(__name__).error(f"Ошибка при откате: {rollback_error}")
            messagebox.showerror(
                tr("mods_save_error_title", "Ошибка"),
                tr("mods_save_error", "Не удалось сохранить конфигурацию:") + f" {e}",
            )

    def _refresh_mods(self):
        """Обновить список модов"""
        self._load_mods(force_rescan=True)

    def _clear_search(self):
        """Очистить поиск и показать все моды"""
        self.search_var.set("")
        self._apply_filters()

    def _on_filter_change_debounced(self, event=None):
        """Debounce для фильтрации модов (300мс задержка)"""
        if self._filter_debounce_timer:
            self.after_cancel(self._filter_debounce_timer)
        self._filter_debounce_timer = self.after(300, self._apply_filters)

    def _on_filter_change(self, event):
        """Обработка изменения фильтра"""
        self._apply_filters()

    def _sort_by(self, column):
        """Сортировка по столбцу"""
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        # Сортируем данные
        self.filtered_mods.sort(
            key=lambda x: x.get(column, ""),
            reverse=self.sort_reverse,
        )
        # Обновляем дерево
        self._update_tree()
        # Обновляем заголовок столбца
        arrow = " ▲" if self.sort_reverse else " ▼"
        self.tree.heading(column, text=self.tree.heading(column)["text"].rstrip(" ▲▼") + arrow)

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _copy_mod_id(self):
        selection = self.tree.selection()
        if selection:
            mod_id = self.tree.item(selection[0])["text"]
            self.clipboard_clear()
            self.clipboard_append(mod_id)

    def _open_mod_folder(self):
        selection = self.tree.selection()
        if not selection:
            return
        item = self.tree.item(selection[0])
        mod_id = item["text"]
        for mod in self.filtered_mods:
            if mod["mod_id"] == mod_id:
                mod_path = mod["path"]
                if os.path.exists(mod_path):
                    os.startfile(mod_path)
                else:
                    from tkinter import messagebox

                    messagebox.showwarning(
                        tr("mods_folder_warning_title", "Предупреждение"),
                        tr("mods_folder_warning", "Папка мода не найдена:") + f"\n{mod_path}",
                    )
                break

    def set_mods_folder(self, folder: str):
        """Установить папку с модами и обновить список"""
        if self.mods_folder != folder:
            self.mods_folder = folder
            self._load_mods()

    def update_mods_folder(self, folder: str):
        """Обновить папку с модами (вызывается извне)
        Deprecated: используйте set_mods_folder вместо этого метода.
        """
        self.set_mods_folder(folder)

    def _on_tab_shown(self, event=None):
        """Обновить список модов при первом показе вкладки"""
        if not self._tab_shown_once:
            self._tab_shown_once = True
            self._load_mods()
            # Debug: логируем первый показ вкладки
            if hasattr(self, "_log_callback") and self._log_callback:
                try:
                    pass
                    # Если есть debug_manager, логируем
                except:
                    pass
