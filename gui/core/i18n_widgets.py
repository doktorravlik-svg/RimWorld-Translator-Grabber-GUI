# gui/core/i18n_widgets.py
"""
Обёртки для виджетов с поддержкой автоматического обновления при смене языка.

Использование:
    from gui.core.i18n_widgets import I18nLabel, I18nButton
    
    # Вместо:
    label = ttk.Label(parent, text=tr("my_key", "Текст"))
    
    # Используйте:
    label = I18nLabel(parent, "my_key", "Текст")
"""

import tkinter as tk
from tkinter import ttk


class I18nMixin:
    """
    Миксин для виджетов с поддержкой i18n.
    Автоматически обновляет текст при событии <<LanguageChanged>>.
    """

    def set_i18n_key(self, key, default_text=""):
        """
        Установить i18n ключ.
        
        Args:
            key: Ключ перевода
            default_text: Текст по умолчанию если перевод не найден
        """
        self._i18n_key = key
        self._i18n_default = default_text
        self._update_text()

    def _update_text(self):
        """Обновить текст виджета из текущего языка"""
        if not hasattr(self, '_i18n_key'):
            return
        
        try:
            from gui.gui_i18n import i18n
            new_text = i18n.tr(self._i18n_key, self._i18n_default)
            
            # Обновляем текст в зависимости от типа виджета
            if hasattr(self, 'config'):
                self.config(text=new_text)
        except Exception as e:
            print(f"Ошибка обновления текста виджета {self._i18n_key}: {e}")


class I18nLabel(I18nMixin, ttk.Label):
    """Label с поддержкой i18n"""
    
    def __init__(self, master=None, i18n_key=None, default="", **kwargs):
        if i18n_key:
            # Получаем перевод для initial text
            from gui.gui_i18n import i18n
            kwargs['text'] = i18n.tr(i18n_key, default)
        
        super().__init__(master, **kwargs)
        
        if i18n_key:
            self.set_i18n_key(i18n_key, default)


class I18nButton(I18nMixin, ttk.Button):
    """Button с поддержкой i18n"""
    
    def __init__(self, master=None, i18n_key=None, default="", **kwargs):
        if i18n_key:
            from gui.gui_i18n import i18n
            kwargs['text'] = i18n.tr(i18n_key, default)
        
        super().__init__(master, **kwargs)
        
        if i18n_key:
            self.set_i18n_key(i18n_key, default)


class I18nCheckbutton(I18nMixin, ttk.Checkbutton):
    """Checkbutton с поддержкой i18n"""
    
    def __init__(self, master=None, i18n_key=None, default="", **kwargs):
        if i18n_key:
            from gui.gui_i18n import i18n
            kwargs['text'] = i18n.tr(i18n_key, default)
        
        super().__init__(master, **kwargs)
        
        if i18n_key:
            self.set_i18n_key(i18n_key, default)


class I18nLabelFrame(I18nMixin, ttk.LabelFrame):
    """LabelFrame с поддержкой i18n"""
    
    def __init__(self, master=None, i18n_key=None, default="", **kwargs):
        if i18n_key:
            from gui.gui_i18n import i18n
            kwargs['text'] = i18n.tr(i18n_key, default)
        
        super().__init__(master, **kwargs)
        
        if i18n_key:
            self.set_i18n_key(i18n_key, default)


def setup_auto_language_update(widget_container):
    """
    Настроить автоматическое обновление языка для всех дочерних виджетов.
    
    Вызывается once для контейнера (вкладки, диалога и т.д.)
    
    Args:
        widget_container: Контейнер (Frame, Toplevel, etc.)
    """
    def on_language_changed(event=None):
        """Обновить все I18n виджеты внутри контейнера"""
        _update_i18n_widgets(widget_container)
    
    widget_container.bind("<<LanguageChanged>>", on_language_changed)
    return on_language_changed


def _update_i18n_widgets(container):
    """Рекурсивно обновить все I18n виджеты"""
    if hasattr(container, '_i18n_key'):
        container._update_text()
    
    if hasattr(container, 'winfo_children'):
        for child in container.winfo_children():
            _update_i18n_widgets(child)
