# gui/styling/icon_manager.py
"""
Менеджер иконок ttkbootstrap-icons для RimWorld Translator Grabber.
Централизованное управление иконками с адаптивными цветами для разных тем.

Поддерживает:
- Адаптивные цвета для светлых/темных тем
- Семантические цвета (success, warning, error, info)
- Разные размеры для разных контекстов
- Кэширование с учетом темы
- Отложенное создание иконок (требуется tkinter root)
"""

# Импорты иконок
HAS_ICONS = False
BootstrapIcon = None

try:
    from ttkbootstrap_icons_bs import BootstrapIcon

    HAS_ICONS = True
except ImportError:
    try:
        from ttkbootstrap_icons import BootstrapIcon

        HAS_ICONS = True
    except ImportError:
        pass


# ===== ЦВЕТОВЫЕ СХЕМЫ ДЛЯ ТЕМ =====

# Цвета иконок для СВЕТЛЫХ тем (cosmo, minty, united, solar)
LIGHT_THEME_COLORS = {
    "success": "#28a745",
    "warning": "#fd7e14",
    "error": "#dc3545",
    "info": "#0071bc",
    "primary": "#0d6efd",
    "menu_icon": "#495057",
    "tab_icon": "#6c757d",
    "toolbar_icon": "#343a40",
    "status_icon": "#6c757d",
    "accent": "#e94560",
}

# Цвета иконок для ТЕМНЫХ тем (darkly, cyborg, superhero, vapor)
DARK_THEME_COLORS = {
    "success": "#4caf50",
    "warning": "#ffc107",
    "error": "#f44336",
    "info": "#29b6f6",
    "primary": "#64b5f6",
    "menu_icon": "#ced4da",
    "tab_icon": "#adb5bd",
    "toolbar_icon": "#e9ecef",
    "status_icon": "#adb5bd",
    "accent": "#ff6b6b",
}

# Маппинг тем на цветовые схемы
THEME_COLOR_MAP = {
    "light": "light",
    "ocean": "light",
    "forest": "light",
    "solar": "light",
    "dark": "dark",
    "cyborg": "dark",
    "superhero": "dark",
    "vapor": "dark",
}

# Размеры иконок
ICON_SIZES = {
    "menu": 16,
    "tab": 18,
    "toolbar": 22,
    "toolbar_large": 26,
    "status": 14,
    "button": 20,
    "dialog": 24,
}


class IconManager:
    """
    Централизованный менеджер иконок с адаптивными цветами.
    Отложенное создание иконок (требуется tkinter root).
    """

    def __init__(self):
        self._cache = {}
        self._current_theme = "light"
        self._pending_icons = {}  # Определения иконок для отложенного создания

    def set_theme(self, theme_name: str):
        """Установить текущую тему и очистить кэш"""
        self._current_theme = theme_name
        self.clear_cache()

    @property
    def colors(self) -> dict:
        """Получить цветовую схему для текущей темы"""
        scheme = THEME_COLOR_MAP.get(self._current_theme, "light")
        return DARK_THEME_COLORS if scheme == "dark" else LIGHT_THEME_COLORS

    def get(
        self,
        name: str,
        size: int = 16,
        color: str = None,
        color_key: str = None,
        style: str = None,
        fallback_text: str = None,
    ):
        """
        Получить иконку (создается отложенно при первом вызове в GUI контексте).

        Args:
            name: Имя иконки (Bootstrap Icons)
            size: Размер в пикселях
            color: Явный цвет (hex) — переопределяет color_key
            color_key: Ключ цвета из схемы темы
            style: Стиль (пока не используется)
            fallback_text: Текст для отображения если иконка не найдена (например, эмодзи)

        Returns:
            BootstrapIcon объект или fallback_text
        """
        if not HAS_ICONS:
            return fallback_text

        # Определяем цвет
        if color is None and color_key:
            color = self.colors.get(color_key, self.colors["menu_icon"])

        cache_key = (name, size, color, style)
        if cache_key not in self._cache:
            try:
                self._cache[cache_key] = BootstrapIcon(name=name, size=size, color=color)
            except RuntimeError:
                # tkinter root не инициализирован — вернем fallback_text
                return fallback_text
            except Exception:
                print(f"⚠️ Ошибка загрузки иконки '{name}': используем fallback '{fallback_text}'")
                return fallback_text
        return self._cache[cache_key]

    def get_with_states(
        self,
        name: str,
        size: int = 16,
        color: str = None,
        hover_color: str = None,
        pressed_color: str = None,
        disabled_color: str = None,
        fallback_text: str = None,
    ):
        """
        Получить иконку с состояниями (Stateful Icons v3.1+).
        Автоматически меняет цвет при hover/pressed/disabled.

        Args:
            name: Имя иконки
            size: Размер
            color: Базовый цвет
            hover_color: Цвет при наведении
            pressed_color: Цвет при нажатии
            disabled_color: Цвет при отключении
            fallback_text: Fallback текст

        Returns:
            BootstrapIcon объект или fallback_text
        """
        icon = self.get(name, size, color, fallback_text=fallback_text)
        if icon is None or isinstance(icon, str):
            return icon
            
        # Сохраняем конфигурацию состояний для применения к виджету
        states = {}
        if hover_color:
            states["hover"] = {"color": hover_color}
        if pressed_color:
            states["pressed"] = {"color": pressed_color}
        if disabled_color:
            states["disabled"] = {"color": disabled_color}
            
        if states:
            icon._state_config = states
                
        return icon

    def get_icon_defs(self, icon_dict: dict) -> dict:
        """
        Получить определения иконок (без создания).
        Используется для предварительной настройки.
        """
        return icon_dict.copy()

    def clear_cache(self):
        """Очистить кэш иконок"""
        self._cache.clear()


# Глобальный экземпляр
icons = IconManager()


# ===== ПРЕДУСТАНОВЛЕННЫЕ НАБОРЫ ИКОНОК =====
# Возвращают определения иконок (name, size, color_key)
# Реальные объекты создаются при первом вызове icons.get()


def _make_icon(name, size, color_key=None, style=None):
    """Создать определение иконки"""
    return {"name": name, "size": size, "color_key": color_key, "style": style}


def _resolve_icon_def(defn):
    """Создать реальный объект иконки из определения"""
    if defn is None or not HAS_ICONS:
        return None
    return icons.get(
        defn["name"],
        size=defn["size"],
        color_key=defn.get("color_key"),
        style=defn.get("style"),
    )


def get_menu_icons(size=None):
    """Иконки для главного меню"""
    if not HAS_ICONS:
        return {}
    if size is None:
        size = ICON_SIZES["menu"]

    defs = {
        "file": _make_icon("folder", size, "menu_icon"),
        "open_mods": _make_icon("folder2-open", size, "menu_icon"),
        "save": _make_icon("floppy", size, "success", "fill"),
        "exit": _make_icon("box-arrow-right", size, "menu_icon"),
        "view": _make_icon("eye", size, "menu_icon"),
        "theme": _make_icon("palette", size, "accent"),
        "tabs": _make_icon("layout-three-columns", size, "menu_icon"),
        "show_tabs": _make_icon("eye-fill", size, "menu_icon"),
        "clear_log": _make_icon("trash3", size, "warning"),
        "history": _make_icon("clock-history", size, "menu_icon"),
        "tools": _make_icon("wrench", size, "menu_icon"),
        "verification": _make_icon("shield-check", size, "success", "fill"),
        "full_check": _make_icon("clipboard2-check", size, "menu_icon"),
        "integrity": _make_icon("file-earmark-check", size, "info"),
        "load_game": _make_icon("controller", size, "menu_icon"),
        "help": _make_icon("question-circle", size, "info"),
        "documentation": _make_icon("book", size, "menu_icon"),
        "about": _make_icon("info-circle", size, "info"),
        "shortcuts": _make_icon("keyboard", size, "menu_icon"),
        "language": _make_icon("translate", size, "menu_icon"),
        "debug_toggle": _make_icon("bug", size, "warning"),
        "debug_log": _make_icon("journal-text", size, "menu_icon"),
    }

    # Создаем реальные иконки
    return {k: _resolve_icon_def(v) for k, v in defs.items()}


def get_tab_icons(size=None):
    """Иконки для вкладок Notebook (чуть крупнее)"""
    if not HAS_ICONS:
        return {}
    if size is None:
        size = ICON_SIZES["tab"]

    defs = {
        "translation": _make_icon("translate", size, "primary"),
        "verification": _make_icon("shield-check", size, "success", "fill"),
        "duplicates": _make_icon("files-alt", size, "warning"),
        "settings": _make_icon("gear", size, "menu_icon", "fill"),
        "mods": _make_icon("box-seam", size, "info"),
        "filters": _make_icon("funnel", size, "menu_icon"),
        "dependencies": _make_icon("diagram-3", size, "menu_icon"),
        "editor": _make_icon("pencil-square", size, "accent"),
        "log": _make_icon("terminal", size, "menu_icon"),
    }

    return {k: _resolve_icon_def(v) for k, v in defs.items()}


def get_editor_toolbar_icons(size=None):
    """Иконки для панели инструментов редактора (крупные)"""
    if not HAS_ICONS:
        return {}
    if size is None:
        size = ICON_SIZES["toolbar"]

    save_size = ICON_SIZES["toolbar_large"]
    delete_size = ICON_SIZES["toolbar_large"]

    defs = {
        "open": _make_icon("folder2-open", size, "info", "fill"),
        "save": _make_icon("floppy", save_size, "success", "fill"),
        "refresh": _make_icon("arrow-clockwise", size, "menu_icon"),
        "undo": _make_icon("arrow-counterclockwise", size, "primary"),
        "redo": _make_icon("arrow-repeat", size, "primary"),
        "add": _make_icon("plus-circle", size, "success", "fill"),
        "delete": _make_icon("trash3", delete_size, "error", "fill"),
        "find": _make_icon("search", size, "menu_icon"),
        "replace": _make_icon("arrow-left-right", size, "menu_icon"),
        "export": _make_icon("download", size, "info"),
        "check": _make_icon("check2-circle", size, "success"),
        "spellcheck": _make_icon("spellcheck", size, "menu_icon"),
        "mass_edit": _make_icon("input-cursor-text", size, "menu_icon"),
        "auto_translate": _make_icon("translate", size, "accent"),
    }

    return {k: _resolve_icon_def(v) for k, v in defs.items()}


def get_status_bar_icons(size=None):
    """Иконки для статус-бара (семантические цвета)"""
    if not HAS_ICONS:
        return {}
    if size is None:
        size = ICON_SIZES["status"]

    defs = {
        "mods": _make_icon("box-seam", size, "menu_icon"),
        "translated": _make_icon("check-circle", size, "success", "fill"),
        "errors": _make_icon("exclamation-triangle", size, "error", "fill"),
        "warnings": _make_icon("exclamation-circle", size, "warning", "fill"),
        "info": _make_icon("info-circle", size, "info"),
    }

    return {k: _resolve_icon_def(v) for k, v in defs.items()}


def get_button_icons(size=None):
    """Иконки для кнопок действий"""
    if not HAS_ICONS:
        return {}
    if size is None:
        size = ICON_SIZES["button"]

    defs = {
        "play": _make_icon("play-fill", size, "success"),
        "pause": _make_icon("pause-fill", size, "warning"),
        "stop": _make_icon("stop-fill", size, "error"),
        "reset": _make_icon("arrow-counterclockwise", size, "menu_icon"),
        "browse": _make_icon("folder2-open", size, "info"),
        "copy": _make_icon("clipboard", size, "menu_icon"),
        "paste": _make_icon("clipboard-plus", size, "menu_icon"),
    }

    return {k: _resolve_icon_def(v) for k, v in defs.items()}


def get_tab_labels(size=None):
    """
    Получить кортежи (иконка, переведённый текст) для каждой вкладки.

    Returns:
        list[tuple]: Список кортежей (BootstrapIcon|None, str)
    """
    if not HAS_ICONS:
        return []
    if size is None:
        size = ICON_SIZES["tab"]

    labels = [
        ("translate", "Перевод"),
        ("shield-check", "Верификация"),
        ("files-alt", "Дубликаты"),
        ("gear", "Настройки"),
        ("box-seam", "Моды"),
        ("funnel", "Фильтры"),
        ("diagram-3", "Зависимости"),
        ("pencil-square", "Редактор"),
        ("terminal", "Лог"),
    ]

    result = []
    for icon_name, text in labels:
        icon = icons.get(icon_name, size=size)
        result.append((icon, text))
    return result


def get_dialog_header_icons(size=32):
    """
    Получить увеличенные иконки для заголовков диалогов.

    Args:
        size: Размер иконок (по умолчанию 32)

    Returns:
        dict[str, BootstrapIcon|None]: Словарь иконок для заголовков диалогов
    """
    if not HAS_ICONS:
        return {}

    defs = {
        "about": _make_icon("info-circle-fill", size, "info"),
        "shortcuts": _make_icon("keyboard", size, "menu_icon"),
        "documentation": _make_icon("book", size, "menu_icon"),
        "debug_log": _make_icon("bug", size, "warning"),
    }

    return {k: _resolve_icon_def(v) for k, v in defs.items()}


def get_dialog_icons(size=None):
    """Иконки для диалогов и сообщений"""
    if not HAS_ICONS:
        return {}
    if size is None:
        size = ICON_SIZES["dialog"]

    defs = {
        "success": _make_icon("check-circle-fill", size, "success"),
        "warning": _make_icon("exclamation-triangle-fill", size, "warning"),
        "error": _make_icon("x-circle-fill", size, "error"),
        "info": _make_icon("info-circle-fill", size, "info"),
        "question": _make_icon("question-circle-fill", size, "info"),
    }

    return {k: _resolve_icon_def(v) for k, v in defs.items()}
