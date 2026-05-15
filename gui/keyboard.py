# gui/keyboard.py - Универсальная поддержка горячих клавиш для всех раскладок
"""
Модуль для обработки горячих клавиш независимо от языковой раскладки.
Использует физический keycode вместо символов, что гарантирует работу
на любой раскладке (RU, EN, DE, и т.д.)
"""

from ttkbootstrap.tooltip import ToolTip

# === Таблица физических кодов клавиш (Windows) ===
# Эти коды одинаковы для всех раскладок
KEYCODES = {
    # Буквы (основные)
    "A": 65,
    "B": 66,
    "C": 67,
    "D": 68,
    "E": 69,
    "F": 70,
    "G": 71,
    "H": 72,
    "I": 73,
    "J": 74,
    "K": 75,
    "L": 76,
    "M": 77,
    "N": 78,
    "O": 79,
    "P": 80,
    "Q": 81,
    "R": 82,
    "S": 83,
    "T": 84,
    "U": 85,
    "V": 86,
    "W": 87,
    "X": 88,
    "Y": 89,
    "Z": 90,
    # Служебные клавиши
    "ENTER": 13,
    "RETURN": 13,
    "ESCAPE": 27,
    "SPACE": 32,
    "TAB": 9,
    "BACKSPACE": 8,
    "DELETE": 46,
    # F-клавиши
    "F1": 112,
    "F2": 113,
    "F3": 114,
    "F4": 115,
    "F5": 116,
    "F6": 117,
    "F7": 118,
    "F8": 119,
    "F9": 120,
    "F10": 121,
    "F11": 122,
    "F12": 123,
    # Навигация
    "UP": 38,
    "DOWN": 40,
    "LEFT": 37,
    "RIGHT": 39,
    "HOME": 36,
    "END": 35,
    "PAGE_UP": 33,
    "PAGE_DOWN": 34,
    "INSERT": 45,
}

# Модификаторы
MODIFIERS = {
    "CTRL": 0x0004,
    "ALT": 0x20000,
    "SHIFT": 0x0001,
}


class HotkeyManager:
    """
    Универсальный менеджер горячих клавиш.

    Работает на всех языковых раскладках через проверку физических keycode.
    """

    def __init__(self, root):
        """
        Инициализирует менеджер горячих клавиш.

        Args:
            root: Главный ttk.Window
        """
        self.root = root
        self.handlers = {}
        self._bind_all()

    def _bind_all(self):
        """Привязывает глобальный обработчик ко всему приложению."""
        self.root.bind_all("<KeyPress>", self._on_key_press)

        # ✅ Инженерный патч: Исправляет работу Ctrl+A/C/V/X/Z на русской раскладке для ВСЕХ полей ввода
        # Работает по физическому keycode, не зависит от раскладки
        shortcuts = [
            (65, "<<SelectAll>>"),   # A
            (67, "<<Copy>>"),        # C
            (86, "<<Paste>>"),       # V
            (88, "<<Cut>>"),         # X
        ]

        def _check_and_trigger(event):
            for keycode, virtual_event in shortcuts:
                if event.keycode == keycode:
                    event.widget.event_generate(virtual_event)
                    return "break"

        # Применяем ко всем классам полей ввода
        self.root.bind_class("Entry", "<Control-KeyPress>", _check_and_trigger)
        self.root.bind_class("TEntry", "<Control-KeyPress>", _check_and_trigger)
        self.root.bind_class("Text", "<Control-KeyPress>", _check_and_trigger)
        self.root.bind_class("Combobox", "<Control-KeyPress>", _check_and_trigger)
        self.root.bind_class("Searchbox", "<Control-KeyPress>", _check_and_trigger)

    def _on_key_press(self, event):
        """
        Глобальный обработчик нажатий клавиш.

        Args:
            event: Событие нажатия клавиши
        """
        # ✅ Исправление: Если фокус в поле ввода, пропускаем только горячие клавиши
        # с модификаторами Ctrl/Alt, обычные буквы идут в поле ввода
        try:
            focused = self.root.focus_get()
            if focused and hasattr(focused, "winfo_class"):
                if focused.winfo_class() in ("Entry", "Text", "Combobox", "Searchbox"):

                    # ✅ Белый список комбинаций которые работают ВСЕГДА, даже в поле поиска
                    ctrl = bool(event.state & MODIFIERS["CTRL"])
                    alt = bool(event.state & MODIFIERS["ALT"])

                    # F1-F12, Escape, Enter работают всегда
                    if event.keysym.startswith('F') and event.keysym[1:].isdigit():
                        # Это F клавиша - обрабатываем
                        pass
                    elif event.keysym in ("Escape", "Return", "F5"):
                        # Служебные клавиши - обрабатываем
                        pass
                    elif ctrl or alt:
                        # ✅ Все Ctrl и Alt комбинации работают даже при вводе текста
                        pass
                    else:
                        # ✅ Все остальные клавиши идут напрямую в поле ввода
                        return
        except:
            pass

        # Определяем модификаторы
        ctrl = bool(event.state & MODIFIERS["CTRL"])
        alt = bool(event.state & MODIFIERS["ALT"])
        shift = bool(event.state & MODIFIERS["SHIFT"])

        # Проверяем F-клавиши и служебные через keysym
        keysym = event.keysym

        # Ищем подходящий обработчик
        # Приоритет: Ctrl+Alt+Key > Ctrl+Key > Alt+Key > Key > F-клавиши

        # 1. F-клавиши и служебные (не зависят от раскладки)
        if keysym in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"):
            handler_key = keysym
            if handler_key in self.handlers:
                return self.handlers[handler_key](event)

        # 2. Служебные клавиши
        if keysym in ("Return", "Escape", "Delete", "Insert", "Tab", "BackSpace"):
            handler_key = keysym
            if handler_key in self.handlers:
                return self.handlers[handler_key](event)

        # 3. Клавиши навигации (стрелки и т.д.) - проверяем и с модификаторами
        if keysym in ("Up", "Down", "Left", "Right", "Home", "End", "Prior", "Next"):
            # Преобразуем keysym в наше имя
            keysym_map = {
                "Up": "UP",
                "Down": "DOWN",
                "Left": "LEFT",
                "Right": "RIGHT",
                "Home": "HOME",
                "End": "END",
                "Prior": "PAGE_UP",
                "Next": "PAGE_DOWN",
            }
            key_name = keysym_map.get(keysym, keysym)

            if ctrl:
                handler_key = f"Ctrl+{KEYCODES[key_name]}"
                if handler_key in self.handlers:
                    return self.handlers[handler_key](event)

            # Без модификаторов
            handler_key = str(KEYCODES[key_name])
            if handler_key in self.handlers:
                return self.handlers[handler_key](event)

        # 4. Комбинации с Ctrl
        if ctrl:
            # ✅ Если фокус в поле ввода — не перехватываем стандартные комбинации редактирования
            try:
                focused = self.root.focus_get()
                if focused:
                    widget_class = focused.winfo_class()
                    if widget_class in ("Entry", "Text", "Combobox", "Searchbox", "TEntry"):
                        # Стандартные комбинации для редактирования текста — пропускаем
                        standard_ctrl_keys = {65, 67, 86, 88, 89, 90}  # A, C, V, X, Y, Z
                        if event.keycode in standard_ctrl_keys:
                            return
            except:
                pass

            handler_key = f"Ctrl+{event.keycode}"
            if handler_key in self.handlers:
                return self.handlers[handler_key](event)

        # 5. Комбинации с Alt
        if alt:
            handler_key = f"Alt+{event.keycode}"
            if handler_key in self.handlers:
                return self.handlers[handler_key](event)

        # 6. Одиночные клавиши по keycode
        handler_key = str(event.keycode)
        if handler_key in self.handlers:
            return self.handlers[handler_key](event)

    def register(self, key, handler, tooltip_text=None, widget=None):
        """
        Регистрирует обработчик горячей клавиши.

        Args:
            key: Клавиша (например, 'Ctrl+S', 'F1', 'Delete', 'Ctrl+O')
            handler: Функция-обработчик
            tooltip_text: Текст подсказки для виджета
            widget: Виджет, к которому привязать подсказку (опционально)
        """
        # Парсим клавишу
        if "+" in key:
            parts = key.split("+")
            modifiers = [p.upper() for p in parts[:-1]]
            key_part = parts[-1]

            # Определяем keycode или keysym
            if key_part in KEYCODES:
                keycode = KEYCODES[key_part]
            elif key_part.upper() in KEYCODES:
                keycode = KEYCODES[key_part.upper()]
            else:
                # Пробуем как одиночную клавишу
                keycode = key_part

            # Формируем ключ обработчика
            handler_key = ""
            if "CTRL" in modifiers:
                handler_key += "Ctrl+"
            if "ALT" in modifiers:
                handler_key += "Alt+"
            if "SHIFT" in modifiers:
                handler_key += "Shift+"

            if isinstance(keycode, int):
                handler_key += str(keycode)
            else:
                handler_key = keycode

            self.handlers[handler_key] = handler
        # Одиночная клавиша
        elif key in KEYCODES:
            self.handlers[str(KEYCODES[key])] = handler
        elif key in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"):
            self.handlers[key] = handler
        elif key in ("Return", "Escape", "Delete", "Insert"):
            self.handlers[key] = handler

        # Добавляем подсказку к виджету
        if tooltip_text and widget:
            ToolTip(widget, text=tooltip_text)

    def get_hotkey_text(self, key):
        """
        Возвращает текстовое описание горячей клавиши для отображения в UI.

        Args:
            key: Клавиша (например, 'Ctrl+S')

        Returns:
            Строка для отображения (например, 'Ctrl+S (Ctrl+Ы)')
        """
        # Для отображения в интерфейсе
        return key


def setup_default_hotkeys(manager, app_instance):
    """
    Настраивает стандартные горячие клавиши для приложения.

    Args:
        manager: Экземпляр HotkeyManager
        app_instance: Экземпляр главного приложения (GUI)
    """
    from gui.gui_i18n import tr

    # Файл
    manager.register(
        "Ctrl+O",
        lambda e: app_instance.tab_manager.mods_tab._browse_mods(),
        tooltip_text=tr("menu_open_mods", "Открыть папку модов (Ctrl+O)"),
    )
    manager.register(
        "Ctrl+S",
        lambda e: app_instance.save_config(),
        tooltip_text=tr("menu_save_settings", "Сохранить настройки (Ctrl+S)"),
    )

    # Верификация
    manager.register(
        "F5",
        lambda e: app_instance.start_full_verification(),
        tooltip_text=tr("menu_full_check", "Полная проверка (F5)"),
    )

    # Справка
    manager.register(
        "F1",
        lambda e: app_instance._show_documentation(),
        tooltip_text=tr("menu_documentation", "Документация (F1)"),
    )
