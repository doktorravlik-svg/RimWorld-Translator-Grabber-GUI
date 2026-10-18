# gui/components/performance_monitor.py
"""
Монитор системных ресурсов для статус-бара.

Компактные индикаторы загрузки CPU, RAM и потоков приложения.
Использует psutil (если установлен) и полностью безопасен при его отсутствии.

Особенности:
- Неблокирующий опрос (cpu_percent без interval) — UI не подтормаживает
- Автоматическая остановка при уничтожении виджета (без TclError в after)
- Потокобезопасное обновление через after()
- Цветовая индикация нагрузки (норма/предупреждение/критично)
"""

import tkinter as tk

import ttkbootstrap as ttk

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:  # pragma: no cover - опциональная зависимость
    psutil = None
    HAS_PSUTIL = False

# Пороги нагрузки (в процентах)
THRESHOLD_WARNING = 70
THRESHOLD_CRITICAL = 90


class PerformanceMonitor(ttk.Frame):
    """
    Компактный виджет мониторинга ресурсов для статус-бара.

    Отображает: CPU%  RAM%  Потоки

    Args:
        parent: Родительский виджет
        interval_ms: Период опроса в миллисекундах (по умолчанию 2000)
        show_threads: Показывать счётчик потоков приложения
    """

    def __init__(self, parent, interval_ms: int = 2000, show_threads: bool = True):
        super().__init__(parent)

        self.interval_ms = max(500, int(interval_ms))
        self.show_threads = show_threads
        self._job_id: str | None = None
        self._destroyed = False

        # Тултип общий для всех индикаторов
        self._tooltip = "Загрузка CPU / ОЗУ / потоки приложения"

        self._build_ui()

        if HAS_PSUTIL:
            # Первичный опрос CPU: инициализирует внутренний счётчик psutil
            try:
                psutil.cpu_percent(interval=None)
            except Exception:
                pass

        self.start()

    # ── UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        font = ("Segoe UI", 8)

        self.cpu_label = ttk.Label(self, text="CPU —", font=font, foreground="gray")
        self.cpu_label.pack(side="left", padx=(4, 0))
        self.set_tooltip(self.cpu_label, self._tooltip)

        self.cpu_bar = ttk.Progressbar(
            self,
            length=48,
            mode="determinate",
            maximum=100,
            bootstyle="success",
        )
        self.cpu_bar.pack(side="left", padx=(2, 4))

        self.ram_label = ttk.Label(self, text="RAM —", font=font, foreground="gray")
        self.ram_label.pack(side="left")
        self.set_tooltip(self.ram_label, self._tooltip)

        self.ram_bar = ttk.Progressbar(
            self,
            length=48,
            mode="determinate",
            maximum=100,
            bootstyle="info",
        )
        self.ram_bar.pack(side="left", padx=(2, 4))

        if self.show_threads:
            self.threads_label = ttk.Label(self, text="⟳ 0", font=font, foreground="gray")
            self.threads_label.pack(side="left")
            self.set_tooltip(self.threads_label, "Количество активных потоков приложения")

        # Привязка очистки к уничтожению виджета
        self.bind("<Destroy>", self._on_destroy, add="+")

    def set_tooltip(self, widget, text: str):
        """Установить тултип (тихо игнорируется если ttkbootstrap ToolTip недоступен)."""
        try:
            from ttkbootstrap.widgets import ToolTip

            ToolTip(widget, text=text)
        except Exception:
            pass

    # ── Жизненный цикл ────────────────────────────────────────────
    def start(self):
        """Запустить периодический опрос (безопасно повторный вызов)."""
        if self._job_id or self._destroyed:
            return
        self._job_id = self.after(self.interval_ms, self._tick)

    def stop(self):
        """Остановить опрос."""
        if self._job_id:
            try:
                self.after_cancel(self._job_id)
            except Exception:
                pass
            self._job_id = None

    def _on_destroy(self, event=None):
        """Гарантированно отменить таймер при уничтожении виджета."""
        if event is not None and event.widget is not self:
            return
        self._destroyed = True
        self.stop()

    # ── Логика ────────────────────────────────────────────────────
    def _tick(self):
        """Один такт опроса (вызывается из главного потока Tk)."""
        if self._destroyed:
            return
        self._job_id = None

        try:
            if not self.winfo_exists():
                self._destroyed = True
                return
        except Exception:
            self._destroyed = True
            return

        self._sample()

        if not self._destroyed:
            self._job_id = self.after(self.interval_ms, self._tick)

    def _sample(self):
        """Снять показания и обновить UI."""
        if not HAS_PSUTIL:
            self.cpu_label.config(text="CPU н/д")
            return

        try:
            cpu = psutil.cpu_percent(interval=None)
            self._set_cpu(cpu)

            mem = psutil.virtual_memory()
            self._set_ram(mem.percent)

            if self.show_threads:
                proc = self._process()
                if proc is not None:
                    count = proc.num_threads()
                    self.threads_label.config(
                        text=f"⟳ {count}",
                        foreground="gray" if count < 40 else "orange",
                    )
        except Exception:
            # psutil может быть временно недоступен — молча пропускаем такт
            pass

    def _set_cpu(self, value: float):
        """Обновить индикатор CPU."""
        value = max(0.0, min(100.0, float(value)))
        self.cpu_bar.config(value=value, bootstyle=self._bootstyle(value))
        self.cpu_label.config(text=f"CPU {value:.0f}%")

    def _set_ram(self, value: float):
        """Обновить индикатор RAM."""
        value = max(0.0, min(100.0, float(value)))
        self.ram_bar.config(value=value)
        self.ram_label.config(text=f"RAM {value:.0f}%")

    @staticmethod
    def _bootstyle(value: float) -> str:
        """Выбрать bootstyle в зависимости от нагрузки."""
        if value >= THRESHOLD_CRITICAL:
            return "danger"
        if value >= THRESHOLD_WARNING:
            return "warning"
        return "success"

    def _process(self):
        """Получить (и закэшировать) объект текущего процесса."""
        if not hasattr(self, "_proc") or self._proc is None:
            try:
                self._proc = psutil.Process()
            except Exception:
                self._proc = False  # маркер "недоступно"
        return self._proc if self._proc else None
