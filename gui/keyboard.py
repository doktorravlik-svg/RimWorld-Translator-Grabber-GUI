# gui/keyboard.py - Универсальная поддержка горячих клавиш для всех раскладок
"""
Модуль для обработки горячих клавиш независимо от языковой раскладки.
Использует физический keycode вместо символов, что гарантирует работу
на любой раскладке (RU, EN, DE, и т.д.)
"""

from ttkbootstrap.tooltip import ToolTip

HOTKEYS_CONFIG = {
    "open_mods": {
        "key": "Ctrl+O",
        "tooltip": "gui_tooltip_open_mods",
        "tooltip_default": "Открыть папку модов (Ctrl+O / Ctrl+Щ)",
    },
    "save_settings": {
        "key": "Ctrl+S",
        "tooltip": "gui_tooltip_save_settings",
        "tooltip_default": "Сохранить настройки (Ctrl+S / Ctrl+Ы)",
    },
    "clear_log": {
        "key": "Ctrl+L",
        "tooltip": "gui_tooltip_clear_log",
        "tooltip_default": "Очистить лог (Ctrl+L / Ctrl+Д)",
    },
    "show_history": {
        "key": "Ctrl+H",
        "tooltip": "gui_tooltip_show_history",
        "tooltip_default": "История операций (Ctrl+H / Ctrl+Р)",
    },
    "show_shortcuts": {
        "key": "F1",
        "tooltip": "gui_tooltip_show_shortcuts",
        "tooltip_default": "Горячие клавиши (F1)",
    },
    "start_translation": {
        "key": "F5",
        "tooltip": "gui_tooltip_start_translation",
        "tooltip_default": "Начать перевод (F5)",
    },
    "start_verification": {
        "key": "F6",
        "tooltip": "gui_tooltip_start_verification",
        "tooltip_default": "Верификация (F6)",
    },
    "full_check": {
        "key": "F9",
        "tooltip": "gui_tooltip_full_check",
        "tooltip_default": "Полная проверка (F9)",
    },
}

def register_hotkeys(hotkey_manager, callbacks, i18n_tr=None):
    """
    Регистрирует все горячие клавиши из конфигурации.
    
    Args:
        hotkey_manager: Экземпляр HotkeyManager
        callbacks: Словарь обработчиков ({name: callable})
        i18n_tr: Функция для перевода (i18n.tr(key, default))
    """
    if i18n_tr is None:
        i18n_tr = lambda key, default="": default

    for name, config in HOTKEYS_CONFIG.items():
        handler = callbacks.get(name)
        if handler:
            tooltip_key = config["tooltip"]
            tooltip_default = config["tooltip_default"]
            hotkey_manager.register(
                config["key"],
                lambda e, h=handler: h(),
                tooltip_text=i18n_tr(tooltip_key, tooltip_default),
            )

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

# === Кроссплатформенные keycode-карты ===
# Для Linux/X11 физические коды отличаются от Windows
import platform
import sys

if platform.system() == "Linux":
    # Linux/X11 keycodes
    KEYCODES_LINUX = {
        "A": 38, "B": 56, "C": 54, "D": 40, "E": 26, "F": 41, "G": 42,
        "H": 43, "I": 31, "J": 44, "K": 45, "L": 46, "M": 57, "N": 58,
        "O": 32, "P": 33, "Q": 24, "R": 27, "S": 39, "T": 28, "U": 30,
        "V": 55, "W": 25, "X": 53, "Y": 29, "Z": 52,
    }
    KEYCODES.update(KEYCODES_LINUX)
elif platform.system() == "Darwin":
    # macOS keycodes (based on X11 on macOS)
    KEYCODES_MACOS = {
        "A": 0, "B": 11, "C": 8, "D": 2, "E": 14, "F": 3, "G": 5,
        "H": 4, "I": 34, "J": 38, "K": 40, "L": 37, "M": 46, "N": 45,
        "O": 35, "P": 36, "Q": 6, "R": 15, "S": 7, "T": 16, "U": 6,
        "V": 9, "W": 13, "X": 7, "Y": 10, "Z": 12,
    }
    KEYCODES.update(KEYCODES_MACOS)

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
        except Exception:
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
            except Exception:
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



