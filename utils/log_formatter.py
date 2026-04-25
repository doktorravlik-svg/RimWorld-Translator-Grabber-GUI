# utils/log_formatter.py
"""
Улучшенный форматтер логов с поддержкой секций, статистики и детализации.

Используется для:
- Подробного вывода во вкладку "Лог"
- Debug-режима с временными метками
- Сводок после каждой операции
"""

import time


class LogSection:
    """Контекстный менеджер для создания секций в логе"""

    def __init__(self, parent, title, icon="📄"):
        self.parent = parent
        self.title = title
        self.icon = icon
        self.start_time = None
        self.items = []

        # Ищем logger в разных местах
        self._log_method = None

        # 1. Проверяем parent.logger (TranslationWorker)
        if hasattr(parent, "logger") and parent.logger:
            if hasattr(parent.logger, "info"):
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

    def __enter__(self):
        self.start_time = time.time()
        separator = "─" * 60
        self._log(f"\n{separator}")
        self._log(f"{self.icon} {self.title}")
        self._log(separator)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        status = "✅ Успешно" if exc_type is None else f"❌ Ошибка: {exc_val}"
        self._log(f"   ⏱️  Время: {elapsed:.2f}с")
        self._log(f"   📊 Элементов: {len(self.items)}")
        self._log(f"   Статус: {status}")
        return False

    def _log(self, message):
        """Универсальный метод логирования"""
        if self._log_method:
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
