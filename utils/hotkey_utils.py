# utils/hotkey_utils.py
"""
Утилиты для поддержки мультираскладочных горячих клавиш.

Этот модуль обеспечивает работу горячих клавиш независимо от
текущей раскладки клавиатуры (RU, EN, UK, DE и т.д.)
"""

from gui.keyboard import HotkeyManager, KEYCODES, MODIFIERS

# Экспортируем для удобства
__all__ = [
    "HotkeyManager",
    "KEYCODES",
    "MODIFIERS",
    "create_hotkey_handler",
    "bind_hotkey",
]


def create_hotkey_handler(root, key_sequence: str, callback):
    """
    Создаёт обработчик горячей клавиши с поддержкой всех раскладок.

    Args:
        root: Главный ttk.Window
        key_sequence: Последовательность клавиш (например, 'Ctrl+S', 'F5')
        callback: Функция для вызова

    Returns:
        HotkeyManager с зарегистрированным обработчиком
    """
    manager = HotkeyManager(root)
    manager.register(key_sequence, lambda e: callback())
    return manager


def bind_hotkey(root, key_sequence: str, callback):
    """
    Привязывает горячую клавишу к приложению.

    Это удобная обёртка над HotkeyManager для быстрой привязки.

    Args:
        root: Главный ttk.Window
        key_sequence: Последовательность клавиш (например, 'Ctrl+O', 'F1')
        callback: Функция для вызова при нажатии

    Returns:
        Функция для отмены привязки (unbind)
    """
    manager = HotkeyManager(root)
    manager.register(key_sequence, lambda e: callback())

    def unbind():
        """Отменить привязку."""
        # Удаляем обработчик из managers.handlers
        pass  # Реализация при необходимости

    return unbind
