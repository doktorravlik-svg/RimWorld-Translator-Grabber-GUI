# gui/core/ui_builder.py
"""
Построение пользовательского интерфейса для RimWorld Translator Grabber.
"""


class UIBuilder:
    """
    Построитель основного интерфейса.

    Отвечает за:
    - Создание PanedWindow
    - Создание Notebook и вкладок
    - Создание лог-панели
    - Создание статус-бара
    - Регистрацию вкладок в TabManager

    Args:
        root: Tk root
        config: Словарь конфигурации
        tab_manager: TabManager для управления вкладками
        callbacks: Словарь callback-функций
            Ожидает:
            - save_config
            - start_translation
            - start_verification
            - start_full_verification
            - start_duplicate_merge
            - run_integrity_check(language_filter)
            - apply_fonts
            - apply_colors
            - on_save_settings
            - on_load_settings
            - on_save_filters_config
            - log (функция логирования)
    """

    def __init__(
        self, root, config: dict, tab_manager, callbacks: dict, main_paned=None, notebook=None
    ):
        self.root = root
        self.config = config
        self.tab_manager = tab_manager
        self.callbacks = callbacks
        self._existing_main_paned = main_paned
        self._existing_notebook = notebook

    def build(self) -> dict:
        """
        Построить интерфейс.

        Returns:
            Словарь с созданными виджетами:
            - main_paned, notebook, log_panel, status_bar,
              tab_translation, tab_verification, tab_duplicates,
              tab_settings, tab_mods_manager, tab_filters,
              tab_dependencies, tab_editor, tab_log
        """
        import ttkbootstrap as ttk
        from gui.components.gui_components import LogPanel
        from gui.components.statusbar import StatusBar
        from gui.gui_i18n import i18n

        # Применяем тему
        theme = self.config.get("theme", "light")
        bs_theme = {
            "light": "cosmo",
            "dark": "darkly",
            "ocean": "minty",
            "forest": "united",
        }.get(theme, "cosmo")

        style = ttk.Style()
        style.theme_use(bs_theme)

        # Используем существующие или создаём новые
        if self._existing_main_paned:
            main_paned = self._existing_main_paned
        else:
            main_paned = ttk.Panedwindow(self.root, orient="vertical")

        if self._existing_notebook:
            notebook = self._existing_notebook
        else:
            notebook = ttk.Notebook(main_paned)
            main_paned.add(notebook, weight=3)

        # Вкладки
        widgets = {}
        widgets.update(self._create_tabs(notebook))

        # Вкладка "Лог"
        tab_log = ttk.Frame(notebook)
        self.tab_manager.register_and_add("📋 Лог", tab_log)

        log_panel = LogPanel(tab_log, title=i18n.tr("log_panel_title", "Журнал событий"), height=20)
        log_panel.pack(fill="both", expand=True, padx=5, pady=5)
        widgets["log_panel"] = log_panel

        # ✅ ИСПРАВЛЕНО: StatusBar прикреплён к низу окна (вне PanedWindow)
        # Упаковываем в правильном порядке: сначала StatusBar, потом PanedWindow

        # Создаём фрейм для статус-бара с компактной высотой
        status_frame = ttk.Frame(self.root)
        status_frame.pack_propagate(False)
        status_frame.configure(height=50)

        status_bar = StatusBar(status_frame)
        status_bar.pack(fill="both", expand=True, padx=2, pady=1)

        # Pack'уем StatusBar ПЕРВЫМ (side="bottom") - он зарезервирует место внизу
        status_frame.pack(side="bottom", fill="x", padx=5, pady=1)

        # Pack'уем PanedWindow ВТОРЫМ (fill="both", expand=True) - займёт всё оставшееся место
        main_paned.pack(fill="both", expand=True, padx=5, pady=5)

        widgets["status_bar"] = status_bar

        # Методы для обратной совместимости
        widgets["progress_bar"] = status_bar.progress_bar
        widgets["status_label"] = status_bar.status_label
        widgets["log_text"] = log_panel.log_text

        widgets["notebook"] = notebook
        widgets["main_paned"] = main_paned
        widgets["style"] = style

        # Setup tab icons
        self._setup_tab_icons(notebook)

        # ✅ НОВОЕ: Тултипы для элементов статус-бара
        self._setup_tooltips(status_bar, widgets)

        return widgets

    def _setup_tooltips(self, status_bar, widgets):
        """Установить тултипы для основных элементов интерфейса"""
        # Тултипы статус-бара
        status_bar.set_tooltip(status_bar.progress_bar, "Прогресс выполнения операции")

    def _create_tabs(self, notebook) -> dict:
        """Создать все вкладки с поддержкой i18n"""
        import ttkbootstrap as ttk
        from gui.gui_i18n import i18n

        widgets = {}

        # Импорт вкладок
        from config.paths_config import get_paths_config
        from gui.tabs.editor.editor_file_browser import TranslationEditorTab  # ✅ НОВОЕ: из editor/
        from gui.tabs.gui_dependencies import create_dependencies_tab
        from gui.tabs.gui_filters_tab import FiltersTab
        from gui.tabs.gui_mods_tab import ModsManagerTab
        from gui.tabs.gui_tab_duplicates import DuplicatesTab
        from gui.tabs.gui_tab_settings import SettingsTab
        from gui.tabs.gui_tab_translation import TranslationTab
        from gui.tabs.gui_tab_verification import VerificationTab

        # Перевод
        tab_translation = TranslationTab(
            notebook,
            self.config,
            on_change=self.callbacks.get("save_config"),
            on_translate=self.callbacks.get("start_translation"),
            on_cancel=self.callbacks.get("cancel_translation"),
        )
        self.tab_manager.register_and_add(i18n.tr("tab_translation", "🌐 Перевод"), tab_translation)
        widgets["tab_translation"] = tab_translation

        # Верификация
        tab_verification = VerificationTab(
            notebook,
            on_verify_callback=self.callbacks.get("start_verification"),
            on_full_verify_callback=self.callbacks.get("start_full_verification"),
        )
        self.tab_manager.register_and_add(
            i18n.tr("tab_verification", "✅ Верификация"), tab_verification
        )
        widgets["tab_verification"] = tab_verification

        # Дубликаты
        tab_duplicates = DuplicatesTab(
            notebook,
            self.config,
            on_merge_callback=self.callbacks.get("start_duplicate_merge"),
        )
        self.tab_manager.register_and_add(i18n.tr("tab_duplicates", "🔄 Дубликаты"), tab_duplicates)
        widgets["tab_duplicates"] = tab_duplicates

        # Настройки
        tab_settings = SettingsTab(
            notebook,
            self.config,
            on_save_callback=self.callbacks.get("on_save_settings"),
            on_load_callback=self.callbacks.get("on_load_settings"),
            on_integrity_check_callback=self.callbacks.get("run_integrity_check"),
            on_font_change_callback=self.callbacks.get("apply_fonts"),
            on_color_change_callback=self.callbacks.get("apply_colors"),
        )
        self.tab_manager.register_and_add(i18n.tr("tab_settings", "⚙️ Настройки"), tab_settings)
        widgets["tab_settings"] = tab_settings

        # Моды
        tab_mods_manager = ModsManagerTab(
            notebook,
            mods_folder=get_paths_config().get_mods_path(),
            on_change=self.callbacks.get("save_config"),
            log_callback=self.callbacks.get("log"),  # ✅ НОВОЕ: логирование в панель
        )
        self.tab_manager.register_and_add(i18n.tr("tab_mods", "📦 Моды"), tab_mods_manager)
        widgets["tab_mods_manager"] = tab_mods_manager

        # Фильтры
        tab_filters = FiltersTab(
            notebook,
            on_save_callback=self.callbacks.get("on_save_filters_config"),
        )
        self.tab_manager.register_and_add(i18n.tr("tab_filters", "📝 Фильтры"), tab_filters)
        widgets["tab_filters"] = tab_filters

        # Зависимости
        tab_dependencies = ttk.Frame(notebook)
        self.tab_manager.register_and_add(
            i18n.tr("tab_dependencies", "🔗 Зависимости"), tab_dependencies
        )
        widgets["tab_dependencies"] = tab_dependencies

        # Зависимости — содержимое
        widgets["dependencies_tab"] = create_dependencies_tab(
            tab_dependencies,
            self.config,
            self.callbacks.get("log"),
            self.callbacks.get("set_status"),
            self.callbacks.get("start_progress"),
            self.callbacks.get("stop_progress"),
            self.callbacks.get("set_progress"),
        )

        # Редактор файлов (просмотр и выбор файлов)
        tab_editor = TranslationEditorTab(
            notebook,
            mods_folder=get_paths_config().get_mods_path(),
            log_callback=self.callbacks.get("log"),  # ✅ НОВОЕ: логирование в панель
        )
        self.tab_manager.register_and_add(i18n.tr("tab_editor", "✏️ Редактор"), tab_editor)
        widgets["tab_editor"] = tab_editor

        # Вкладка "Лог" — добавляется отдельно в build()

        return widgets

    def _setup_tab_icons(self, notebook):
        """Set icons for all tabs"""
        from gui.styling.icon_manager import get_tab_icons

        tab_icons = get_tab_icons(size=18)
        if not tab_icons:
            return

        # Map tab names to their index in the notebook
        tab_name_map = [
            "translation",
            "verification",
            "duplicates",
            "settings",
            "mods",
            "filters",
            "dependencies",
            "editor",
            "log",
        ]

        for i, tab_name in enumerate(tab_name_map):
            icon = tab_icons.get(tab_name)
            if icon and hasattr(icon, "image"):
                try:
                    # Get current text
                    current_text = notebook.tab(i, "text")
                    notebook.tab(i, image=icon.image, text=current_text, compound="left")
                except Exception:
                    pass
