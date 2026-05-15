# utils/ui_helpers.py
"""
Вспомогательные функции для Tkinter UI.

Включает:
- Debounced обновители прогресса
- Factory функции для создания компонентов
"""

from __future__ import annotations

from loguru import logger
import time
import tkinter as tk
from typing import Any


# ============================================================
# УДАЛЕНО: debounce() — сломанная реализация (возвращала "pending")
# УДАЛЕНО: setup_debounce_entry() — 0 использований
# УДАЛЕНО: _on_debounced_key_release() — внутренний для setup_debounce_entry
# ============================================================


class DebouncedProgressUpdater:
    """
    Debounced обновитель прогресса для предотвращения мерцания UI.

    При частых обновлениях прогресса (например, каждые 10ms) UI может
    мерцать или тормозить. Этот класс группирует обновления и применяет
    их с заданной частотой.

    Поддерживает:
    - Адаптивный delay (автоподстройка под общее время)
    - Throttle режим (гарантированные обновления)
    - Потокобезопасность через root.after()

    Args:
        widget: Виджет с методами update_progress() или finish_translation()
        delay_ms: Задержка между обновлениями в мс (по умолчанию 100ms)
        use_root_after: Использовать root.after() для безопасности потоков
        adaptive: Включить адаптивный delay (автоподстройка)
        throttle_ms: Минимальный интервал между обновлениями (throttle)
    """

    def __init__(
        self,
        widget: Any,
        delay_ms: int = 100,
        use_root_after: bool = True,
        adaptive: bool = False,
        throttle_ms: int = 0,
    ) -> None:
        self.widget = widget
        self.delay_ms = delay_ms
        self.use_root_after = use_root_after
        self.adaptive = adaptive
        self.throttle_ms = throttle_ms

        self._timer_id: str | None = None
        self._pending_value: int = 0
        self._pending_message: str = ""
        self._tk_root: tk.Tk | None = None

        # Для адаптивного delay
        self._start_time: float = 0
        self._total_updates: int = 0
        self._last_update_time: float = 0

    def set_root(self, root: tk.Tk) -> None:
        """Установить Tk root для безопасности потоков."""
        self._tk_root = root

    def update(self, value: int, message: str = "") -> None:
        """
        Запланировать обновление прогресса с debounce.

        Args:
            value: Значение прогресса (0-100)
            message: Сообщение для отображения
        """
        self._pending_value = value
        self._pending_message = message
        self._total_updates += 1

        # Throttle: если прошло меньше throttle_ms, пропускаем
        if self.throttle_ms > 0:
            now = time.time() * 1000  # ms
            if self._last_update_time > 0:
                elapsed = now - self._last_update_time
                if elapsed < self.throttle_ms:
                    self._debounce_update()
                    return
            self._last_update_time = now

        self._debounce_update()

    def finish(self, success: bool = True) -> None:
        """
        Немедленно завершить перевод (без debounce).

        Применяет последнее обновление прогресса.
        НЕ вызывает widget.finish_translation() чтобы избежать рекурсии.
        Callback finish_translation() вызывается из gui.py напрямую.

        Args:
            success: Успешно ли завершён перевод
        """
        self._cancel_timer()
        self._apply()
        # Убрано: self.widget.finish_translation(success) - вызывает рекурсию!

    def flush(self) -> None:
        """Немедленно применить все отложенные обновления."""
        self._cancel_timer()
        self._apply()

    def reset(self) -> None:
        """Сбросить состояние для повторного использования."""
        self._cancel_timer()
        self._pending_value = 0
        self._pending_message = ""
        self._start_time = 0
        self._total_updates = 0
        self._last_update_time = 0

    def _debounce_update(self) -> None:
        """Внутренний метод debounce."""
        current_delay = self._calculate_adaptive_delay()
        self._cancel_timer()

        if self._tk_root:
            self._timer_id = self._tk_root.after(current_delay, self._apply)
        elif hasattr(self.widget, "after"):
            self._timer_id = self.widget.after(current_delay, self._apply)
        else:
            self._apply()

    def _calculate_adaptive_delay(self) -> int:  # ✅ Исправлена опечатка: adive -> adaptive
        """Рассчитать адаптивный delay на основе прогресса."""
        if not self.adaptive:
            return self.delay_ms

        if self._total_updates > 100:
            return min(self.delay_ms * 3, 500)
        elif self._total_updates > 50:
            return min(self.delay_ms * 2, 300)
        else:
            return self.delay_ms

    def _cancel_timer(self) -> None:
        """Отменить текущий таймер."""
        if self._timer_id is not None:
            try:
                if self._tk_root:
                    self._tk_root.after_cancel(self._timer_id)
                elif hasattr(self.widget, "after_cancel"):
                    self.widget.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

    def _apply(self) -> None:
        """Применить обновление прогресса."""
        try:
            # Проверяем что widget не использует debounced updater
            # чтобы избежать бесконечной рекурсии
            if hasattr(self.widget, "update_progress"):
                # Проверяем не внутри ли мы уже DebouncedProgressUpdater
                if hasattr(self.widget, "_progress_updater") and self.widget._progress_updater:
                    # Виджет использует debounced updater - обновляем напрямую
                    self.widget.progress_var.set(self._pending_value)
                    if self._pending_message and hasattr(self.widget, "progress_label"):
                        self.widget.progress_label.config(text=self._pending_message)
                else:
                    # Fallback: вызываем update_progress()
                    self.widget.update_progress(self._pending_value, self._pending_message)
            elif hasattr(self.widget, "progress_var"):
                self.widget.progress_var.set(self._pending_value)
                if self._pending_message and hasattr(self.widget, "progress_label"):
                    self.widget.progress_label.config(text=self._pending_message)
        except Exception as e:
            logger.error(f"Ошибка при обновлении прогресса: {e}")

        self._timer_id = None
        self._last_update_time = time.time() * 1000


def create_debounced_progress(
    widget: Any,
    root: tk.Tk | None = None,
    delay_ms: int = 100,
    adaptive: bool = False,
    throttle_ms: int = 0,
) -> DebouncedProgressUpdater:
    """
    Создать debounced обновитель прогресса.

    Args:
        widget: Виджет с update_progress() или progress_var
        root: Tk root для безопасности потоков
        delay_ms: Задержка между обновлениями в мс
        adaptive: Включить адаптивный delay
        throttle_ms: Минимальный интервал между обновлениями

    Returns:
        DebouncedProgressUpdater
    """
    updater = DebouncedProgressUpdater(widget, delay_ms, adaptive=adaptive, throttle_ms=throttle_ms)
    if root:
        updater.set_root(root)
    return updater
