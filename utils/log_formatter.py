# utils/log_formatter.py
"""
Улучшенный форматтер логов с поддержкой секций, статистики и детализации.

Используется для:
- Подробного вывода во вкладку "Лог"
- Debug-режима с временными метками
- Сводок после каждой операции
"""

import time

from loguru import logger


class LogSection:
    """Контекстный менеджер для создания секций в логе"""

    __slots__ = ('parent', 'title', 'icon', 'start_time', '_items', '_log_method')

    def __init__(self, parent, title, icon="📄"):
        self.parent = parent
        self.title = title
        self.icon = icon
        self.start_time = None
        self._items = []
        self._log_method = None

        # 0. Check if parent itself is a logger-like object (has info method)
        if callable(getattr(parent, "info", None)):
            self._log_method = parent.info

        # 1. Проверяем parent.logger (TranslationWorker)
        if not self._log_method and hasattr(parent, "logger") and parent.logger:
            if callable(getattr(parent.logger, "info", None)):
                self._log_method = parent.logger.info

        # 2. Проверяем parent.log_callback (если есть)
        if not self._log_method and hasattr(parent, "log_callback"):
            if callable(parent.log_callback):
                self._log_method = parent.log_callback

        # 3. Проверяем parent.log (если это LogPanel или подобный)
        if not self._log_method and hasattr(parent, "log"):
            if callable(parent.log):
                self._log_method = parent.log

        # 4. Fallback на print
        if not self._log_method:
            self._log_method = print

    @property
    def items(self):
        """Возвращает список элементов, восстанавливая его если нужно"""
        if not isinstance(self._items, list):
            # If _items is a Logger or other non-list object, create new list
            self._items = []
        return self._items

    def _safe_len(self):
        """Safe length calculation that handles non-list types"""
        if isinstance(self._items, list):
            return len(self._items)
        return 0

    def __len__(self):
        return self._safe_len()

    def __enter__(self):
        self.start_time = time.time()
        separator = "─" * 60
        self._log(f"\n{separator}")
        self._log(f"{self.icon} {self.title}")
        self._log(separator)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type is None:
            status = "✅ Успешно"
        else:
            status = f"❌ Ошибка: {exc_val}"
            # Логируем факт аварийного завершения секции
            logger.error(f"Секция '{self.title}' завершилась аварийно: {exc_val}")

        self._log(f"   ⏱️  Время: {elapsed:.2f}с")
        self._log(f"   📊 Элементов: {self._safe_len()}")
        self._log(f"   Статус: {status}")
        return False

    def _log(self, message):
        """Универсальный метод логирования"""
        if self._log_method and callable(self._log_method):
            self._log_method(message)

    def add_item(self, message, level="info"):
        """Добавить элемент в секцию"""
        self.items.append({"message": message, "level": level, "time": time.time()})

        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "debug": "🔍",
        }
        icon = icons.get(level, "•")
        self._log(f"   {icon} {message}")