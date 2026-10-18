# gui/components/statusbar.py
"""
Компактная панель статуса с Floodgauge, Toast и статистикой.
Переработанная версия без дублирования элементов.
"""

import threading
import time
import tkinter as tk

import ttkbootstrap as ttk
from gui.gui_i18n import tr
from gui.styling.icon_manager import HAS_ICONS, get_status_bar_icons
from gui.styling.theme_manager import is_dark_theme
from gui.components.performance_monitor import HAS_PSUTIL, PerformanceMonitor

# Интервал обновления монитора ресурсов (мс) — единый источник: gui/constants.py
from gui.constants import PERFORMANCE_MONITOR_INTERVAL

# Локальные импорты с fallback
try:
    from ttkbootstrap.widgets import ToastNotification
except ImportError:
    ToastNotification = None

try:
    from ttkbootstrap.widgets import ToolTip
except ImportError:
    ToolTip = None


class StatusBar(ttk.Frame):
    """Компактная панель статуса: Floodgauge + статистика + Toast"""

    def __init__(self, parent):
        super().__init__(parent, padding=(2, 0))  # Уменьшил padding

        # Тултипы через ttkbootstrap.ToolTip (set_tooltip) — хранятся для возможного доступа
        self._tooltips: list = []

        # Иконки
        self.status_icons = get_status_bar_icons() if HAS_ICONS else {}
        self._is_dark_theme = self._check_dark_theme()

        # === СТРОКА 1: Progressbar прогресс-бар ===
        self._progress_text = tk.StringVar(value="")
        self.progress_bar = ttk.Floodgauge(
            self,
            mode="determinate",
            maximum=100,
            textvariable=self._progress_text,
            font=("Segoe UI", 8, "bold"),  # Уменьшил шрифт
            thickness=16,  # Уменьшил толщину
        )
        self.progress_bar.pack(fill="x", pady=(0, 0))
        self.progress_bar["value"] = 0

        # === СТРОКА 2: Статистика в одну строку ===
        stats = ttk.Frame(self)
        stats.pack(fill="x")

        # Статус
        self.status_label = ttk.Label(stats, text=tr("status_ready", "Готов"), font=("Segoe UI", 7))
        self.status_label.pack(side="left", padx=(0, 5))

        # Счётчики с тултипами (через ttkbootstrap Tooltip)
        self.mods_label = self._stat(stats, tr("status_mods_count", "Модов: 0"), "primary")
        self.mods_label.pack(side="left", padx=3)
        self.set_tooltip(self.mods_label, tr("tooltip_mods", "Количество обработанных модов"))

        self.translated_label = self._stat(stats, tr("status_translated_count", "Переведено: 0"), "success")
        self.translated_label.pack(side="left", padx=3)
        self.set_tooltip(
            self.translated_label, tr("tooltip_translated", "Количество переведённых записей")
        )

        self.errors_label = self._stat(stats, tr("status_errors_count", "Ошибок: 0"), "danger")
        self.errors_label.pack(side="left", padx=3)
        self.set_tooltip(
            self.errors_label, tr("tooltip_errors", "Количество ошибок при последней операции")
        )

        self.warnings_label = self._stat(stats, tr("status_warnings_count", "Предупреждений: 0"), "warning")
        self.warnings_label.pack(side="left", padx=3)
        self.set_tooltip(
            self.warnings_label,
            tr("tooltip_warnings", "Количество предупреждений при последней операции"),
        )

        # Последнее действие — используем muted (secondary) bootstyle
        self.last_action_label = ttk.Label(
            stats,
            text=tr("last_action_none", "Последнее: -"),
            bootstyle="secondary",
            font=("Segoe UI", 8),
        )
        self.last_action_label.pack(side="right", padx=4)

        # ✅ НОВОЕ (2026): Монитор системных ресурсов (CPU / RAM / потоки)
        # Показывается только при наличии psutil и если включено в конфиге
        self.performance_monitor: PerformanceMonitor | None = None
        self._monitor_config = self._load_monitor_config()
        self._init_performance_monitor(stats)

        # Состояние
        self._last_update = 0.0
        self._throttle_timer: str | None = None
        self._throttle_interval = 500  # В миллисекундах для after()
        # Состояние статистики и буфер для троттлинга
        self.stats = {"mods": 0, "translated": 0, "errors": 0, "warnings": 0, "last_action": "-"}
        self._stats_buffer: dict[str, any] = {}  # Буфер для накопления данных

    @staticmethod
    def _stat(parent: ttk.Frame, text: str, fg: str) -> ttk.Label:
        """Создать метку статистики."""
        return ttk.Label(parent, text=text, bootstyle=fg, font=("Segoe UI", 8))

    # ttkbootstrap ToolTip используется через set_tooltip — ручные обработчики <Enter>/<Leave> больше не нужны

    def _check_dark_theme(self) -> bool:
        """Проверяет тёмную тему через единый реестр theme_manager."""
        try:
            from config.config_manager import get_config_manager

            theme_key = get_config_manager().get("theme", "light")
            return is_dark_theme(theme_key)
        except Exception:
            return False

    # ── Монитор ресурсов ─────────────────────────────────────────
    def _load_monitor_config(self) -> dict:
        """Загрузить настройки монитора из конфига (с безопасными дефолтами)."""
        try:
            from config.config_manager import get_config_manager

            cfg = get_config_manager()
            interval = int(
                cfg.get("performance_monitor_interval", PERFORMANCE_MONITOR_INTERVAL)
            )
            return {
                "enabled": bool(cfg.get("show_performance_monitor", True)),
                "interval": max(500, interval),
            }
        except Exception:
            return {"enabled": True, "interval": PERFORMANCE_MONITOR_INTERVAL}

    def _init_performance_monitor(self, parent):
        """Создать (и при необходимости показать) монитор ресурсов."""
        if not HAS_PSUTIL:
            return

        self._monitor_parent = parent
        self.performance_monitor = PerformanceMonitor(
            parent, interval_ms=self._monitor_config.get("interval")
        )

        if self._monitor_config.get("enabled", True):
            self.performance_monitor.pack(side="right", padx=(2, 6))
        else:
            self.performance_monitor.stop()

    def toggle_performance_monitor(self) -> bool:
        """
        Переключить отображение монитора ресурсов.

        Returns:
            Новое состояние (True = показан) или False если недоступен
        """
        if not self.performance_monitor:
            return False

        try:
            enabled = not bool(self.performance_monitor.winfo_ismapped())
            if enabled:
                self.performance_monitor.pack(side="right", padx=(2, 6))
                self.performance_monitor.start()
            else:
                self.performance_monitor.pack_forget()
                self.performance_monitor.stop()
        except Exception:
            return False

        try:
            from config.config_manager import get_config_manager

            get_config_manager().set("show_performance_monitor", enabled, save=False)
        except Exception:
            pass
        return enabled

    # ── Статус ──────────────────────────────────────────────
    def _on_ui(self, fn):
        """Выполнить функцию в главном UI-потоке (безопасно из любого потока)."""
        if threading.current_thread() is threading.main_thread():
            fn()
            return
        try:
            self.after(0, fn)
        except Exception:
            pass  # Виджет мог быть уничтожен

    def set_status(self, message: str):
        """Устанавливает текст статусной строки (безопасно для потоков)."""
        def _apply():
            try:
                # Проверяем, что виджет существует и не был уничтожен
                if self.status_label.winfo_exists():
                    self.status_label.config(text=message)
            except Exception:
                pass  # Виджет мог быть уничтожен

        self._on_ui(_apply)

    # ── Статистика с throttle ───────────────────────────────
    def update_stats(self, **kwargs):
        """Накапливает данные и обновляет UI с задержкой (безопасно для потоков)."""

        def _apply():
            self._stats_buffer.update(kwargs)  # Сохраняем все пришедшие ключи

            now = time.time()
            if now - self._last_update < (self._throttle_interval / 1000):
                if not self._throttle_timer:
                    self._throttle_timer = self.after(
                        self._throttle_interval, self._flush_pending_update
                    )
                return

            self._flush_pending_update()

        self._on_ui(_apply)

    def _flush_pending_update(self):
        if self._throttle_timer:
            self.after_cancel(self._throttle_timer)
            self._throttle_timer = None

        self._last_update = time.time()
        if self._stats_buffer:
            self._apply_stats(self._stats_buffer)
            self._stats_buffer.clear()  # Очищаем после применения

    def _apply_stats(self, kwargs: dict):
        if "mods" in kwargs:
            self.stats["mods"] = kwargs["mods"]
            self.mods_label.config(text=f"Модов: {self.stats['mods']}", bootstyle="primary")
        if "translated" in kwargs:
            self.stats["translated"] = kwargs["translated"]
            bootstyle = "success" if self.stats["translated"] > 0 else "secondary"
            self.translated_label.config(
                text=f"Переведено: {self.stats['translated']}", bootstyle=bootstyle
            )
        if "errors" in kwargs:
            self.stats["errors"] = kwargs["errors"]
            bootstyle = "danger" if self.stats["errors"] > 0 else "secondary"
            self.errors_label.config(text=f"Ошибок: {self.stats['errors']}", bootstyle=bootstyle)
        if "warnings" in kwargs:
            self.stats["warnings"] = kwargs["warnings"]
            bootstyle = "warning" if self.stats["warnings"] > 0 else "secondary"
            self.warnings_label.config(
                text=f"Предупреждений: {self.stats['warnings']}", bootstyle=bootstyle
            )
        if "last_action" in kwargs:
            self.stats["last_action"] = kwargs["last_action"]
            self.last_action_label.config(text=f"Последнее: {self.stats['last_action']}")

    def reset_stats(self):
        self.stats = {"mods": 0, "translated": 0, "errors": 0, "warnings": 0, "last_action": "-"}
        self.mods_label.config(text=tr("status_mods_count", "Модов: 0"), bootstyle="primary")
        self.translated_label.config(text=tr("status_translated_count", "Переведено: 0"), bootstyle="secondary")
        self.errors_label.config(text=tr("status_errors_count", "Ошибок: 0"), bootstyle="secondary")
        self.warnings_label.config(text=tr("status_warnings_count", "Предупреждений: 0"), bootstyle="secondary")
        self.last_action_label.config(text=tr("last_action_none", "Последнее: -"))

    # ── Прогресс ────────────────────────────────────────────
    def start_progress(self, text: str = None):
        def _apply():
            self.progress_bar["value"] = 0
            if text:
                # С текстом — детерминированный прогресс (0% до set_progress)
                self._progress_text.set(text)
                self.progress_bar.configure(mode="determinate")
                self.progress_bar.stop()
            else:
                # Без текста — неопределённая анимация (спиннер)
                self._progress_text.set("")
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start(20)

        self._on_ui(_apply)

    def stop_progress(self):
        def _apply():
            self.progress_bar.stop()
            self.progress_bar["value"] = 0
            self.progress_bar.configure(mode="determinate")
            self._progress_text.set("")

        self._on_ui(_apply)

    def set_progress(self, value: float, text: str = None):
        def _apply():
            # Устанавливаем конкретное значение — режим должен быть determinate
            if self.progress_bar["mode"] != "determinate":
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
            safe_value = max(0, min(100, value))
            self.progress_bar["value"] = safe_value
            self._progress_text.set(text if text else f"{safe_value:.1f}%")

        self._on_ui(_apply)

    def update_detailed_progress(self, current: int, total: int):
        """Обновляет прогресс на основе количества обработанных элементов."""
        if total <= 0:
            return
        percentage = (current / total) * 100
        detail_text = f"{percentage:.1f}% ({current} / {total})"
        self.set_progress(percentage, text=detail_text)

    # ── Toast уведомления ──────────────────────────────────
    def show_toast(
        self, message: str, toast_type: str = "info", duration: int = 3000, group_by: str = None
    ):
        """Показать всплывающее уведомление через ttkbootstrap ToastNotification.
        
        Безопасно вызывается из любого потока — автоматически перенаправляется
        в главный UI-поток через .after().
        """
        # Если вызов из фонового потока — перенаправляем в главный
        if threading.current_thread() != threading.main_thread():
            self.after(0, self.show_toast, message, toast_type, duration, group_by)
            return
        
        if ToastNotification is None:
            # Fallback: логируем если ToastNotification недоступен
            self._log_message(f"[TOAST {toast_type.upper()}] {message}")
            return
            
        try:
            # Маппинг типов на bootstyle
            style_map = {
                "info": "info",
                "success": "success",
                "warning": "warning",
                "error": "danger",
            }

            # Эмодзи для заголовка
            icons = {
                "info": "ℹ️",
                "success": "✅",
                "warning": "⚠️",
                "error": "❌",
            }

            toast = ToastNotification(
                title=f"{icons.get(toast_type, 'ℹ️')} Уведомление",
                message=message,
                duration=duration,
                bootstyle=style_map.get(toast_type, "info"),
                position=(20, 20, "ne"),  # (x, y, corner) — правый верхний угол
            )
            toast.show_toast()
        except Exception as e:
            self._log_message(f"[TOAST ERROR] {e}: {message}")
    
    def _log_message(self, message: str):
        """Вспомогательный метод для логирования."""
        if hasattr(self, "_log_callback") and self._log_callback:
            self._log_callback(message)
        else:
            print(message)  # Fallback на случай, если коллбек не задан

    # ── Тултипы ──────────────────────────────────
    def set_tooltip(self, widget, text: str):
        """Установить тултип для виджета через ttkbootstrap.ToolTip"""
        if ToolTip is None:
            return  # Тултипы недоступны — тихое игнорирование
        
        try:
            tooltip = ToolTip(widget, text=text)
            self._tooltips.append((widget, tooltip))
        except Exception:
            pass  # Тултипы недоступны — тихое игнорирование
