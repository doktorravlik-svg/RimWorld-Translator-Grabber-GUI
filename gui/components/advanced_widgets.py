# gui/components/advanced_widgets.py
"""
Расширенные GUI-компоненты для RimWorld Translator Grabber.

Включает:
- AutocompleteCombobox: Выпадающий список с автодополнением
- AutocompleteEntry: Поле ввода с автодополнением (выпадающий список)
- CollapsibleFrame: Сворачиваемый/разворачиваемый фрейм
- ValidatedEntry: Поле ввода с валидацией
"""

import tkinter as tk
from tkinter import ttk


class AutocompleteCombobox(ttk.Combobox):
    """
    Combobox с автодополнением.

    При вводе текста автоматически подбирает варианты из списка
    и выделяет общую часть.

    Args:
        values: Список вариантов для автодополнения
        case_sensitive: Учитывать ли регистр (по умолчанию False)
        min_chars: Мин. количество символов для начала автодополнения
    """
    
    def __init__(
        self,
        master=None,
        values=None,
        case_sensitive: bool = False,
        min_chars: int = 1,
        **kwargs,
    ):
        if values is None:
            values = []
        
        self._values = values
        self._case_sensitive = case_sensitive
        self._min_chars = min_chars
        self._autocompleting = False
        
        super().__init__(master, values=values, **kwargs)
        
        # Привязка событий для автодополнения
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<FocusOut>", self._on_focus_out)
    
    def _on_key_release(self, event):
        """Обработка ввода текста."""
        # Игнорируем специальные клавиши
        if event.keysym in ("Return", "Tab", "Escape", "Up", "Down", 
                           "Left", "Right", "Home", "End", "Prior", "Next"):
            return
        
        # Контрольные клавиши
        if event.state & 0x4:  # Ctrl
            return
        
        self._autocomplete()
    
    def _autocomplete(self):
        """Выполняет автодополнение."""
        if self._autocompleting:
            return
        
        value = self.get()
        
        # Проверяем минимальное количество символов
        if len(value) < self._min_chars:
            self.configure(values=self._values)
            return
        
        # Находим совпадения
        matches = self._find_matches(value)
        
        if matches:
            self._autocompleting = True
            
            # Обновляем список значений
            self.configure(values=matches)
            
            # Если есть точное совпадение — не автодополняем
            if value in matches:
                self.set(value)
                self.icursor(tk.END)
                self.event_generate("<ComboboxSelected>")
            else:
                # Автодополняем первым совпадением
                self.set(matches[0])
                self.icursor(len(value))
                # Выделяем дополненную часть
                self.select_range(len(value), tk.END)
            
            self._autocompleting = False
    
    def _find_matches(self, value: str) -> list:
        """Находит совпадения для автодополнения."""
        if not value:
            return self._values
        
        if self._case_sensitive:
            return [v for v in self._values if value.lower() in v.lower()]
        else:
            value_lower = value.lower()
            return [v for v in self._values if value_lower in v.lower()]
    
    def _on_focus_out(self, event=None):
        """При потере фокуса — восстанавливаем полный список."""
        self.configure(values=self._values)
    
    def set_values(self, values: list):
        """Обновить список вариантов."""
        self._values = values
        self.configure(values=values)
    
    def add_value(self, value: str):
        """Добавить новый вариант в список."""
        if value not in self._values:
            self._values.append(value)
            self.configure(values=self._values)


class AutocompleteEntry(ttk.Entry):
    """
    Поле ввода с выпадающим списком автодополнения.

    В отличие от AutocompleteCombobox, показывает выпадающий список
    только при вводе, а не постоянно.

    Args:
        values: Список вариантов
        case_sensitive: Учитывать ли регистр
        min_chars: Мин. количество символов для показа списка
        max_visible: Макс. количество видимых элементов в списке
    """
    
    def __init__(
        self,
        master=None,
        values=None,
        case_sensitive: bool = False,
        min_chars: int = 1,
        max_visible: int = 8,
        **kwargs,
    ):
        if values is None:
            values = []
        
        self._values = values
        self._case_sensitive = case_sensitive
        self._min_chars = min_chars
        self._max_visible = max_visible
        self._listbox = None
        self._listbox_visible = False
        
        super().__init__(master, **kwargs)
        
        # Привязка событий
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Down>", self._on_down)
        self.bind("<Up>", self._on_up)
        self.bind("<Return>", self._on_return)
        self.bind("<Escape>", self._on_escape)
    
    def _on_key_release(self, event):
        """Обработка ввода."""
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        if event.state & 0x4:  # Ctrl
            return
        
        self._update_listbox()
    
    def _update_listbox(self):
        """Обновить выпадающий список."""
        value = self.get()
        
        if len(value) < self._min_chars:
            self._hide_listbox()
            return
        
        matches = self._find_matches(value)
        
        if not matches:
            self._hide_listbox()
            return
        
        self._show_listbox(matches)
    
    def _find_matches(self, value: str) -> list:
        """Найти совпадения."""
        if self._case_sensitive:
            return [v for v in self._values if value.lower() in v.lower()]
        else:
            value_lower = value.lower()
            return [v for v in self._values if value_lower in v.lower()]
    
    def _show_listbox(self, matches: list):
        """Показать выпадающий список."""
        if self._listbox is None:
            self._create_listbox()
        
        # Обновляем содержимое
        self._listbox.delete(0, tk.END)
        visible_items = matches[:self._max_visible]
        for item in visible_items:
            self._listbox.insert(tk.END, item)
        
        # Позиционируем под полем ввода
        self._listbox.place(
            x=0,
            y=self.winfo_height(),
            width=self.winfo_width(),
        )
        self._listbox.lift()
        self._listbox_visible = True
    
    def _create_listbox(self):
        """Создать выпадающий список."""
        self._listbox = tk.Listbox(
            self.master,
            height=self._max_visible,
            activestyle="none",
            selectmode=tk.SINGLE,
        )
        self._listbox.bind("<Button-1>", self._on_listbox_select)
        self._listbox.bind("<Motion>", self._on_listbox_hover)
    
    def _hide_listbox(self):
        """Скрыть выпадающий список."""
        if self._listbox is not None:
            self._listbox.place_forget()
            self._listbox_visible = False
    
    def _on_listbox_select(self, event):
        """Выбор элемента из списка."""
        if self._listbox is None:
            return
        
        selection = self._listbox.curselection()
        if selection:
            self.set(self._listbox.get(selection[0]))
            self.icursor(tk.END)
            self._hide_listbox()
            self.event_generate("<<AutocompleteSelect>>")
    
    def _on_listbox_hover(self, event):
        """Подсветка элемента при наведении."""
        if self._listbox is None:
            return
        
        index = self._listbox.nearest(event.y)
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(index)
        self._listbox.activate(index)
    
    def _on_down(self, event):
        """Навигация вниз по списку."""
        if self._listbox_visible and self._listbox is not None:
            self._listbox.focus_set()
            return "break"
    
    def _on_up(self, event):
        """Навигация вверх по списку."""
        if self._listbox_visible and self._listbox is not None:
            self._listbox.focus_set()
            return "break"
    
    def _on_return(self, event):
        """Выбор элемента по Enter."""
        if self._listbox_visible and self._listbox is not None:
            selection = self._listbox.curselection()
            if selection:
                self.set(self._listbox.get(selection[0]))
                self.icursor(tk.END)
                self._hide_listbox()
                self.event_generate("<<AutocompleteSelect>>")
                return "break"
    
    def _on_escape(self, event):
        """Закрыть список по Escape."""
        self._hide_listbox()
    
    def _on_focus_out(self, event=None):
        """Скрыть список при потере фокуса."""
        # Небольшая задержка, чтобы клики по списку успевали обработаться
        self.after(100, self._hide_listbox)
    
    def set_values(self, values: list):
        """Обновить список вариантов."""
        self._values = values
    
    def add_value(self, value: str):
        """Добавить новый вариант."""
        if value not in self._values:
            self._values.append(value)


class CollapsibleFrame(ttk.LabelFrame):
    """
    Сворачиваемый/разворачиваемый фрейм.

    Позволяет скрыть дополнительные настройки за кнопкой.

    Args:
        text: Заголовок фрейма
        collapsed: Начальное состояние (True = свёрнут)
        animation_duration: Длительность анимации в мс (0 = без анимации)
    """
    
    def __init__(
        self,
        master=None,
        text: str = "",
        collapsed: bool = False,
        animation_duration: int = 0,
        **kwargs,
    ):
        self._collapsed = collapsed
        self._animation_duration = animation_duration
        self._content_frame = None
        self._toggle_button = None
        self._arrow_label = None
        
        super().__init__(master, text=text, **kwargs)
        
        # Фрейм для заголовка с кнопкой
        self._header_frame = ttk.Frame(self)
        self._header_frame.pack(fill="x", padx=5, pady=2)
        
        # Кнопка сворачивания
        self._toggle_button = ttk.Button(
            self._header_frame,
            text=self._get_toggle_text(),
            command=self.toggle,
            width=5,
        )
        self._toggle_button.pack(side="left", padx=2)
        
        # Метка с заголовком
        ttk.Label(
            self._header_frame,
            text=text,
        ).pack(side="left", padx=5)
        
        # Контент-фрейм
        self._content_frame = ttk.Frame(self)
        
        # Если не свёрнут — показываем сразу
        if not self._collapsed:
            self._content_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    def _get_toggle_text(self):
        """Текст кнопки в зависимости от состояния."""
        return "▼" if not self._collapsed else "▶"
    
    def toggle(self):
        """Переключить состояние."""
        if self._collapsed:
            self.expand()
        else:
            self.collapse()
    
    def collapse(self):
        """Свернуть."""
        if not self._collapsed:
            self._content_frame.pack_forget()
            self._collapsed = True
            self._toggle_button.config(text="▶")
            self.event_generate("<<Collapsed>>")
    
    def expand(self):
        """Развернуть."""
        if self._collapsed:
            if self._animation_duration > 0:
                self._animate_expand()
            else:
                self._content_frame.pack(fill="both", expand=True, padx=5, pady=5)
                self._collapsed = False
                self._toggle_button.config(text="▼")
                self.event_generate("<<Expanded>>")
    
    def _animate_expand(self):
        """Анимированное разворачивание (заглушка для будущего улучшения)."""
        # TODO: Реализовать плавную анимацию через after()
        self._content_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self._collapsed = False
        self._toggle_button.config(text="▼")
        self.event_generate("<<Expanded>>")
    
    @property
    def content_frame(self):
        """Возвращает фрейм для добавления контента."""
        return self._content_frame
    
    @property
    def is_collapsed(self):
        """Возвращает текущее состояние."""
        return self._collapsed
    
    def is_expanded(self):
        """Возвращает, развёрнут ли фрейм."""
        return not self._collapsed


class CollapsingFrame(ttk.Frame):
    """
    Фрейм с анимированным сворачиванием/разворачиванием содержимого.

    В отличие от CollapsibleFrame, сохраняет высоту контента при сворачивании
    и позволяет плавно анимировать процесс.

    Args:
        text: Заголовок фрейма
        collapsed: Начальное состояние (True = свёрнут)
    """
    
    def __init__(
        self,
        master=None,
        text: str = "",
        collapsed: bool = False,
        **kwargs,
    ):
        self._collapsed = collapsed
        self._content_frame = None
        self._toggle_button = None
        self._target_height = 0
        self._current_height = 0
        self._animation_id = None
        
        super().__init__(master, **kwargs)
        
        self._header_frame = ttk.Frame(self)
        self._header_frame.pack(fill="x", padx=5, pady=2)
        
        self._toggle_button = ttk.Button(
            self._header_frame,
            text="▼",
            command=self.toggle,
            width=5,
        )
        self._toggle_button.pack(side="left", padx=2)
        
        ttk.Label(self._header_frame, text=text, font=("Segoe UI", 10, "bold")).pack(
            side="left", padx=5
        )
        
        self._content_frame = ttk.Frame(self)
        self._content_frame.bind("<Configure>", self._on_content_configure)
        
        if not self._collapsed:
            self._content_frame.pack(fill="both", expand=True, padx=5, pady=5)
            self._toggle_button.config(text="▼")
        else:
            self._toggle_button.config(text="▶")
    
    def _on_content_configure(self, event=None):
        """Сохраняет целевую высоту контента."""
        self._target_height = self._content_frame.winfo_reqheight()
    
    def toggle(self):
        """Переключить состояние."""
        if self._collapsed:
            self.expand()
        else:
            self.collapse()
    
    def collapse(self):
        """Свернуть с анимацией."""
        if self._collapsed:
            return
        
        if self._animation_id:
            self.after_cancel(self._animation_id)
        
        self._animate_collapse()
    
    def _animate_collapse(self):
        """Анимированное сворачивание."""
        self._collapsed = True
        self._toggle_button.config(text="▶")
        self._content_frame.pack_forget()
        self.event_generate("<<Collapsed>>")
    
    def expand(self):
        """Развернуть с анимацией."""
        if not self._collapsed:
            return
        
        if self._animation_id:
            self.after_cancel(self._animation_id)
        
        self._collapsed = False
        self._toggle_button.config(text="▼")
        self._content_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.event_generate("<<Expanded>>")
    
    @property
    def content_frame(self):
        """Возвращает фрейм для добавления контента."""
        return self._content_frame
    
    @property
    def is_collapsed(self):
        """Возвращает текущее состояние."""
        return self._collapsed
    
    def is_expanded(self):
        """Возвращает, развёрнут ли фрейм."""
        return not self._collapsed


class ValidatedEntry(ttk.Entry):
    """
    Поле ввода с встроенной валидацией.

    Args:
        validate_type: Тип валидации
            - 'number': Только числа
            - 'float': Числа с плавающей точкой
            - 'alpha': Только буквы
            - 'alphanumeric': Буквы и цифры
            - 'path': Путь к файлу/папке
            - 'url': URL адрес
            - 'email': Email
            - 'custom': Пользовательская валидация (через validate_func)
        validate_func: Пользовательская функция валидации
        error_callback: Callback при ошибке валидации
        max_length: Максимальная длина
    """
    
    def __init__(
        self,
        master=None,
        validate_type: str = "none",
        validate_func=None,
        error_callback=None,
        max_length: int = 0,
        **kwargs,
    ):
        self._validate_type = validate_type
        self._validate_func = validate_func
        self._error_callback = error_callback
        self._max_length = max_length
        self._last_valid_value = ""
        self._validation_result = True
        
        super().__init__(master, **kwargs)
        
        # Настройка валидации
        vcmd = (self.register(self._validate), "%P")
        self.configure(validate="key", validatecommand=vcmd)
        
        # Привязка для восстановления при ошибке
        self.bind("<FocusOut>", self._on_focus_out)
    
    def _validate(self, new_value: str) -> bool:
        """Проверяет валидность введённого значения."""
        # Проверка на максимальную длину
        if self._max_length > 0 and len(new_value) > self._max_length:
            self._on_error("Превышена максимальная длина")
            return False
        
        # Пустое значение — всегда валидно
        if not new_value:
            self._validation_result = True
            return True
        
        # Валидация по типу
        if self._validate_type == "number":
            result = new_value.lstrip("-").isdigit()
        elif self._validate_type == "float":
            try:
                float(new_value)
                result = True
            except ValueError:
                result = False
        elif self._validate_type == "alpha":
            result = new_value.isalpha()
        elif self._validate_type == "alphanumeric":
            result = new_value.isalnum()
        elif self._validate_type == "url":
            result = new_value.startswith(("http://", "https://", "localhost"))
        elif self._validate_type == "email":
            result = "@" in new_value and "." in new_value.split("@")[-1]
        elif self._validate_type == "path":
            result = True  # Разрешаем любые пути
        elif self._validate_type == "custom" and self._validate_func:
            result = self._validate_func(new_value)
        else:
            result = True
        
        if result:
            self._validation_result = True
            self._last_valid_value = new_value
        else:
            self._on_error(f"Недопустимый формат: {self._validate_type}")
        
        return result
    
    def _on_error(self, message: str):
        """Обработка ошибки валидации."""
        self._validation_result = False
        if self._error_callback:
            self._error_callback(message)
    
    def _on_focus_out(self, event=None):
        """При потере фокуса — восстанавливаем последнее валидное значение."""
        if not self._validation_result:
            self.delete(0, tk.END)
            self.insert(0, self._last_valid_value)
            self._validation_result = True
    
    def is_valid(self) -> bool:
        """Проверяет, валидно ли текущее значение."""
        return self._validation_result
    
    def get_valid_value(self) -> str:
        """Возвращает последнее валидное значение."""
        return self._last_valid_value if not self._validation_result else self.get()
