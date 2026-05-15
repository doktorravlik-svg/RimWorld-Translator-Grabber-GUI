# gui/core/i18n_updater.py
"""
Система автоматического обновления переводов во всех виджетах.

Работает через:
1. Сканирование всех виджетов
2. Поиск виджетов с текстом содержащим ключи перевода
3. Автоматическое обновление через i18n.tr()
"""

from tkinter import ttk

# Маппинг переводов для обратного поиска (текст → ключ)
_TRANSLATION_CACHE = {}


def build_translation_map():
    """
    Построить карту переводов: текст → ключ.
    Вызывается один раз при загрузке.
    """
    from gui.gui_i18n import i18n

    _TRANSLATION_CACHE.clear()

    for lang_code, translations in i18n.translations.items():
        for key, text in translations.items():
            # Пропускаем _meta и другие не-строковые значения
            if not isinstance(text, str):
                continue
            # Сохраняем для всех языков
            _TRANSLATION_CACHE[text.strip()] = key


def find_widget_key(widget):
    """
    Найти i18n ключ для виджета по его текущему тексту.

    Returns:
        str: Ключ перевода или None
    """
    try:
        current_text = widget.cget("text")
        if not current_text:
            return None

        # Ищем в кэше
        return _TRANSLATION_CACHE.get(current_text.strip())
    except:
        return None


def update_widget_if_translatable(widget):
    """
    Обновить виджет если он использует перевод.

    Returns:
        bool: True если виджет был обновлён
    """
    try:
        # Специальная обработка для Treeview
        if isinstance(widget, ttk.Treeview):
            return _update_treeview_headings(widget)

        current_text = widget.cget("text")
        if not current_text:
            return False

        # Проверяем есть ли виджет уже _i18n_key
        if hasattr(widget, "_i18n_key"):
            from gui.gui_i18n import i18n

            new_text = i18n.tr(widget._i18n_key, current_text)
            if new_text != current_text:
                widget.config(text=new_text)
                return True
            return False

        # Ищем ключ по тексту
        key = find_widget_key(widget)
        if key:
            from gui.gui_i18n import i18n

            new_text = i18n.tr(key, current_text)
            if new_text != current_text:
                widget.config(text=new_text)
                # Регистрируем ключ для будущих обновлений
                widget._i18n_key = key
                return True

        return False
    except:
        return False


def _update_treeview_headings(treeview):
    """Обновить заголовки колонок Treeview"""
    updated = False
    try:
        for col in treeview["columns"]:
            current_heading = treeview.heading(col, "text")
            if not current_heading:
                continue

            # Ищем ключ по тексту заголовка
            key = _TRANSLATION_CACHE.get(current_heading.strip())
            if key:
                from gui.gui_i18n import i18n

                new_text = i18n.tr(key, current_heading)
                if new_text != current_heading:
                    treeview.heading(col, text=new_text)
                    updated = True
    except Exception:
        pass

    return updated


def _update_notebook_tabs(notebook):
    """Обновить названия вкладок notebook"""
    updated = False
    try:
        tab_count = notebook.index("end")
        for i in range(tab_count):
            current_text = notebook.tab(i, "text")
            if not current_text:
                continue

            # Ищем ключ по тексту вкладки
            key = _TRANSLATION_CACHE.get(current_text.strip())
            if key:
                from gui.gui_i18n import i18n

                new_text = i18n.tr(key, current_text)
                if new_text != current_text:
                    notebook.tab(i, text=new_text)
                    updated = True
    except Exception:
        pass

    return updated


def update_all_widgets_in_container(container):
    """
    Обновить все переводимые виджеты в контейнере.

    Args:
        container: Контейнер (Frame, Notebook, Toplevel, etc.)

    Returns:
        int: Количество обновлённых виджетов
    """
    updated = 0

    def _recursive_update(widget):
        nonlocal updated

        # Если это Notebook - обновить названия вкладок
        if isinstance(widget, ttk.Notebook):
            if _update_notebook_tabs(widget):
                updated += 10  # Приблизительное количество

        # Обновляем сам виджет
        if update_widget_if_translatable(widget):
            updated += 1

        # Рекурсивно обновляем дочерние
        if hasattr(widget, "winfo_children"):
            for child in widget.winfo_children():
                _recursive_update(child)

    _recursive_update(container)
    return updated


def register_widget_i18n(widget, key, default_text):
    """
    Зарегистрировать виджет с i18n ключом.

    Используйте при создании виджета:
        label = ttk.Label(parent, text=tr("my_key", "Текст"))
        register_widget_i18n(label, "my_key", "Текст")

    Args:
        widget: Виджет
        key: i18n ключ
        default_text: Текст по умолчанию
    """
    widget._i18n_key = key
    widget._i18n_default = default_text


def setup_auto_update(container):
    """
    Настроить автоматическое обновление переводов для контейнера.

    Вызывается при создании вкладки/диалога:
        setup_auto_update(self.notebook)

    Args:
        container: Контейнер
    """

    def on_language_changed(event=None):
        updated = update_all_widgets_in_container(container)
        if updated > 0:
            print(f"✅ Обновлено {updated} виджетов")

    container.bind("<<LanguageChanged>>", on_language_changed, add=True)

    return on_language_changed
