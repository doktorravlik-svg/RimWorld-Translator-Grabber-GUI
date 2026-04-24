# gui/components/statusbar.py
"""
Компактная панель статуса с Floodgauge, Toast и статистикой.
Переработанная версия без дублирования элементов.
"""

import time
import tkinter as tk

import ttkbootstrap as ttk
from gui.gui_i18n import tr
from gui.styling.icon_manager import HAS_ICONS, get_status_bar_icons


class StatusBar(ttk.Frame):
    """Компактная панель статуса: Floodgauge + статистика + Toast"""

    def __init__(self, parent):
        super().__init__(parent, padding=(2, 0))  # Уменьшил padding

        # Тултипы через ttkbootstrap.ToolTip (set_tooltip) — хранятся для возможного доступа
        self._tooltips: list = []

        # Иконки
        self.status_icons = get_status_bar_icons() if HAS_ICONS else {}
        self._is_dark_theme = self._check_dark_theme()

        # === СТРОКА 1: Floodgauge прогресс-бар ===
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
        self.mods_label = self._stat(stats, "Модов: 0", "#3b82f6")
        self.mods_label.pack(side="left", padx=3)
        self.set_tooltip(self.mods_label, tr("tooltip_mods", "Количество обработанных модов"))

        self.translated_label = self._stat(stats, "Переведено: 0", "#22c55e")
        self.translated_label.pack(side="left", padx=3)
        self.set_tooltip(
            self.translated_label, tr("tooltip_translated", "Количество переведённых записей")
        )

        self.errors_label = self._stat(stats, "Ошибок: 0", "#ef4444")
        self.errors_label.pack(side="left", padx=3)
        self.set_tooltip(
            self.errors_label, tr("tooltip_errors", "Количество ошибок при последней операции")
        )

        self.warnings_label = self._stat(stats, "Предупреждений: 0", "#f59e0b")
        self.warnings_label.pack(side="left", padx=3)
        self.set_tooltip(
            self.warnings_label,
            tr("tooltip_warnings", "Количество предупреждений при последней операции"),
        )

        # Последнее действие
        # ✅ ИСПОЛЬЗУЕМ цвет, подходящий для текущей темы (серый для светлой, светло-серый для темной)
        is_dark = self._check_dark_theme()
        last_action_color = "#aaaaaa" if is_dark else "gray"

        self.last_action_label = ttk.Label(
            stats,
            text=tr("last_action_none", "Последнее: -"),
            foreground=last_action_color,
            font=("Segoe UI", 8),
        )
        self.last_action_label.pack(side="right", padx=4)

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
        return ttk.Label(parent, text=text, foreground=fg, font=("Segoe UI", 8))

    # ttkbootstrap ToolTip используется через set_tooltip — ручные обработчики <Enter>/<Leave> больше не нужны

    def _check_dark_theme(self) -> bool:
        """Проверяет тёмную тему."""
        try:
            from config.config_manager import get_config_manager
            from gui.styling.theme_manager import TTKBOOTSTRAP_THEMES

            cfg = get_config_manager().get_all()
            bs = TTKBOOTSTRAP_THEMES.get(cfg.get("theme", "light"), "cosmo")
            return bs in ("darkly", "cyborg", "superhero", "solar")
        except Exception:
            return False

    # ── Статус ──────────────────────────────────────────────
    def set_status(self, message: str):
        self.status_label.config(text=message)

    # ── Статистика с throttle ───────────────────────────────
    def update_stats(self, **kwargs):
        """Накапливает данные и обновляет UI с задержкой."""
        self._stats_buffer.update(kwargs)  # Сохраняем все пришедшие ключи

        now = time.time()
        if now - self._last_update < (self._throttle_interval / 1000):
            if not self._throttle_timer:
                self._throttle_timer = self.after(
                    self._throttle_interval, self._flush_pending_update
                )
            return

        self._flush_pending_update()

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
            self.mods_label.config(text=f"Модов: {self.stats['mods']}", foreground="#3b82f6")
        if "translated" in kwargs:
            self.stats["translated"] = kwargs["translated"]
            c = "#22c55e" if self.stats["translated"] > 0 else "gray"
            self.translated_label.config(
                text=f"Переведено: {self.stats['translated']}", foreground=c
            )
        if "errors" in kwargs:
            self.stats["errors"] = kwargs["errors"]
            c = "#ef4444" if self.stats["errors"] > 0 else "gray"
            self.errors_label.config(text=f"Ошибок: {self.stats['errors']}", foreground=c)
        if "warnings" in kwargs:
            self.stats["warnings"] = kwargs["warnings"]
            c = "#f59e0b" if self.stats["warnings"] > 0 else "gray"
            self.warnings_label.config(
                text=f"Предупреждений: {self.stats['warnings']}", foreground=c
            )
        if "last_action" in kwargs:
            self.stats["last_action"] = kwargs["last_action"]
            self.last_action_label.config(text=f"Последнее: {self.stats['last_action']}")

    def reset_stats(self):
        self.stats = {"mods": 0, "translated": 0, "errors": 0, "warnings": 0, "last_action": "-"}
        self.mods_label.config(text="Модов: 0", foreground="#3b82f6")
        self.translated_label.config(text="Переведено: 0", foreground="gray")
        self.errors_label.config(text="Ошибок: 0", foreground="gray")
        self.warnings_label.config(text="Предупреждений: 0", foreground="gray")
        self.last_action_label.config(text=tr("last_action_none", "Последнее: -"))

    # ── Прогресс ────────────────────────────────────────────
    def start_progress(self, text: str = None):
        self.progress_bar["value"] = 0
        if text:
            self._progress_text.set(text)
        else:
            self._progress_text.set("")
            self.progress_bar.mode = "indeterminate"
        self.progress_bar.start(20)

    def stop_progress(self):
        self.progress_bar.stop()
        self.progress_bar["value"] = 0
        self.progress_bar.mode = "determinate"
        self._progress_text.set("")

    def set_progress(self, value: float, text: str = None):
        safe_value = max(0, min(100, value))
        self.progress_bar["value"] = safe_value
        self._progress_text.set(text if text else f"{safe_value:.1f}%")

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
        """Показать всплывающее уведомление через ttkbootstrap ToastNotification"""
        try:
            from ttkbootstrap.widgets import ToastNotification

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
        except ImportError:
            # Fallback: если ttkbootstrap.toast недоступен, логируем
            if hasattr(self, "_log_callback"):
                self._log_callback(f"[TOAST {toast_type.upper()}] {message}")

    # ── Тултипы ──────────────────────────────────
    def set_tooltip(self, widget, text: str):
        """Установить тултип для виджета через ttkbootstrap.ToolTip"""
        try:
            from ttkbootstrap.widgets import ToolTip

            tooltip = ToolTip(widget, text=text)
            self._tooltips.append((widget, tooltip))
        except ImportError:
            pass  # Тултипы недоступны — тихое игнорирование
