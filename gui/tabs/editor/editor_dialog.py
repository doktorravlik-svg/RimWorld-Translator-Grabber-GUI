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


def __getattr__(name):
    """Ленивый импорт TranslationEditorDialog (PEP 562).

    ВАЖНО: не объявлять TranslationEditorDialog на уровне модуля —
    иначе __getattr__ не вызывается и `from ... import X` вернёт None.
    """
    if name == "TranslationEditorDialog":
        from gui.tabs.gui_translation_editor import TranslationEditorDialog as _cls

        globals()["TranslationEditorDialog"] = _cls
        return _cls
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
