# gui/tabs/editor/editor_dialog.py
"""
Точка входа в диалог редактирования переводов.

Импортирует TranslationEditorDialog из основного файла для избежания
циклических зависимостей. В будущем этот файл будет заменён на
полноценное разделение TranslationEditorDialog на модули.
"""

# Динамический импорт из оригинального файла
# (после полного разделения gui_translation_editor.py импортировать отсюда)


def get_editor_dialog_class():
    """Получить класс TranslationEditorDialog"""
    import sys
    import os

    # Импортируем из оригинального файла
    from gui.tabs.gui_translation_editor import TranslationEditorDialog

    return TranslationEditorDialog


# Для удобства прямого импорта
TranslationEditorDialog = None


def __getattr__(name):
    """Ленивый импорт TranslationEditorDialog"""
    if name == "TranslationEditorDialog":
        global TranslationEditorDialog
        if TranslationEditorDialog is None:
            from gui.tabs.gui_translation_editor import TranslationEditorDialog

            TranslationEditorDialog = TranslationEditorDialog
        return TranslationEditorDialog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
