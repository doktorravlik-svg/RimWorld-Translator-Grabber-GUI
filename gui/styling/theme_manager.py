# gui/styling/theme_manager.py
"""
Управление темами ttkbootstrap для RimWorld Translator Grabber.

Обновлено под ttkbootstrap 2.2+ (2026):
- Полный набор современных тем (Catppuccin, Nord, Tokyo Night, Everforest, ...)
- Надёжное определение тёмной/светлой темы через единый реестр
- Удобные хелперы для построения меню выбора темы
"""

import warnings

import ttkbootstrap as ttk

# =====================================================================
# Реестр тем: config_key -> ttkbootstrap 2.x theme name
#
# ВАЖНО: использовать только имена из Style.theme_names().
# Все ключи ниже совместимы со старыми конфигами (theme = "light"/"dark"/...),
# поэтому сохранённые настройки пользователей продолжают работать.
# =====================================================================
TTKBOOTSTRAP_THEMES = {
    # --- Базовые (обратная совместимость) ---
    "light": "bootstrap-light",
    "dark": "bootstrap-dark",
    "ocean": "minty-light",
    "forest": "united-light",
    "solar": "solarized-light",
    "vapor": "vapor-light",
    "cyborg": "dracula-dark",
    "superhero": "gruvbox-dark",
    # --- Новые темы ttkbootstrap 2.2.x ---
    "nord": "nord-dark",
    "nord_light": "nord-light",
    "catppuccin": "catppuccin-dark",
    "catppuccin_light": "catppuccin-light",
    "tokyo": "tokyo-night-dark",
    "tokyo_light": "tokyo-night-light",
    "one": "one-dark",
    "one_light": "one-light",
    "everforest": "everforest-dark",
    "everforest_light": "everforest-light",
    "pulse": "pulse-dark",
    "pulse_light": "pulse-light",
    "pydata": "pydata-dark",
    "pydata_light": "pydata-light",
    "sandstone": "sandstone-dark",
    "sandstone_light": "sandstone-light",
    "minty": "minty-dark",
    "dracula_light": "dracula-light",
    "gruvbox_light": "gruvbox-light",
    "united_dark": "united-dark",
    "minty_dark": "minty-dark",
    "solar_dark": "solarized-dark",
    "bootstrap": "bootstrap-dark",  # дефолт ttkbootstrap 2.x
}

# Описания тем для отображения в меню (в порядке отображения)
THEME_DESCRIPTIONS = {
    # --- Базовые ---
    "light": "☀️ Светлая (Bootstrap Light)",
    "dark": "🌙 Тёмная (Bootstrap Dark)",
    "ocean": "🌊 Океан (Minty Light)",
    "forest": "🌲 Лес (United Light)",
    "solar": "🔆 Солнечная (Solarized Light)",
    "vapor": "💨 Пар (Vapor Light)",
    "cyborg": "🤖 Киборг (Dracula Dark)",
    "superhero": "🦸 Супергерой (Gruvbox Dark)",
    # --- Новые ---
    "nord": "🏔 Nord Dark",
    "nord_light": "🏔 Nord Light",
    "catppuccin": "🐱 Catppuccin Dark",
    "catppuccin_light": "🐱 Catppuccin Light",
    "tokyo": "🌃 Tokyo Night",
    "tokyo_light": "🌃 Tokyo Night Light",
    "one": "1️⃣ Atom One Dark",
    "one_light": "1️⃣ Atom One Light",
    "everforest": "🌲 Everforest Dark",
    "everforest_light": "🌲 Everforest Light",
    "pulse": "💜 Pulse Dark",
    "pulse_light": "💜 Pulse Light",
    "pydata": "🐼 PyData Dark",
    "pydata_light": "🐼 PyData Light",
    "sandstone": "🏜 Sandstone Dark",
    "sandstone_light": "🏜 Sandstone Light",
}

# Тема по умолчанию для новых пользователей
DEFAULT_THEME_KEY = "light"

# Тёмные темы ttkbootstrap 2.x (для корректной подстройки цветов UI)
_DARK_THEMES = frozenset(
    {
        "bootstrap-dark",
        "dracula-dark",
        "gruvbox-dark",
        "minty-dark",
        "nord-dark",
        "one-dark",
        "solarized-dark",
        "united-dark",
        "vapor-dark",
        "catppuccin-dark",
        "everforest-dark",
        "pulse-dark",
        "pydata-dark",
        "sandstone-dark",
        "tokyo-night-dark",
    }
)

_LEGACY_THEMES_INSTALLED = False


def install_legacy_themes_if_needed():
    """Install legacy themes once (ttkbootstrap 2.x keeps pre-2.0 theme names as
    a migration convenience; installation is idempotent, so do it lazily).
    The 2.x DeprecationWarning about legacy names is muted here because this
    call is intentional for backward compatibility (training GUI themes)."""
    global _LEGACY_THEMES_INSTALLED
    if _LEGACY_THEMES_INSTALLED:
        return
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ttk.install_legacy_themes()
        _LEGACY_THEMES_INSTALLED = True
    except Exception:
        pass  # Already installed or not available


def resolve_bootstrap_theme(theme_key: str) -> str:
    """
    Преобразовать ключ конфига в имя темы ttkbootstrap.

    Args:
        theme_key: Ключ темы ("light", "nord", ...) или уже имя ttkbootstrap

    Returns:
        Валидное имя темы ttkbootstrap (всегда fallback на bootstrap-light)
    """
    if not theme_key:
        return TTKBOOTSTRAP_THEMES[DEFAULT_THEME_KEY]

    bs_theme = TTKBOOTSTRAP_THEMES.get(theme_key)
    if bs_theme:
        return bs_theme

    # Прямое имя ttkbootstrap (например, из чужого конфига) — нормализуем
    if theme_key in _DARK_THEMES or theme_key.endswith(("-dark", "-light")):
        return theme_key

    return TTKBOOTSTRAP_THEMES[DEFAULT_THEME_KEY]


def is_dark_theme(theme_key_or_name: str) -> bool:
    """
    Проверить, является ли тема тёмной.

    Принимает как ключ конфига ("nord"), так и прямое имя ttkbootstrap
    ("nord-dark"). Неизвестные темы считаются светлыми (безопасный дефолт).

    Args:
        theme_key_or_name: Ключ темы или имя ttkbootstrap

    Returns:
        True если тема тёмная
    """
    if not theme_key_or_name:
        return False

    # Явное имя ttkbootstrap
    if theme_key_or_name in _DARK_THEMES:
        return True

    # Ключ конфига -> имя ttkbootstrap -> проверка
    bs_theme = TTKBOOTSTRAP_THEMES.get(theme_key_or_name)
    if bs_theme:
        return bs_theme in _DARK_THEMES

    # Эвристика для неизвестных/новых имён
    return theme_key_or_name.endswith("-dark")


def get_theme_names() -> list[str]:
    """
    Возвращает список всех доступных ключей тем.

    Returns:
        Список ключей тем
    """
    return list(THEME_DESCRIPTIONS.keys())


def get_theme_name_display(theme_key: str) -> str:
    """
    Возвращает отображаемое имя темы.

    Args:
        theme_key: Ключ темы

    Returns:
        Отображаемое имя или ключ если не найдено
    """
    return THEME_DESCRIPTIONS.get(theme_key, theme_key)


def get_theme_choices() -> list[tuple[str, str]]:
    """
    Вернуть список (ключ, отображаемое имя) для построения меню.

    Returns:
        Список кортежей в порядке отображения
    """
    return [(key, THEME_DESCRIPTIONS[key]) for key in THEME_DESCRIPTIONS]


def get_available_bootstrap_themes() -> list[str]:
    """
    Вернуть имена тем, реально доступные в текущей установке ttkbootstrap.

    Returns:
        Отфильтрованный список имён из Style.theme_names()
    """
    try:
        available = set(ttk.Style().theme_names())
    except Exception:
        available = set()
    return [
        bs_name
        for bs_name in TTKBOOTSTRAP_THEMES.values()
        if not available or bs_name in available
    ]


def _get_style_object(style_or_window):
    """Extract Style object from Window or return Style directly."""
    if hasattr(style_or_window, "style"):
        return style_or_window.style
    return style_or_window


def apply_theme(style_or_window, theme_name: str):
    """
    Применить тему ttkbootstrap.

    Args:
        style_or_window: ttkbootstrap Style или Window
        theme_name: Имя темы из конфига (light, dark, ocean, nord, ...)
    """
    install_legacy_themes_if_needed()
    style = _get_style_object(style_or_window)
    bs_theme = resolve_bootstrap_theme(theme_name)
    try:
        style.theme_use(bs_theme)
    except Exception:
        # Последний fallback: гарантированно существующая светлая тема
        style.theme_use("bootstrap-light")


def change_theme(config, style_or_window, theme_name: str, log_callback=None):
    """
    Сменить тему оформления.

    Args:
        config: Словарь конфигурации
        style_or_window: ttkbootstrap Style или Window
        theme_name: Новое имя темы
        log_callback: Функция для логирования
    """
    config["theme"] = theme_name
    apply_theme(style_or_window, theme_name)
    if log_callback:
        log_callback(f"Тема изменена на: {get_theme_name_display(theme_name)}")
