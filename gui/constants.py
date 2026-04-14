# gui/constants.py
"""
Глобальные константы для GUI приложения — Единые стандарты UI 2026
"""

# === Размеры окна ===
DEFAULT_WINDOW_GEOMETRY = "1100x800"
MIN_WINDOW_SIZE = (800, 600)  # (width, height)

# === Универсальные отступы ===
PAD_X = 5
PAD_Y = 5
PADY_SMALL = 2
PADY_MEDIUM = 3
PADY_LARGE = 5
PADX_SMALL = 2
PADX_LARGE = 5
PAD_BTN_X = 2
PAD_FRAME_X = 5
PAD_FRAME_Y = 5
PAD_LABEL_X = (0, 5)
PAD_ENTRY_X = 5
PAD_TREE_X = 5
PAD_TREE_Y = 5
BADGE_PADX = 8
BADGE_PADY = 4
BUTTON_WIDTH = 4
LABEL_WIDTH = 15
ENTRY_WIDTH_SMALL = 20

# === Цвета превью UI ===
PREVIEW_BG_DARK = "#2b2b2b"
PREVIEW_BG_LIGHT = "#ffffff"
PREVIEW_TEXT_DARK = "#d4d4d4"
PREVIEW_TEXT_LIGHT = "#2c3e50"
PREVIEW_OUTLINE_DARK = "#444444"
PREVIEW_OUTLINE_LIGHT = "#cccccc"
PREVIEW_ACCENT = "#0d6efd"
PREVIEW_ACCENT_OUTLINE = "#0a58ca"

# === Цвета логов ===
DEFAULT_LOG_BG = "#1e1e1e"
DEFAULT_LOG_TEXT = "#d4d4d4"
TAG_COLOR_INFO = "#4fc3f7"
TAG_COLOR_WARNING = "#ffb74d"
TAG_COLOR_ERROR = "#ef5350"
TAG_COLOR_SUCCESS = "#66bb6a"
TAG_TEXT_ON_DARK = "#ffffff"
TAG_TEXT_ON_LIGHT = "#000000"

# === Сохранение конфигурации ===
MAX_SAVE_RETRIES = 3
SAVE_RETRY_DELAY = 0.5  # секунды

# === Цвета статус-бара (ttkbootstrap bootstyles) ===
STATUS_BOOTSTYLES = {
    "error": "danger",
    "warning": "warning",
    "info": "info",
    "success": "success",
    "primary": "primary",
    "secondary": "secondary",
}

# === Иконки статусов ===
STATUS_ICONS = {
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "success": "✅",
    "critical": "🔴",
    "outdated": "🟡",
    "version_mismatch": "🟠",
    "missing_parent": "🔴",
    "custom": "🟣",
    "unknown": "⚪",
}

# === Прогресс-бары — bootstyles по операциям ===
PROGRESS_BOOTSTYLES = {
    "translation": "success-striped",
    "verification": "info-striped",
    "duplicates": "warning-striped",
    "dependencies": "primary-striped",
    "integrity": "secondary-striped",
}

# === Цвета статус-бара (HEX) ===
STATUS_COLOR_MODS = "#3b82f6"
STATUS_COLOR_TRANSLATED = "#22c55e"
STATUS_COLOR_ERRORS = "#ef4444"
STATUS_COLOR_WARNINGS = "#f59e0b"
STATUS_COLOR_LAST_ACTION = "gray"

# === Шрифты статус-бара ===
STATUS_FONT_SIZE = 7
STATUS_FONT_FAMILY = "Segoe UI"
STATUS_PROGRESS_THICKNESS = 16

# === Превью цветов и шрифтов ===
FONT_PREVIEW_HEIGHT = 2
FONT_PREVIEW_WIDTH = 20
COLOR_PREVIEW_WIDTH = 30
COLOR_PREVIEW_HEIGHT = 20

# === Toast-уведомления ===
TOAST_DURATION = 3000  # мс
TOAST_POSITION = (50, 50, "ne")  # правый верхний угол

# === Стандарты шрифтов ===
FONT_DEFAULT = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_SUBTITLE = ("Segoe UI", 12, "bold")
FONT_SMALL = ("Segoe UI", 8)
FONT_MONO = ("Consolas", 9)

# === Анимация/Throttle ===
DEBOUNCE_DELAY_MS = 150
PROGRESS_UPDATE_INTERVAL = 100  # мс
UI_COLOR_PREVIEW_HEIGHT = 60
LOG_COLOR_PREVIEW_HEIGHT = 6
LABEL_WIDTH_LARGE = 18
BUTTON_WIDTH_SMALL = 12
COLLAPSIBLE_BOOTSTYLE = {
    "fonts": "info",
    "colors": "primary",
    "logs": "success",
    "tags": "info",
}

# === Дополнительные цвета превью ===
PREVIEW_BG_LOG = "#1e1e1e"
PREVIEW_TEXT_LOG = "#d4d4d4"

# === Дополнительные цвета интерфейса ===
DEFAULT_TEXT_COLOR = "#2c3e50"
DEFAULT_BG_COLOR = "#ffffff"
DEFAULT_ACCENT_COLOR = "#3498db"
DARK_PREVIEW_BG = "#333333"

# === Дополнительные отступы ===
PADX_MEDIUM = 3
PADX_XLARGE = 10
PADY_XLARGE = 10

# === Дополнительные размеры виджетов ===
ENTRY_WIDTH = 50
ENTRY_WIDTH_TINY = 10
HISTORY_TEXT_HEIGHT = 3
LOG_TAG_PREVIEW_WIDTH = 30

# === Версии RimWorld ===
SUPPORTED_RIMWORLD_VERSIONS = {"1.6", "1.5", "1.4", "1.3", "1.2", "1.1", "Common"}

# === Логирование ===
LOG_PREVIEW_LENGTH = 50
