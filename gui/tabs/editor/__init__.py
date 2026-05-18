# gui/tabs/editor/__init__.py
"""
Модули редактора переводов.

Разделение gui_translation_editor.py на логические компоненты:
- TranslationEditorTab: Вкладка выбора файлов/папок (editor_file_browser.py)
- WrappingToolbar: Панель инструментов с переносом (editor_toolbar.py)
- TranslationEditorDialog: Диалог редактиирования (пока в gui_translation_editor.py)
- SyntaxHighlighter: Подсветка синтаксиса XML
- QualityChecker: Проверка качества переводов
- DiffViewer: Просмотр различий
"""

from gui.tabs.editor.diff_viewer import DiffViewer
from gui.tabs.editor.editor_file_browser import TranslationEditorTab
from gui.tabs.editor.editor_toolbar import WrappingToolbar
from gui.tabs.editor.quality_checker import TranslationQualityChecker
from gui.tabs.editor.syntax_highlighter import SpellingChecker, XMLSyntaxHighlighter

__all__ = [
    "DiffViewer",
    "SpellingChecker",
    "TranslationEditorTab",
    "TranslationQualityChecker",
    "WrappingToolbar",
    "XMLSyntaxHighlighter",
]


def get_editor_dialog():
    """Получить класс TranslationEditorDialog (ленивый импорт)"""
    from gui.tabs.editor.editor_dialog import get_editor_dialog_class

    return get_editor_dialog_class()
