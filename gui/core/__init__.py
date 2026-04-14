# gui/core/__init__.py
"""
Базовые модули ядра для RimWorld Translator Grabber.
"""

from gui.core.menu_builder import MenuBuilder
from gui.core.tab_manager import TabManager
from gui.core.ui_builder import UIBuilder

__all__ = [
    "MenuBuilder",
    "TabManager",
    "UIBuilder",
]
