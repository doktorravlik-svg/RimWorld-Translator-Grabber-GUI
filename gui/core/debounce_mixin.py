"""
DebounceMixin - миксин для устранения дребезга (debounce) в GUI.

Используется для отложенного выполнения действий при быстром повторении событий
(например, ввод текста в поле поиска).

Пример использования:
    class MyTab(ttk.Frame, DebounceMixin):
        def __init__(self):
            super().__init__()
            self._init_debounce('search')  # Инициализация таймера

        def on_search_change(self, event=None):
            self.debounce('search', 300, self._apply_search)  # Выполнит через 300мс
"""


class DebounceMixin:
    """Миксин для debounce операций в tkinter/ttkbootstrap виджетах."""

    def _init_debounce(self, name: str) -> None:
        """
        Инициализирует debounce таймер с именем.

        Args:
            name: Имя таймера (используется как ключ в словаре)
        """
        if not hasattr(self, '_debounce_timers'):
            self._debounce_timers = {}
        self._debounce_timers[name] = None

    def debounce(self, name: str, delay_ms: int, callback) -> None:
        """
        Выполняет callback через указанное время, отменяя предыдущий таймер.

        Args:
            name: Имя таймера (должно быть инициализировано через _init_debounce)
            delay_ms: Задержка в миллисекундах
            callback: Функция для вызова
        """
        if not hasattr(self, '_debounce_timers'):
            self._debounce_timers = {}

        # Отменяем предыдущий таймер
        timer_id = self._debounce_timers.get(name)
        if timer_id is not None:
            try:
                self.after_cancel(timer_id)
            except Exception:
                pass  # Таймер уже выполнен или отменён

        # Устанавливаем новый таймер
        self._debounce_timers[name] = self.after(delay_ms, callback)

    def cancel_debounce(self, name: str) -> None:
        """
        Отменяет debounce таймер по имени.

        Args:
            name: Имя таймера
        """
        if hasattr(self, '_debounce_timers'):
            timer_id = self._debounce_timers.get(name)
            if timer_id is not None:
                try:
                    self.after_cancel(timer_id)
                except Exception:
                    pass
                self._debounce_timers[name] = None

    def cancel_all_debounce(self) -> None:
        """Отменяет все debounce таймеры."""
        if hasattr(self, '_debounce_timers'):
            for name in list(self._debounce_timers.keys()):
                self.cancel_debounce(name)
