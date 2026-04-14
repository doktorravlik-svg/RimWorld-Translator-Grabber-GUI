# gui/dialogs/__init__.py
"""
Диалоговые окна приложения RimWorld Translator Grabber.
"""

from gui.dialogs.about_dialog import show_about
from gui.dialogs.debug_log_dialog import show_debug_log
from gui.dialogs.documentation_dialog import show_documentation
from gui.dialogs.history_dialog import show_history
from gui.dialogs.shortcuts_dialog import show_shortcuts

__all__ = [
    "show_about",
    "show_debug_log",
    "show_documentation",
    "show_history",
    "show_shortcuts",
]
