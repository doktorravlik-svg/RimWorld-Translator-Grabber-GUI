# gui_dependencies.py
"""
Модуль вкладки "Зависимости" для GUI RimWorld Translator Grabber.

Содержит:
- Настройку вкладки зависимостей переводов
- Методы анализа и визуализации дерева зависимостей
- Экспорт отчётов о зависимостях
"""

import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from gui.constants import (
    FONT_SMALL,
    PAD_BTN_X,
    PAD_ENTRY_X,
    PAD_FRAME_X,
    PAD_FRAME_Y,
    PAD_LABEL_X,
    PAD_TREE_X,
    PAD_TREE_Y,
    PAD_X,
    SEARCH_DEBOUNCE_MS,
)
from gui.gui_i18n import tr
from ttkbootstrap.constants import *
from ttkbootstrap.widgets.tooltip import ToolTip


class DependenciesTab:
    """
    Класс для управления вкладкой "Зависимости" в GUI.

    Предоставляет:
    - Визуализацию дерева зависимостей переводов
    - Анализ статусов переводов
    - Фильтрацию дерева (поиск + статусы + типы переводов)
    - Сортировку по столбцам (клик по заголовку)
    - Экспорт отчётов
    """

    # ✅ Порядок статусов при сортировке по столбцу "Статус"
    _STATUS_RANK = {
        "missing": 0,
        "missing_parent": 1,
        "version_mismatch": 2,
        "outdated": 3,
        "up_to_date": 4,
        "custom": 5,
        "unknown": 6,
    }

    def __init__(
        self,
        parent,
        config,
        log_callback,
        set_status_callback,
        start_progress_callback=None,
        stop_progress_callback=None,
        set_progress_callback=None,
    ):
        """
        Инициализация вкладки зависимостей.

        Args:
            parent: Родительский виджет (ttk.Frame)
            config: Словарь конфигурации
            log_callback: Функция для логирования сообщений
            set_status_callback: Функция для установки статуса
            start_progress_callback: Функция для запуска прогресс бара
            stop_progress_callback: Функция для остановки прогресс бара
            set_progress_callback: Функция для установки значения прогресс бара
        """
        self.parent = parent
        self.config = config
        self.log = log_callback
        self.set_status = set_status_callback
        self.start_progress = start_progress_callback
        self.stop_progress = stop_progress_callback
        self.set_progress = set_progress_callback

        # ✅ НОВОЕ: Debounced обновитель прогресса
        self._progress_updater = None

        # Виджеты вкладки
        self.mods_folder_entry = None
        self.dep_tree = None
        self.stats_label = None

        # ✅ НОВОЕ: Состояние фильтров/сортировки/поиска (инициализируется в setup_ui)
        self._filter_states = {}
        self._legend_canvases = {}  # Ссылки на Canvas индикаторы легенды
        self._legend_indicators = {}  # Ссылки на Label индикаторы легенды
        self._legend_visible = True  # Состояние легенды
        self._all_tree_items = []  # Все элементы дерева (для фильтрации)

        # ✅ НОВОЕ: Мета-данные элементов дерева для фильтров и сортировки
        self._items_meta = {}  # item_id -> {label, values, status, type_tag, kind}
        self._items_parent = {}  # item_id -> item_id родителя (или "")
        self._sort_column = None  # Текущий столбец сортировки (None — без сортировки)
        self._sort_reverse = False  # Направление сортировки
        self._heading_base = {}  # Исходные тексты заголовков (для стрелок ▲/▼)
        self._search_var = tk.StringVar()  # Текст поиска
        self._search_entry = None
        self._shown_label = None
        self._filter_debounce_timer = None
        self._gauge_base_colors = {}  # tag -> исходный bootstyle карточки статистики

        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса вкладки"""
        # Фрейм для выбора папки
        folder_frame = ttk.Frame(self.parent)
        folder_frame.grid(
            row=0, column=0, columnspan=3, sticky="ew", padx=PAD_FRAME_X, pady=PAD_FRAME_Y
        )
        folder_frame.columnconfigure(1, weight=1)

        # Выбор папки с модами
        ttk.Label(folder_frame, text=tr("deps_mods_folder", "Папка с модами:")).grid(
            row=0, column=0, padx=PAD_LABEL_X
        )

        self.mods_folder_entry = ttk.Entry(folder_frame, width=60)
        self.mods_folder_entry.grid(row=0, column=1, sticky="ew", padx=PAD_X)
        from config.paths_config import get_paths_config

        self.mods_folder_entry.insert(0, get_paths_config().get_mods_path())

        # ✅ Фильтры статусов и типов переводов (по умолчанию все включены)
        self._filter_states = {
            "up_to_date": True,
            "outdated": True,
            "version_mismatch": True,
            "missing": True,
            "missing_parent": True,
            "custom": True,
            "unknown": True,
            "standalone": True,
            "embedded": True,
        }
        self._legend_canvases = {}  # Ссылки на Canvas индикаторы
        self._legend_indicators = {}  # Ссылки на Label индикаторы
        self._legend_visible = True  # Состояние легенды
        self._all_tree_items = []  # Все элементы дерева (для фильтрации)

        # Фрейм с кнопками — горизонтальное расположение
        btn_frame = ttk.Frame(folder_frame)
        btn_frame.grid(row=0, column=2, padx=PAD_BTN_X)

        btn_browse = ttk.Button(
            btn_frame, text=tr("deps_browse", "📂 Обзор..."), command=self.browse_mods_folder
        )
        btn_browse.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_browse, text="Выбрать папку с модами")

        btn_find = ttk.Button(
            btn_frame, text=tr("dependencies_find_mods", "🔍 Найти"), command=self.auto_find_mods
        )
        btn_find.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_find, text="Автоматически найти папку Mods")

        btn_open = ttk.Button(btn_frame, text="📁", command=self.open_mods_folder)
        btn_open.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_open, text="Открыть папку Mods в проводнике")

        # Кнопка анализа зависимостей
        self.analyze_btn = ttk.Button(
            self.parent,
            text=tr("deps_analyze", "🚀 Анализировать зависимости"),
            command=self.analyze_dependencies,
            bootstyle="info",
        )
        self.analyze_btn.grid(row=1, column=0, columnspan=3, padx=PAD_FRAME_X, pady=PAD_FRAME_Y)

        # ✅ НОВОЕ: Панель поиска и сброса фильтров
        search_frame = ttk.Frame(self.parent)
        search_frame.grid(
            row=2, column=0, columnspan=3, sticky="ew", padx=PAD_FRAME_X, pady=PAD_FRAME_Y
        )
        ttk.Label(search_frame, text=tr("deps_search_label", "🔍 Поиск:")).pack(
            side="left", padx=PAD_LABEL_X
        )
        self._search_entry = ttk.Entry(
            search_frame, textvariable=self._search_var, bootstyle="info"
        )
        self._search_entry.pack(side="left", fill="x", expand=True, padx=PAD_ENTRY_X)
        # ✅ Debounce поиска (SEARCH_DEBOUNCE_MS) — без подвисаний на больших деревьях
        self._search_entry.bind("<KeyRelease>", self._on_search_key)
        ToolTip(
            self._search_entry,
            text=tr(
                "deps_search_tooltip",
                "Введите текст для фильтрации дерева (мод, версия, статус)",
            ),
        )
        ttk.Button(
            search_frame,
            text="✕",
            width=3,
            command=self._clear_search,
            bootstyle="secondary",
        ).pack(side="left", padx=(0, PAD_BTN_X))

        btn_reset = ttk.Button(
            search_frame,
            text=tr("deps_reset_filters", "🔄 Сбросить фильтры"),
            command=self._reset_filters,
            bootstyle="warning-outline",
        )
        btn_reset.pack(side="left", padx=PAD_BTN_X)
        ToolTip(
            btn_reset,
            text=tr("deps_reset_filters_tooltip", "Показать все статусы и очистить поиск"),
        )

        ttk.Label(
            search_frame,
            text=tr("deps_sort_hint", "↕ Клик по заголовку — сортировка"),
            font=FONT_SMALL,
            bootstyle="secondary",
        ).pack(side="left", padx=PAD_X)

        # Фрейм для дерева
        tree_frame = ttk.LabelFrame(
            self.parent, text=tr("deps_tree", "🌳 Дерево зависимостей переводов")
        )
        tree_frame.grid(
            row=3, column=0, columnspan=3, padx=PAD_TREE_X, pady=PAD_TREE_Y, sticky="nsew"
        )

        # ✅ ИСПОЛЬЗУЕМ переиспользуемый компонент ScrollableTree
        from gui.components.scrollable_tree import ScrollableTree

        columns = ("type", "version", "status")
        self.dep_tree_widget = ScrollableTree(
            tree_frame,
            columns=columns,
            headings={
                "#0": tr("deps_mod", "Мод"),
                "type": tr("deps_type", "Тип"),
                "version": tr("deps_version", "Версия"),
                "status": tr("deps_status", "Статус"),
            },
            column_widths={"#0": 200, "type": 100, "version": 80, "status": 120},
            show="tree headings",
            selectmode="browse",
        )
        # ✅ ScrollableTree сам управляет своими дочерними виджетами
        self.dep_tree_widget.pack(fill="both", expand=True, padx=5, pady=5)

        # Псевдоним для обратной совместимости
        self.dep_tree = self.dep_tree_widget.tree

        # ✅ НОВОЕ: Сортировка по столбцам — клик по заголовку (как во вкладке "Моды")
        self._heading_base = {
            "#0": tr("deps_mod", "Мод"),
            "type": tr("deps_type", "Тип"),
            "version": tr("deps_version", "Версия"),
            "status": tr("deps_status", "Статус"),
        }
        self.dep_tree_widget.tree.heading("#0", text=self._heading_base["#0"])
        self.dep_tree_widget.tree.heading(
            "#0", command=lambda: self._sort_by("#0")
        )
        self.dep_tree_widget.tree.heading("type", command=lambda: self._sort_by("type"))
        self.dep_tree_widget.tree.heading("version", command=lambda: self._sort_by("version"))
        self.dep_tree_widget.tree.heading("status", command=lambda: self._sort_by("status"))

        # Применяем цветовую маркировку
        self.update_tree_colors()

        # Статистика
        stats_frame = ttk.LabelFrame(self.parent, text=tr("deps_statistics", "Статистика"))
        stats_frame.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        self.stats_label = ttk.Label(
            stats_frame, text=tr("deps_not_analyzed", "Анализ не проводился")
        )
        self.stats_label.pack(padx=5, pady=5)

        # ✅ ЛЕГЕНДА цветовой маркировки
        legend_frame = ttk.LabelFrame(self.parent, text=tr("deps_legend", "📊 Легенда статусов"))
        legend_frame.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        self._build_legend()

        # Кнопки
        btn_frame = ttk.Frame(self.parent)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=10)

        ttk.Button(
            btn_frame, text=tr("deps_export_report", "Экспорт отчёта"), command=self.export_report
        ).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=tr("deps_refresh", "Обновить"), command=self.refresh).pack(
            side="left", padx=5
        )

        # Настройка растягивания — все колонки и строка с деревом
        self.parent.rowconfigure(3, weight=1)
        self.parent.columnconfigure(0, weight=1)
        self.parent.columnconfigure(1, weight=1)
        self.parent.columnconfigure(2, weight=1)

    def browse_mods_folder(self):
        """Выбор папки с модами через диалог"""
        folder = filedialog.askdirectory(
            title=tr("deps_select_mods_folder", "Выберите папку Mods"),
            initialdir=os.path.expandvars(r"C:\Program Files (x86)\Steam\steamapps\common"),
        )
        if folder:
            # Проверяем что это папка Mods или содержит моды
            folder_name = os.path.basename(folder).lower()

            if folder_name != "mods":
                # Если выбрана не папка Mods, предупреждаем
                response = messagebox.askyesno(
                    tr("deps_confirmation", "Подтверждение"),
                    tr(
                        "deps_confirm_mods",
                        "Вы выбрали папку '{folder}'.\n\n"
                        "Рекомендуется выбирать папку 'Mods' в которой находятся все моды.\n\n"
                        "Продолжить?",
                    ).format(folder=os.path.basename(folder)),
                    icon="warning",
                )
                if not response:
                    return

            self.mods_folder_entry.delete(0, tk.END)
            self.mods_folder_entry.insert(0, folder)
            self.config["mods_folder"] = folder
            # Обновляем PathsConfig
            from config.paths_config import get_paths_config

            get_paths_config().set_mods_path(folder, save=True)
            self.log(f"Выбрана папка: {folder}")

    def open_mods_folder(self):
        """Открыть текущую папку Mods в проводнике"""
        folder = self.mods_folder_entry.get()

        if not folder:
            messagebox.showwarning(
                tr("deps_warning", "Предупреждение"),
                tr("deps_select_folder_first", "Сначала выберите папку Mods"),
            )
            return

        if not os.path.exists(folder):
            messagebox.showerror(
                tr("deps_error", "Ошибка"),
                tr("deps_folder_not_exist", "Папка не существует:\n{folder}").format(folder=folder),
            )
            return

        # Открываем папку в проводнике (кроссплатформенно)
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)

    def auto_find_mods(self):
        """Автоматический поиск папки Mods"""
        self.log("Поиск папки Mods...")

        # Стандартные пути для поиска RimWorld
        search_paths = []

        # Windows
        if sys.platform == "win32":
            # 1. Проверяем реестр Windows (самый надёжный способ)
            try:
                import winreg

                # Steam
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
                    steam_path = winreg.QueryValueEx(key, "SteamPath")[0]
                    winreg.CloseKey(key)
                    mods_path = os.path.join(steam_path, "steamapps", "common", "RimWorld", "Mods")
                    if os.path.exists(mods_path):
                        search_paths.append(mods_path)
                except OSError:
                    pass

                # Ludeon (разработчик RimWorld)
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Ludeon Studios\RimWorld"
                    )
                    rimworld_path = winreg.QueryValueEx(key, "InstallPath")[0]
                    winreg.CloseKey(key)
                    mods_path = os.path.join(rimworld_path, "Mods")
                    if os.path.exists(mods_path):
                        search_paths.append(mods_path)
                except OSError:
                    pass
            except ImportError:
                pass  # winreg недоступен

            # 2. Steam - библиотека (автоматический поиск)
            steam_lib = os.path.expandvars(
                r"C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf"
            )
            if os.path.exists(steam_lib):
                try:
                    with open(steam_lib, encoding="utf-8") as f:
                        content = f.read()
                        # Ищем пути к библиотекам Steam
                        matches = re.findall(r'"path"\s*"([^"]+)"', content)
                        for path in matches:
                            mods_path = os.path.join(
                                path, "steamapps", "common", "RimWorld", "Mods"
                            )
                            if os.path.exists(mods_path):
                                search_paths.append(mods_path)
                except Exception:
                    pass

            # 3. Steam - стандартный путь
            steam_path = os.path.expandvars(
                r"C:\Program Files (x86)\Steam\steamapps\common\RimWorld\Mods"
            )
            if os.path.exists(steam_path):
                search_paths.append(steam_path)

            # 4. GOG
            gog_path = os.path.expandvars(r"C:\Program Files (x86)\GOG Galaxy\Games\RimWorld\Mods")
            if os.path.exists(gog_path):
                search_paths.append(gog_path)

            # 5. Microsoft Store
            ms_path = os.path.expandvars(r"C:\XboxGames\RimWorld\Content\Mods")
            if os.path.exists(ms_path):
                search_paths.append(ms_path)

            # 6. Поиск в Program Files
            pf_paths = [
                os.path.expandvars(r"C:\Program Files\RimWorld\Mods"),
                os.path.expandvars(r"C:\Program Files (x86)\RimWorld\Mods"),
            ]
            search_paths.extend([p for p in pf_paths if os.path.exists(p)])

            # 7. Поиск в Documents
            docs_path = os.path.join(
                os.path.expandvars(r"%USERPROFILE%"), "Documents", "RimWorld", "Mods"
            )
            if os.path.exists(docs_path):
                search_paths.append(docs_path)

            # 8. Поиск на других дисках (D:, E:, F: и т.д.)
            for drive in ["D:", "E:", "F:", "G:", "H:"]:
                drive_paths = [
                    os.path.join(drive, "SteamLibrary", "steamapps", "common", "RimWorld", "Mods"),
                    os.path.join(drive, "Games", "RimWorld", "Mods"),
                    os.path.join(drive, "RimWorld", "Mods"),
                ]
                search_paths.extend([p for p in drive_paths if os.path.exists(p)])

        # Linux
        elif sys.platform == "linux":
            home = os.path.expanduser("~")
            linux_paths = [
                os.path.join(home, ".steam/steam/steamapps/common/RimWorld/Mods"),
                os.path.join(home, ".local/share/Steam/steamapps/common/RimWorld/Mods"),
                os.path.join(
                    home,
                    ".var/app/com.valvesoftware.Steam/.steam/steam/steamapps/common/RimWorld/Mods",
                ),
            ]
            search_paths.extend([p for p in linux_paths if os.path.exists(p)])

        # macOS
        elif sys.platform == "darwin":
            home = os.path.expanduser("~")
            mac_paths = [
                os.path.join(
                    home,
                    "Library/Application Support/Steam/steamapps/common/RimWorld/RimWorldMac.app/Mods",
                ),
                "/Applications/RimWorld.app/Mods",
            ]
            search_paths.extend([p for p in mac_paths if os.path.exists(p)])

        # Проверяем найденные пути
        if search_paths:
            found_path = search_paths[0]
            self.mods_folder_entry.delete(0, tk.END)
            self.mods_folder_entry.insert(0, found_path)
            self.config["mods_folder"] = found_path
            self.log(f"Найдено: {found_path}")
            messagebox.showinfo(
                tr("deps_success", "Успех"),
                tr("deps_mods_found", "Папка Mods найдена:\n{path}").format(path=found_path),
            )
        else:
            # Если не найдено, предлагаем пользователю выбрать
            self.log(tr("deps_not_found_log", "Папка Mods не найдена в стандартных расположениях"))
            messagebox.showwarning(
                tr("deps_not_found", "Не найдено"),
                tr(
                    "deps_not_found_msg",
                    "Папка Mods не найдена в стандартных расположениях.\n\n"
                    "Пожалуйста, выберите папку Mods вручную.\n\n"
                    "Обычно она находится по пути:\n"
                    "• Steam: [диск]:\\SteamLibrary\\steamapps\\common\\RimWorld\\Mods\n"
                    "• GOG: C:\\Program Files (x86)\\GOG Galaxy\\Games\\RimWorld\\Mods\n"
                    "• Microsoft Store: C:\\XboxGames\\RimWorld\\Content\\Mods",
                ),
            )

    def _get_scan_folders(self, selected_folder: str) -> list[str]:
        """
        Определяет список папок для сканирования.

        Если выбрана папка Mods - сканируем все подпапки.
        Если выбрана конкретная папка - ищем родительскую Mods.

        Args:
            selected_folder: Выбранная пользователем папка

        Returns:
            Список папок для сканирования
        """
        scan_folders = []

        # Нормализуем путь
        selected_folder = os.path.normpath(selected_folder)

        # Проверяем является ли выбранная папка папкой Mods
        folder_name = os.path.basename(selected_folder).lower()

        if folder_name == "mods":
            # Сканируем все подпапки в Mods
            if os.path.exists(selected_folder):
                for item in os.listdir(selected_folder):
                    item_path = os.path.join(selected_folder, item)
                    # Обработка символических ссылок
                    try:
                        if os.path.isdir(item_path):
                            # Проверяем, что ссылка ведёт на существующую директорию
                            real_path = os.path.realpath(item_path)
                            if os.path.isdir(real_path):
                                scan_folders.append(item_path)
                            else:
                                self.log(f"Пропущена битая ссылка: {item_path}")
                    except OSError as e:
                        self.log(f"Ошибка доступа к {item_path}: {e}")
        else:
            # Выбрана конкретная папка мода
            # Проверяем есть ли рядом другие моды
            parent_folder = os.path.dirname(selected_folder)
            parent_name = os.path.basename(parent_folder).lower()

            if parent_name == "mods":
                # Сканируем всю папку Mods
                for item in os.listdir(parent_folder):
                    item_path = os.path.join(parent_folder, item)
                    try:
                        if os.path.isdir(item_path):
                            real_path = os.path.realpath(item_path)
                            if os.path.isdir(real_path):
                                scan_folders.append(item_path)
                            else:
                                self.log(f"Пропущена битая ссылка: {item_path}")
                    except OSError as e:
                        self.log(f"Ошибка доступа к {item_path}: {e}")
            # Сканируем только выбранную папку
            elif os.path.exists(selected_folder):
                scan_folders.append(selected_folder)

        return scan_folders

    def analyze_dependencies(self):
        """Анализ зависимостей переводов"""
        mods_folder = self.mods_folder_entry.get()

        if not mods_folder:
            messagebox.showwarning(
                tr("deps_warning", "Предупреждение"),
                tr("deps_select_mods", "Выберите папку с модами"),
            )
            return

        # Получаем список папок для сканирования
        scan_folders = self._get_scan_folders(mods_folder)

        if not scan_folders:
            messagebox.showerror(
                tr("deps_error", "Ошибка"),
                tr("deps_mods_not_exist", "Папки с модами не существуют"),
            )
            return

        self.set_status("Анализ зависимостей...")

        # ✅ НОВОЕ: Создаём debounced обновитель прогресса
        from utils.ui_helpers import create_debounced_progress

        root = self.parent.winfo_toplevel()
        self._progress_updater = create_debounced_progress(
            self, root=root, delay_ms=150, adaptive=True
        )

        if self.start_progress:
            self.start_progress()

        try:
            from verification.translation_status_checker import TranslationStatusChecker

            self.log(f"Начало анализа... Найдено папок: {len(scan_folders)}")

            # Создаём checker и сканируем все папки
            checker = TranslationStatusChecker("", None)

            # Сканируем все папки с обновлением прогресса
            total = len(scan_folders)
            for i, folder in enumerate(scan_folders, 1):
                self.set_status(f"Сканирование: {os.path.basename(folder)} ({i}/{total})")
                # Обновляем прогресс через debouncer
                progress = int((i / total) * 50)  # 0-50% за сканирование
                if self._progress_updater:
                    self._progress_updater.update(
                        progress, f"Сканирование: {os.path.basename(folder)}"
                    )
                elif self.set_progress:
                    self.set_progress(progress)
                checker.load_mods_multi(folder)

            self.log(f"Всего загружено модов: {len(checker._mods_cache)}")
            self.log(f"Найдено {len(checker._translations)} переводов")
            self.log(f"Найдено {len(checker._parents)} основных модов")

            # Выводим список переводов для отладки
            for trans_id in list(checker._translations.keys())[:10]:  # Первые 10
                parent_id = checker._translations[trans_id].get("target_mod_id", "нет")
                self.log(f"  Перевод: {trans_id} → Родитель: {parent_id}")

            if len(checker._translations) > 10:
                self.log(f"  ... и ещё {len(checker._translations) - 10} переводов")

            self.log("Проверка статусов переводов...")
            self.set_status("Проверка статусов...")

            # Проверка статусов (50-100%)
            report = checker.check_all_translations()
            if self._progress_updater:
                self._progress_updater.update(100, "Проверка статусов завершена")
            elif self.set_progress:
                self.set_progress(100)

            # Очищаем дерево
            for item in self.dep_tree.get_children():
                self.dep_tree.delete(item)

            # ✅ ИСПРАВЛЕНО: Очищаем список элементов дерева перед перестроением
            # При повторном анализе старые ID больше не действительны
            self._all_tree_items.clear()
            self._items_meta.clear()
            self._items_parent.clear()

            # Строим дерево зависимостей
            tree_data = checker.get_translation_tree()

            # Добавляем узлы в дерево
            parent_nodes = {}

            # 1. Сначала добавляем все родительские узлы
            for node in tree_data.get("nodes", []):
                node_type = node.get("type", "")
                if node_type == "parent":
                    node_id = node.get("id", "")
                    node_label = node.get("label", "")
                    node_version = node.get("version", "Unknown")
                    node_status = node.get("status", "")

                    # Цветной статус с маркером
                    status_colors = {
                        "missing": ("🔴", tr("deps_missing", "Отсутствует")),
                        "up_to_date": ("🟢", tr("deps_up_to_date", "Актуален")),
                        "outdated": ("🟡", tr("deps_outdated", "Устарел")),
                        "version_mismatch": (
                            "🟠",
                            tr("deps_version_mismatch", "Версия не совпадает"),
                        ),
                        "missing_parent": ("🔴", tr("deps_missing_parent", "Родитель не найден")),
                        "custom": ("🟣", tr("deps_custom", "Пользовательский")),
                        "unknown": ("⚪", tr("deps_unknown", "Неизвестно")),
                    }

                    display_type = tr("deps_parent_mod", "Основной мод")
                    if node_status == "missing":
                        display_type = tr("deps_missing", "❌ Отсутствует")

                    icon, status_text = status_colors.get(node_status, ("⚪", node_status))
                    status_display = f"{icon} {status_text}" if node_status else "-"

                    item_id = self.dep_tree.insert(
                        "",
                        "end",
                        text=node_label,
                        values=(display_type, node_version, status_display),
                        tags=(node_status,) if node_status else (),
                    )
                    # Сохраняем в словарь с ключом в нижнем регистре для регистронезависимого поиска
                    parent_nodes[node_id.lower()] = item_id
                    self._all_tree_items.append(item_id)  # ✅ Сохраняем ID
                    self._register_item(
                        item_id,
                        label=node_label,
                        values=(display_type, node_version, status_display),
                        status=node_status,
                        type_tag="",
                        kind="parent",
                        parent_item="",
                    )

            # 2. Потом добавляем узлы переводов
            for node in tree_data.get("nodes", []):
                node_type = node.get("type", "")
                if node_type != "parent":
                    node_id = node.get("id", "")
                    node_label = node.get("label", "")
                    node_version = node.get("version", "Unknown")
                    node_status = node.get("status", "")
                    parent_id = node.get("parent_id", "")

                    # Определяем тип для отображения
                    trans_type = node.get("translation_type", "standalone")
                    if trans_type == "standalone":
                        display_type = tr("deps_translation_standalone", "Перевод (отдельный)")
                    elif trans_type == "embedded":
                        display_type = tr("deps_translation_embedded", "Перевод (встроенный)")
                    else:
                        display_type = tr("deps_translation", "Перевод")

                    # Определяем статус для отображения
                    if node_status == "missing":
                        status_display = "🔴 " + tr("deps_missing", "Отсутствует")
                    elif node_status:
                        status_map = {
                            "up_to_date": ("🟢", tr("deps_up_to_date", "Актуален")),
                            "outdated": ("🟡", tr("deps_outdated", "Устарел")),
                            "version_mismatch": (
                                "🟠",
                                tr("deps_version_mismatch", "Версия не совпадает"),
                            ),
                            "missing_parent": (
                                "🔴",
                                tr("deps_missing_parent", "Родитель не найден"),
                            ),
                            "custom": ("🟣", tr("deps_custom", "Пользовательский")),
                            "unknown": ("⚪", tr("deps_unknown", "Неизвестно")),
                        }
                        icon, text = status_map.get(
                            node_status, ("⚪", node_status.replace("_", " ").title())
                        )
                        status_display = f"{icon} {text}"
                    else:
                        status_display = "-"

                    # Добавляем как дочерний узел если есть родитель (регистронезависимо)
                    parent_item = parent_nodes.get(parent_id.lower()) if parent_id else None
                    item_tags = tuple(
                        t for t in (node_status, trans_type if trans_type else "") if t
                    )
                    if parent_item:
                        item_id = self.dep_tree.insert(
                            parent_item,
                            "end",
                            text=node_label,
                            values=(display_type, node_version, status_display),
                            tags=item_tags,
                        )
                    else:
                        # Если родитель не найден, добавляем как корневой
                        item_id = self.dep_tree.insert(
                            "",
                            "end",
                            text=node_label,
                            values=(display_type, node_version, status_display),
                            tags=item_tags,
                        )
                    parent_nodes[node_id.lower()] = item_id
                    self._all_tree_items.append(item_id)  # ✅ Сохраняем ID
                    self._register_item(
                        item_id,
                        label=node_label,
                        values=(display_type, node_version, status_display),
                        status=node_status,
                        type_tag=trans_type if trans_type in self._filter_states else "",
                        kind="translation",
                        parent_item=parent_item or "",
                    )

            # ✅ Применяем текущие фильтры и сортировку к новому дереву
            self._apply_filters()

            # Обновляем статистику
            self._update_stats(report)

            self.set_status(tr("deps_analysis_done", "Анализ завершён"))
            if self._progress_updater:
                self._progress_updater.finish(success=True)
                self._progress_updater = None
            if self.stop_progress:
                self.stop_progress()
            self.log(tr("deps_analysis_complete_log", "Анализ зависимостей переводов завершён"))

        except Exception as e:
            self.set_status(tr("deps_error_status", "Ошибка"))
            if self._progress_updater:
                self._progress_updater.finish(success=False)
                self._progress_updater = None
            if self.stop_progress:
                self.stop_progress()
            self.log(
                tr("deps_analysis_error_log", "Ошибка анализа зависимостей: {err}").format(err=e)
            )
            messagebox.showerror(
                tr("deps_error", "Ошибка"),
                tr("deps_analysis_error", "Ошибка анализа зависимостей: {err}").format(err=e),
            )

    def _update_stats(self, report):
        """Обновление статистики на Floodgauge — нативные карточки с прогрессом"""
        # Очищаем старую статистику
        for widget in self.parent.grid_slaves(row=4):
            widget.destroy()

        # Создаём новый фрейм статистики
        stats_frame = ttk.LabelFrame(
            self.parent, text=tr("deps_statistics", "📊 Статистика (клик = фильтр)")
        )
        stats_frame.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        # Контейнер для карточек в 2 колонки
        cards_container = ttk.Frame(stats_frame)
        cards_container.pack(fill="x", padx=5, pady=5)

        total = report.total_translations or 1

        self.stats_items = [
            ("📊 Всего", report.total_translations, "primary", None),
            ("🟢 Актуальных", report.up_to_date, "success", "up_to_date"),
            ("🟡 Устаревших", report.outdated, "warning", "outdated"),
            ("🟠 Версия ≠", report.version_mismatch, "warning", "version_mismatch"),
            ("🔴 Нет родителя", report.missing_parent, "danger", "missing_parent"),
            ("🟣 Пользовательских", report.custom_translations, "secondary", "custom"),
            ("🔵 Отдельных модов", report.standalone_translations, "info", "standalone"),
            ("🟢 Встроенных", report.embedded_translations, "success", "embedded"),
        ]

        # Создаём Floodgauge карточки
        self.stats_gauges = {}
        self._gauge_base_colors = {}
        row = 0
        col = 0
        for label, value, color, filter_tag in self.stats_items:
            pct = int(value / total * 100) if total > 0 else 0

            # Фрейм карточки
            card = ttk.Frame(cards_container)
            card.grid(row=row, column=col, padx=4, pady=3, sticky="ew")
            cards_container.columnconfigure(col, weight=1)

            # Метка с названием
            ttk.Label(card, text=f"{label}: {value} ({pct}%)", font=FONT_SMALL).pack(
                fill="x", padx=2, pady=(2, 0)
            )

            # Floodgauge — прогресс-бар с текстом
            gauge = ttk.Progressbar(
                card,
                orient="horizontal",
                length=150,
                mode="determinate",
                bootstyle=color,
            )
            gauge["value"] = pct
            gauge.pack(fill="x", padx=2, pady=(0, 2))

            # Клик для фильтрации
            if filter_tag:
                gauge.bind("<Button-1>", lambda e, t=filter_tag: self._on_stats_click(t))
                gauge.configure(cursor="hand2")
                ToolTip(
                    gauge, text=tr("deps_filter_card_tooltip", "Клик — включить/выключить фильтр")
                )
                self.stats_gauges[filter_tag] = gauge
                self._gauge_base_colors[filter_tag] = color

            col += 1
            if col >= 2:
                col = 0
                row += 1

        # ✅ НОВОЕ: Счётчик показанных элементов после фильтрации
        self._shown_label = ttk.Label(
            stats_frame, text=tr("deps_shown_stats", "Показано") + ": 0 / 0", bootstyle="secondary"
        )
        self._shown_label.pack(anchor="w", padx=5, pady=(0, 3))
        self._update_shown_stats()

    def _on_stats_click(self, tag):
        """Обработка клика по статистике — фильтрация дерева"""
        self._filter_states[tag] = not self._filter_states[tag]
        is_active = self._filter_states[tag]
        self.log(f"Фильтр '{tag}': {'ВКЛ' if is_active else 'ВЫКЛ'}")
        self._apply_filters()

        # Обновляем цвет прогресс-бара
        if tag in self.stats_gauges:
            gauge = self.stats_gauges[tag]
            if is_active:
                # Активный фильтр — исходный яркий цвет
                gauge.configure(bootstyle=self._gauge_base_colors.get(tag, "primary"))
            else:
                # Неактивный — приглушённый
                gauge.configure(bootstyle="secondary")

    def _restore_gauge_colors(self):
        """Восстановить исходные цвета всех карточек статистики"""
        for tag, gauge in getattr(self, "stats_gauges", {}).items():
            try:
                gauge.configure(bootstyle=self._gauge_base_colors.get(tag, "primary"))
            except Exception:
                continue

    def export_report(self):
        """Экспорт отчёта о зависимостях через ReportExporter"""
        from gui.components.report_exporter import ReportExporter

        mods_folder = self.mods_folder_entry.get()

        if not mods_folder:
            messagebox.showwarning(
                tr("deps_warning", "Предупреждение"),
                tr("deps_select_and_analyze", "Выберите папку с модами и проведите анализ"),
            )
            return

        save_path = filedialog.asksaveasfilename(
            title=tr("deps_save_report", "Сохранить отчёт"),
            defaultextension=".txt",
            filetypes=[
                ("Текстовый файл", "*.txt"),
                ("JSON", "*.json"),
                ("HTML", "*.html"),
            ],
        )

        if not save_path:
            return

        try:
            from verification.translation_status_checker import TranslationStatusChecker

            checker = TranslationStatusChecker(mods_folder, None)
            checker.load_mods()
            report = checker.check_all_translations()

            # Подготовка данных для экспорта
            data = [
                {
                    "translation_mod": dep.translation_mod_name,
                    "parent_mod": dep.parent_mod_name,
                    "status": dep.status.value,
                    "type": dep.translation_type.value,
                }
                for dep in report.dependencies
            ]

            exporter = ReportExporter(
                data=data,
                title="Отчёт о зависимостях переводов RimWorld",
                columns=("Перевод", "Родитель", "Статус", "Тип"),
            )

            if save_path.endswith(".json"):
                exporter.export_json(save_path)
            elif save_path.endswith(".html"):
                exporter.export_html(save_path)
            else:
                exporter.export_txt(save_path)

            self.log(tr("deps_report_saved_log", "Отчёт сохранён: {path}").format(path=save_path))
            messagebox.showinfo(
                tr("deps_success", "Успех"),
                tr("deps_report_saved", "Отчёт сохранён: {path}").format(path=save_path),
            )

        except Exception as e:
            self.log(tr("deps_export_error_log", "Ошибка экспорта отчёта: {err}").format(err=e))
            messagebox.showerror(
                tr("deps_error", "Ошибка"),
                tr("deps_export_error", "Ошибка экспорта: {err}").format(err=e),
            )

    def _format_text_report(self, mods_folder, report):
        """Форматирование текстового отчёта"""
        lines = []
        lines.append("=" * 80)
        lines.append(tr("deps_report_title", "ОТЧЁТ О ЗАВИСИМОСТЯХ ПЕРЕВОДОВ RIMWORLD МОДОВ"))
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"{tr('deps_report_mods_folder', 'Папка модов')}: {mods_folder}")
        lines.append("")
        lines.append("-" * 40)
        lines.append(tr("deps_report_statistics", "СТАТИСТИКА"))
        lines.append("-" * 40)
        lines.append(f"{tr('deps_stat_total', 'Всего переводов')}: {report.total_translations}")
        lines.append(f"{tr('deps_stat_uptodate', 'Актуальных')}: {report.up_to_date}")
        lines.append(f"{tr('deps_stat_outdated', 'Устаревших')}: {report.outdated}")
        lines.append(
            f"{tr('deps_stat_version_mismatch', 'Несовпадение версий')}: {report.version_mismatch}"
        )
        lines.append(
            f"{tr('deps_stat_missing_parent', 'Родитель не найден')}: {report.missing_parent}"
        )
        lines.append(f"{tr('deps_stat_custom', 'Пользовательских')}: {report.custom_translations}")
        lines.append(
            f"{tr('deps_stat_standalone', 'Отдельных модов-переводов')}: {report.standalone_translations}"
        )
        lines.append(
            f"{tr('deps_stat_embedded', 'Встроенных переводов')}: {report.embedded_translations}"
        )
        lines.append("")
        lines.append("-" * 40)
        lines.append(tr("deps_report_deaggregation", "ДЕЗАГРЕГАЦИЯ ПО ПЕРЕВОДАМ"))
        lines.append("-" * 40)

        for dep in report.dependencies:
            lines.append("")
            lines.append(
                f"{tr('deps_report_translation', 'Перевод')}: {dep.translation_mod_name} ({dep.translation_mod_id})"
            )
            lines.append(f"  {tr('deps_report_version', 'Версия')}: {dep.translation_version}")
            lines.append(f"  {tr('deps_report_type', 'Тип')}: {dep.translation_type.value}")
            lines.append(f"  {tr('deps_report_status', 'Статус')}: {dep.status.value}")
            lines.append(
                f"  {tr('deps_report_parent_mod', 'Родительский мод')}: {dep.parent_mod_name} ({dep.parent_mod_id})"
            )
            lines.append(
                f"  {tr('deps_report_parent_version', 'Версия родителя')}: {dep.parent_version}"
            )
            lines.append(
                f"  {tr('deps_report_compatibility', 'Совместимость')}: {tr('deps_report_yes', 'Да') if dep.is_compatible else tr('deps_report_no', 'Нет')}"
            )
            if dep.issues:
                lines.append(f"  {tr('deps_report_issues', 'Проблемы')}: {', '.join(dep.issues)}")

        lines.append("")
        lines.append("=" * 80)
        lines.append(tr("deps_report_end", "КОНЕЦ ОТЧЁТА"))
        lines.append("=" * 80)

        return "\n".join(lines)

    def _build_legend(self):
        """Построить компактную легенду только с цветными индикаторами"""
        # ✅ Полностью очищаем строку легенды от всех виджетов
        for widget in self.parent.grid_slaves(row=5):
            widget.destroy()

        # ✅ Очищаем старые ссылки
        self._legend_canvases = {}
        self._legend_indicators = {}

        # ✅ Флаг что легенда построена
        self._legend_built = True

        # Определяем текущую тему для цветов
        style = ttk.Style()
        current_theme = style.theme_use()
        is_dark = current_theme.endswith("-dark") or current_theme in ("darkly", "cyborg", "superhero", "solar", "vapor")

        # Яркие цвета для индикаторов
        light_colors = {
            "up_to_date": "#22c55e",
            "outdated": "#f59e0b",
            "version_mismatch": "#f97316",
            "missing": "#ef4444",
            "missing_parent": "#dc2626",
            "custom": "#8b5cf6",
            "unknown": "#9ca3af",
        }

        dark_colors = {
            "up_to_date": "#4ade80",
            "outdated": "#fbbf24",
            "version_mismatch": "#fb923c",
            "missing": "#f87171",
            "missing_parent": "#f87171",
            "custom": "#a78bfa",
            "unknown": "#d1d5db",
        }

        colors = dark_colors if is_dark else light_colors
        text_color = "#e5e7eb" if is_dark else "#374151"

        # Фрейм легенды — только цветные индикаторы
        legend_frame = ttk.LabelFrame(self.parent, text=tr("deps_legend", "📊 Легенда"))
        legend_frame.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        # Контейнер для индикаторов
        indicators_frame = ttk.Frame(legend_frame)
        indicators_frame.pack(fill="x", padx=5, pady=5)

        # Статусы
        statuses = [
            ("up_to_date", "Актуален"),
            ("outdated", "Устарел"),
            ("version_mismatch", "Версия ≠"),
            ("missing", "Отсутствует"),
            ("missing_parent", "Нет родителя"),
            ("custom", "Пользовательский"),
            ("unknown", "Неизвестно"),
        ]

        for tag, label in statuses:
            item_frame = ttk.Frame(indicators_frame)
            item_frame.pack(side="left", padx=6, pady=2)

            # Цветной квадрат через Canvas — фиксированный размер 12x12
            box_frame = ttk.Frame(item_frame, width=12, height=12)
            box_frame.pack_propagate(False)  # ✅ Запрещаем растягивание
            box_frame.pack(side="left", padx=(0, 4))

            color_box = tk.Canvas(
                box_frame,
                width=12,
                height=12,
                highlightthickness=0,
                bd=0,
            )
            color_box.place(x=0, y=0, width=12, height=12)
            color_box.create_rectangle(0, 0, 12, 12, fill=colors[tag], outline="")
            self._legend_indicators[tag] = color_box

            # Текст
            ttk.Label(
                item_frame,
                text=label,
                font=("Segoe UI", 8),
                foreground=text_color,
            ).pack(side="left")

    # =========================================================================
    # ФИЛЬТРАЦИЯ И СОРТИРОВКА ДЕРЕВА ЗАВИСИМОСТЕЙ
    # =========================================================================

    def _register_item(self, item_id, label, values, status, type_tag, kind, parent_item):
        """
        Регистрирует мета-данные элемента дерева.

        Используется фильтрацией (поиск/статусы/типы) и сортировкой —
        источник истины вместо парсинга tags/values дерева.

        Args:
            item_id: ID элемента Treeview
            label: Название мода (колонка #0)
            values: Кортеж значений колонок (тип, версия, статус)
            status: Статус (тег фильтра)
            type_tag: Тип перевода ("standalone"/"embedded"/"")
            kind: "parent" или "translation"
            parent_item: ID родительского элемента ("" — корень)
        """
        self._items_meta[item_id] = {
            "label": label or "",
            "values": values or (),
            "status": status or "",
            "type_tag": type_tag or "",
            "kind": kind,
        }
        self._items_parent[item_id] = parent_item or ""

    def _on_search_key(self, event=None):
        """Debounced обработчик ввода в поле поиска (SEARCH_DEBOUNCE_MS)"""
        if self._filter_debounce_timer:
            try:
                self.parent.after_cancel(self._filter_debounce_timer)
            except Exception:
                pass
        self._filter_debounce_timer = self.parent.after(
            SEARCH_DEBOUNCE_MS, self._apply_filters
        )

    def _clear_search(self):
        """Очистить поиск и показать все элементы"""
        self._search_var.set("")
        self._apply_filters()

    def _reset_filters(self):
        """Сбросить все фильтры: включить все статусы, очистить поиск"""
        for key in self._filter_states:
            self._filter_states[key] = True
        self._search_var.set("")
        self._restore_gauge_colors()
        self.log("Фильтры сброшены — показаны все элементы")
        self._apply_filters()

    def _is_item_visible(self, item_id):
        """
        Проверяет видимость элемента с учётом поиска, статуса и типа перевода.

        Returns:
            True если элемент проходит все активные фильтры
        """
        meta = self._items_meta.get(item_id)
        if meta is None:
            return True

        # 1. Поиск по названию и всем колонкам
        search_text = self._search_var.get().strip().lower()
        if search_text:
            haystack = " ".join(
                [str(meta.get("label", "")), *(str(v) for v in meta.get("values", ()))]
            ).lower()
            if search_text not in haystack:
                return False

        # 2. Фильтр по статусу
        status = meta.get("status", "")
        if not self._filter_states.get(status, True):
            return False

        # 3. Фильтр по типу перевода (standalone/embedded)
        type_tag = meta.get("type_tag", "")
        if type_tag and not self._filter_states.get(type_tag, True):
            return False

        return True

    def _apply_filters(self, event=None):
        """
        Применить фильтры (поиск + статусы + типы) и сортировку к дереву.

        Дерево перестраивается: скрытые элементы откреплены (detach),
        видимые пересобраны с учётом иерархии и текущей сортировки.
        """
        self._filter_debounce_timer = None
        try:
            if not getattr(self, "dep_tree", None):
                return
            if not self._all_tree_items:
                return

            # Отсоединяем все элементы — дерево перестроится с учётом сортировки
            for item in self._all_tree_items:
                try:
                    self.dep_tree.detach(item)
                except tk.TclError:
                    # Элемент больше не существует — пропускаем
                    continue

            # Оставляем только видимые
            visible = [iid for iid in self._all_tree_items if self._is_item_visible(iid)]
            visible_set = set(visible)

            # Восстанавливаем иерархию среди видимых:
            # если родитель скрыт — элемент становится корневым
            children_map = {}
            roots = []
            for iid in visible:
                parent = self._items_parent.get(iid, "")
                if parent and parent in visible_set:
                    children_map.setdefault(parent, []).append(iid)
                else:
                    roots.append(iid)

            self._reattach_sorted(roots, children_map, "")
            self._update_shown_stats(len(visible))
        except Exception:
            # Тихо игнорируем ошибки фильтрации — не ломаем UI
            pass

    def _reattach_sorted(self, items, children_map, parent_item):
        """Рекурсивно прикрепляет отсортированные элементы в дерево"""
        for iid in self._sort_items(items):
            try:
                self.dep_tree.move(iid, parent_item, "end")
            except tk.TclError:
                continue
            self._reattach_sorted(children_map.get(iid, []), children_map, iid)

    def _sort_items(self, items):
        """Сортирует список ID элементов по текущему столбцу"""
        if not self._sort_column or len(items) < 2:
            return items
        try:
            return sorted(
                items,
                key=lambda iid: self._sort_key(iid, self._sort_column),
                reverse=self._sort_reverse,
            )
        except Exception:
            return items

    def _sort_key(self, item_id, column):
        """Ключ сортировки элемента для указанного столбца"""
        meta = self._items_meta.get(item_id, {})
        values = list(meta.get("values", ()))
        label = str(meta.get("label", "")).casefold()

        if column == "type":
            return (str(values[0] if len(values) > 0 else "").casefold(),)
        if column == "version":
            return (self._version_key(str(values[1] if len(values) > 1 else "")),)
        if column == "status":
            rank = self._STATUS_RANK.get(meta.get("status", ""), 99)
            return (rank, label)
        # По умолчанию — сортировка по названию мода
        return (label,)

    @staticmethod
    def _version_key(value):
        """Натуральный ключ сортировки версии (1.10 > 1.9, символьные части — текстом)"""
        parts = re.findall(r"\d+|\D+", value or "")
        return tuple((1, int(part)) if part.isdigit() else (0, part.casefold()) for part in parts)

    def _sort_by(self, column):
        """Сортировка по столбцу — клик по заголовку (как во вкладке "Моды")"""
        if self._sort_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            self._sort_reverse = False
        self._update_heading_arrows()
        self._apply_filters()

    def _update_heading_arrows(self):
        """Обновляет стрелки ▲/▼ в заголовках столбцов"""
        if not self._heading_base or not getattr(self, "dep_tree_widget", None):
            return
        for column, base_text in self._heading_base.items():
            if column == self._sort_column:
                arrow = " ▼" if self._sort_reverse else " ▲"
                text = base_text + arrow
            else:
                text = base_text
            try:
                self.dep_tree_widget.tree.heading(column, text=text)
            except tk.TclError:
                continue

    def _update_shown_stats(self, visible_count=None):
        """Обновляет счётчик показанных элементов в блоке статистики"""
        if not self._shown_label:
            return
        try:
            if visible_count is None:
                # Считаем по мета-данным: get_children() вернул бы только корневые
                visible_count = sum(
                    1 for iid in self._all_tree_items if self._is_item_visible(iid)
                )
            total = len(self._all_tree_items)
            self._shown_label.config(
                text=f"{tr('deps_shown_stats', 'Показано')}: {visible_count} / {total}"
            )
        except Exception:
            pass

    def refresh(self):
        """Обновление данных"""
        self.analyze_dependencies()

    def update_tree_colors(self):
        """Обновить цветовую маркировку статусов в дереве зависимостей"""
        style = ttk.Style()
        current_theme = style.theme_use()
        is_dark = current_theme.endswith("-dark") or current_theme in ("darkly", "cyborg", "superhero", "solar", "vapor")

        # ✅ КЛЮЧЕВОЕ: Разрешаем отрисовку фона строк на Windows
        style.configure("Treeview", fieldbackground="")

        # ✅ Переопределяем цвета выделения чтобы не перекрывать теги
        if is_dark:
            style.map(
                "Treeview", background=[("selected", "#3b82f6")], foreground=[("selected", "white")]
            )
            # Тёмная тема — светлый текст на тёмном фоне
            self.dep_tree.tag_configure("missing", background="#7f1d1d", foreground="#fca5a5")
            self.dep_tree.tag_configure("up_to_date", background="#14532d", foreground="#86efac")
            self.dep_tree.tag_configure("outdated", background="#78350f", foreground="#fcd34d")
            self.dep_tree.tag_configure(
                "version_mismatch", background="#7c2d12", foreground="#fdba74"
            )
            self.dep_tree.tag_configure(
                "missing_parent", background="#7f1d1d", foreground="#fca5a5"
            )
            self.dep_tree.tag_configure("custom", background="#4c1d95", foreground="#c4b5fd")
            self.dep_tree.tag_configure("unknown", background="#374151", foreground="#9ca3af")
        else:
            style.map(
                "Treeview", background=[("selected", "#3b82f6")], foreground=[("selected", "white")]
            )
            # Светлая тема — тёмный текст на светлом фоне
            self.dep_tree.tag_configure("missing", background="#fee2e2", foreground="#dc2626")
            self.dep_tree.tag_configure("up_to_date", background="#dcfce7", foreground="#16a34a")
            self.dep_tree.tag_configure("outdated", background="#fef3c7", foreground="#d97706")
            self.dep_tree.tag_configure(
                "version_mismatch", background="#ffedd5", foreground="#ea580c"
            )
            self.dep_tree.tag_configure(
                "missing_parent", background="#fee2e2", foreground="#dc2626"
            )
            self.dep_tree.tag_configure("custom", background="#ede9fe", foreground="#7c3aed")
            self.dep_tree.tag_configure("unknown", background="#f3f4f6", foreground="#6b7280")

        # ✅ Обновляем цвета индикаторов легенды при смене темы (без пересоздания)
        if self._legend_indicators:
            self._update_legend_colors()

    def _update_legend_colors(self):
        """Обновить цвета кнопок фильтров без пересоздания виджетов"""
        style = ttk.Style()
        current_theme = style.theme_use()
        is_dark = current_theme.endswith("-dark") or current_theme in ("darkly", "cyborg", "superhero", "solar", "vapor")

        light_colors = {
            "up_to_date": "#22c55e",
            "outdated": "#f59e0b",
            "version_mismatch": "#f97316",
            "missing": "#ef4444",
            "missing_parent": "#dc2626",
            "custom": "#8b5cf6",
            "unknown": "#9ca3af",
        }

        dark_colors = {
            "up_to_date": "#4ade80",
            "outdated": "#fbbf24",
            "version_mismatch": "#fb923c",
            "missing": "#f87171",
            "missing_parent": "#f87171",
            "custom": "#a78bfa",
            "unknown": "#d1d5db",
        }

        colors = dark_colors if is_dark else light_colors

        # Обновляем цвета Canvas-индикаторов
        for tag, canvas in self._legend_indicators.items():
            items = canvas.find_all()
            if items:
                canvas.itemconfig(items[0], fill=colors[tag])


def create_dependencies_tab(
    parent,
    config,
    log_callback,
    set_status_callback,
    start_progress_callback=None,
    stop_progress_callback=None,
    set_progress_callback=None,
):
    """
    Фабричная функция для создания вкладки зависимостей.

    Args:
        parent: Родительский виджет
        config: Словарь конфигурации
        log_callback: Функция для логирования
        set_status_callback: Функция для установки статуса
        start_progress_callback: Функция для запуска прогресс бара
        stop_progress_callback: Функция для остановки прогресс бара
        set_progress_callback: Функция для установки значения прогресс бара

    Returns:
        Экземпляр DependenciesTab
    """
    return DependenciesTab(
        parent,
        config,
        log_callback,
        set_status_callback,
        start_progress_callback,
        stop_progress_callback,
        set_progress_callback,
    )
