# editor_history.py - Система истории изменений для редактора
"""
Модуль для реализации системы Undo/Redo в редакторе переводов.
Использует паттерн Command для хранения истории действий.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any
from loguru import logger


class ActionType(Enum):
    """Типы действий в истории"""

    EDIT = "edit"  # Редактирование записи
    ADD = "add"  # Добавление записи
    DELETE = "delete"  # Удаление записи
    RENAME = "rename"  # Переименование ключа


@dataclass
class HistoryEntry:
    """Запись в истории изменений"""

    action_type: ActionType
    key: str
    old_value: Any
    new_value: Any
    timestamp: float

    def __repr__(self):
        return f"HistoryEntry({self.action_type.value}, {self.key})"


class EditorHistory:
    """
    Система истории изменений с поддержкой Undo/Redo.

    Особенности:
    - Ограничение размера истории (по умолчанию 50 записей)
    - Автоматическое удаление старых записей при превышении лимита
    - Поддержка различных типов действий
    - Потокобезопасность (для будущего расширения)
    """

    def __init__(self, max_size: int = 50):
        """
        Инициализация истории.

        Args:
            max_size: Максимальное количество записей в истории
        """
        self.max_size = max_size
        self.history: list[HistoryEntry] = []
        self.current_index: int = -1
        self._listeners: list[Callable] = []

    def add_listener(self, listener: Callable):
        """Добавить слушателя изменений истории"""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable):
        """Удалить слушателя"""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_listeners(self):
        """Уведомить слушателей об изменениях"""
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                logger.error(f"Ошибка в слушателе истории: {e}")

    def add_entry(self, entry: HistoryEntry):
        """
        Добавить запись в историю.

        Args:
            entry: Запись для добавления
        """
        # Удаляем все записи после текущего индекса (при отмене и новом действии)
        if self.current_index < len(self.history) - 1:
            self.history = self.history[: self.current_index + 1]

        # Добавляем новую запись
        self.history.append(entry)
        self.current_index = len(self.history) - 1

        # Ограничиваем размер истории
        if len(self.history) > self.max_size:
            self.history = self.history[-self.max_size :]
            self.current_index = len(self.history) - 1

        self._notify_listeners()

    def can_undo(self) -> bool:
        """Проверить, можно ли отменить действие"""
        return self.current_index >= 0

    def can_redo(self) -> bool:
        """Проверить, можно ли повторить действие"""
        return self.current_index < len(self.history) - 1

    def undo(self) -> HistoryEntry | None:
        """
        Отменить последнее действие.

        Returns:
            Запись истории для отмены или None
        """
        if not self.can_undo():
            return None

        entry = self.history[self.current_index]
        self.current_index -= 1
        self._notify_listeners()
        return entry

    def redo(self) -> HistoryEntry | None:
        """
        Повторить отмененное действие.

        Returns:
            Запись истории для повтора или None
        """
        if not self.can_redo():
            return None

        self.current_index += 1
        entry = self.history[self.current_index]
        self._notify_listeners()
        return entry

    def clear(self):
        """Очистить всю историю"""
        self.history.clear()
        self.current_index = -1
        self._notify_listeners()

    def get_history_info(self) -> dict:
        """
        Получить информацию о истории.

        Returns:
            Словарь с информацией о истории
        """
        return {
            "total_entries": len(self.history),
            "current_index": self.current_index,
            "can_undo": self.can_undo(),
            "can_redo": self.can_redo(),
            "max_size": self.max_size,
        }

    def get_recent_entries(self, count: int = 10) -> list[HistoryEntry]:
        """
        Получить последние записи истории.

        Args:
            count: Количество записей

        Returns:
            Список последних записей
        """
        start_index = max(0, len(self.history) - count)
        return self.history[start_index:]


class EditCommand:
    """
    Команда редактирования для паттерна Command.
    Инкапсулирует информацию о действии и позволяет его отменить/повторить.
    """

    def __init__(
        self,
        key: str,
        old_value: str,
        new_value: str,
        apply_func: Callable[[str, str], None],
        undo_func: Callable[[str, str], None],
    ):
        """
        Инициализация команды.

        Args:
            key: Ключ записи
            old_value: Старое значение
            new_value: Новое значение
            apply_func: Функция применения изменения
            undo_func: Функция отмены изменения
        """
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.apply_func = apply_func
        self.undo_func = undo_func

    def execute(self):
        """Выполнить команду"""
        self.apply_func(self.key, self.new_value)

    def undo(self):
        """Отменить команду"""
        self.undo_func(self.key, self.old_value)


class HistoryManager:
    """
    Менеджер истории для интеграции с редактором.
    Обеспечивает удобный интерфейс для работы с историей изменений.
    """

    def __init__(self, max_history: int = 50):
        """
        Инициализация менеджера.

        Args:
            max_history: Максимальный размер истории
        """
        self.history = EditorHistory(max_size=max_history)
        self._edit_callbacks: dict[str, Callable] = {}

    def register_edit_callback(self, key: str, callback: Callable):
        """
        Зарегистрировать callback для редактирования.

        Args:
            key: Ключ записи
            callback: Функция обратного вызова
        """
        self._edit_callbacks[key] = callback

    def record_edit(self, key: str, old_value: str, new_value: str):
        """
        Записать редактирование в историю.

        Args:
            key: Ключ записи
            old_value: Старое значение
            new_value: Новое значение
        """
        import time

        entry = HistoryEntry(
            action_type=ActionType.EDIT,
            key=key,
            old_value=old_value,
            new_value=new_value,
            timestamp=time.time(),
        )

        self.history.add_entry(entry)

    def undo_last_edit(self) -> bool:
        """
        Отменить последнее редактирование.

        Returns:
            True если отмена выполнена успешно
        """
        entry = self.history.undo()
        if entry is None:
            return False

        # Вызываем callback для отмены изменения
        if entry.key in self._edit_callbacks:
            try:
                self._edit_callbacks[entry.key](entry.old_value)
                return True
            except Exception as e:
                print(f"Ошибка при отмене: {e}")
                return False

        return False

    def redo_last_edit(self) -> bool:
        """
        Повторить последнее отмененное редактирование.

        Returns:
            True если повтор выполнен успешно
        """
        entry = self.history.redo()
        if entry is None:
            return False

        # Вызываем callback для повтора изменения
        if entry.key in self._edit_callbacks:
            try:
                self._edit_callbacks[entry.key](entry.new_value)
                return True
            except Exception as e:
                print(f"Ошибка при повторе: {e}")
                return False

        return False

    def can_undo(self) -> bool:
        """Проверить возможность отмены"""
        return self.history.can_undo()

    def can_redo(self) -> bool:
        """Проверить возможность повтора"""
        return self.history.can_redo()

    def push_state(self, state: list):
        """
        Сохранить состояние в истории.

        Args:
            state: Состояние (список записей) для сохранения
        """
        import time
        import copy

        entry = HistoryEntry(
            action_type=ActionType.EDIT,
            key="__state__",
            old_value=None,
            new_value=copy.deepcopy(state),
            timestamp=time.time(),
        )

        self.history.add_entry(entry)

    def pop_state(self) -> list | None:
        """
        Восстановить состояние из истории.

        Returns:
            Состояние или None если история пуста
        """
        entry = self.history.undo()
        if entry is None or entry.key != "__state__":
            return None
        import copy
        return copy.deepcopy(entry.new_value)

    def redo_state(self) -> list | None:
        """
        Восстановить следующее состояние из истории.

        Returns:
            Состояние или None
        """
        entry = self.history.redo()
        if entry is None or entry.key != "__state__":
            return None
        import copy
        return copy.deepcopy(entry.new_value)

    def clear_history(self):
        """Очистить историю"""
        self.history.clear()

    def get_status(self) -> str:
        """
        Получить строку статуса истории.

        Returns:
            Строка статуса
        """
        info = self.history.get_history_info()
        if info["can_undo"] and info["can_redo"]:
            return f"История: {info['current_index'] + 1}/{info['total_entries']}"
        elif info["can_undo"]:
            return f"Можно отменить ({info['current_index'] + 1} действий)"
        elif info["can_redo"]:
            return f"Можно повторить ({info['total_entries'] - info['current_index'] - 1} действий)"
        else:
            return "История пуста"
