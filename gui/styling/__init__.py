# gui/styling/__init__.py
"""
Модули стилизации для RimWorld Translator Grabber.
"""

from gui.styling.color_manager import apply_colors
from gui.styling.font_manager import apply_fonts, get_font_tuple
from gui.styling.theme_manager import (
    DEFAULT_THEME_KEY,
    THEME_DESCRIPTIONS,
    TTKBOOTSTRAP_THEMES,
    apply_theme,
    change_theme,
    get_available_bootstrap_themes,
    get_theme_choices,
    get_theme_name_display,
    get_theme_names,
    is_dark_theme,
    resolve_bootstrap_theme,
)

__all__ = [
    "DEFAULT_THEME_KEY",
    "THEME_DESCRIPTIONS",
    "TTKBOOTSTRAP_THEMES",
    "apply_colors",
    "apply_fonts",
    "apply_theme",
    "change_theme",
    "get_available_bootstrap_themes",
    "get_font_tuple",
    "get_theme_choices",
    "get_theme_name_display",
    "get_theme_names",
    "is_dark_theme",
    "resolve_bootstrap_theme",
]
