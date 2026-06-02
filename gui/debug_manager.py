# gui/debug_manager.py
"""
Централизованный менеджер debug режима для GUI.

Обеспечивает:
- Включение/выключение debug режима
- Логирование всех действий пользователя
- Визуальные индикаторы (заголовок окна)
- Сохранение настроек в конфигурацию
- Интеграцию с DebugLogger

Пример использования:
    debug_mgr = DebugManager(root, config, log_callback, save_callback)
    debug_mgr.toggle()  # Включить/выключить
    debug_mgr.log_event("Перевод запущен", details="English -> Russian")
"""

from __future__ import annotations

import sys
import time
import threading
from collections.abc import Callable
from datetime import datetime
from typing import Any

import ttkbootstrap as ttk
from config.debug_config import DebugConfig
from utils.debug_logger import DebugLogger, get_debug_logger


class DebugManager:
    """
    Менеджер debug режима.

    Управляет состоянием debug режима, логированием действий
    и визуальными индикаторами.

    Args:
        root: Tkinter root окно
        config: Словарь конфигурации приложения
        log_callback: Функция для добавления сообщений в UI лог
        save_callback: Функция для сохранения конфигурации
    """

    def __init__(
        self,
        root: ttk.Window,
        config: dict[str, Any],
        log_callback: Callable[[str], None],
        save_callback: Callable[[], None],
    ) -> None:
        self.root = root
        self.config = config
        self.log_callback = log_callback
        self.save_callback = save_callback

        # Загружаем настройки debug из конфига
        debug_data = config.get("debug", {})
        self.debug_config = DebugConfig.from_dict(debug_data) if debug_data else DebugConfig()

        # Создаём logger
        self.debug_logger: DebugLogger | None = None
        if self.debug_config.enabled:
            self.debug_logger = get_debug_logger(self.debug_config)

        # Таймеры операций: {operation_name: start_time}
        self._timers: dict[str, float] = {}

        # Счётчики статистики
        self._stats: dict[str, int] = {
            "mods_processed": 0,
            "files_read": 0,
            "files_written": 0,
            "translations_done": 0,
            "errors_count": 0,
            "warnings_count": 0,
        }

        # Активные воркеры
        self._active_workers: dict[str, dict[str, Any]] = {}

    @property
    def is_enabled(self) -> bool:
        """Включён ли debug режим"""
        return self.debug_config.enabled

    def toggle(self) -> bool:
        """
        Переключить debug режим.

        Returns:
            Новое состояние (True = включён)
        """
        self.debug_config.enabled = not self.debug_config.enabled
        self.config["debug"] = self.debug_config.to_dict()

        if self.debug_config.enabled:
            self._enable_debug()
        else:
            self._disable_debug()

        # Обновляем UI и сохраняем
        self._update_window_title()
        self.save_callback()

        return self.debug_config.enabled

    def enable(self) -> None:
        """Включить debug режим"""
        if not self.debug_config.enabled:
            self.toggle()

    def disable(self) -> None:
        """Выключить debug режим"""
        if self.debug_config.enabled:
            self.toggle()

    def log_action(self, message: str, category: str = "general") -> None:
        """
        Записать действие в логи (только в debug.log, не в UI).

        Args:
            message: Сообщение для логирования
            category: Категория действия (например, "gui", "translation", "config")
        """
        # Всегда пишем в UI лог через log_callback (но НЕ здесь, чтобы избежать дублирования)
        # UI лог пишется через gui.py:log() -> log_panel.log()
        
        # Если debug включён - пишем в debug.log с категорией
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(f"[{category.upper()}] {message}")

    def log_event(self, event_type: str, widget: str, details: str = "") -> None:
        """
        Записать событие GUI.

        Args:
            event_type: Тип события (например, "button_click")
            widget: Виджет, вызвавший событие
            details: Дополнительные детали
        """
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.gui_event(event_type, widget, details)

    def log_app_start(self) -> None:
        """Записать запуск приложения"""
        if self.debug_config.enabled and self.debug_logger:
            import os

            self.debug_logger.info("=" * 70)
            self.debug_logger.info("ПРИЛОЖЕНИЕ ЗАПУЩЕНО")
            self.debug_logger.info("Версия: RimWorld Translator Grabber V2+")
            self.debug_logger.info(f"Python: {sys.version}")
            self.debug_logger.info(f"Платформа: {sys.platform}")
            self.debug_logger.info(f"Кодировка: {sys.getdefaultencoding()}")
            self.debug_logger.info(f"Рабочая директория: {os.getcwd()}")
            self.debug_logger.info(f"Путь к gui_config: {self.config.get('_config_path', 'default')}")

            # Версии ключевых зависимостей
            self._log_dependency_versions()

            # Статус i18n
            self._log_i18n_status()

            # Настройки из конфига
            self.debug_logger.info(f"Тема: {self.config.get('theme', 'light')}")
            self.debug_logger.info(f"Язык интерфейса: {self.config.get('ui_language', 'ru')}")
            self.debug_logger.info(f"Исходный язык: {self.config.get('source_language', 'English')}")
            self.debug_logger.info(f"Целевой язык: {self.config.get('target_language', 'Russian')}")
            self.debug_logger.info(f"Папка модов: {self.config.get('mods_folder', 'не задана')}")
            self.debug_logger.info("=" * 70)

    def _log_dependency_versions(self) -> None:
        """Записать версии ключевых зависимостей"""
        if not self.debug_logger:
            return
        deps = [
            ("ttkbootstrap", "ttkbootstrap"),
            ("loguru", "loguru"),
            ("lxml", "lxml"),
            ("deep_translator", "deep_translator"),
            ("translators", "translators"),
        ]
        for name, module in deps:
            try:
                mod = __import__(module)
                version = getattr(mod, "__version__", "unknown")
                self.debug_logger.info(f"  {name}: {version}")
            except ImportError:
                self.debug_logger.warning(f"  {name}: НЕ УСТАНОВЛЕН")

    def _log_i18n_status(self) -> None:
        """Записать статус системы локализации"""
        if not self.debug_logger:
            return
        try:
            from gui.gui_i18n import i18n
            available = i18n.get_available_languages()
            current = i18n.current_language
            total_keys = len(i18n.translations.get(current, {}))
            self.debug_logger.info(f"i18n: текущий={current}, доступно={available}, ключей={total_keys}")
        except Exception as e:
            self.debug_logger.warning(f"i18n: ошибка получения статуса: {e}")

    def log_app_exit(self) -> None:
        """Записать завершение приложения"""
        if self.debug_config.enabled and self.debug_logger:
            # Итоговая статистика
            self._log_final_stats()
            self.debug_logger.info("Приложение завершает работу")

    # ===== Таймеры операций =====

    def timer_start(self, operation: str) -> None:
        """Запустить таймер операции"""
        self._timers[operation] = time.monotonic()
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.debug(f"[TIMER] Старт: {operation}")

    def timer_stop(self, operation: str) -> float | None:
        """
        Остановить таймер и записать длительность.

        Returns:
            Длительность в секундах или None если таймер не найден.
        """
        start = self._timers.pop(operation, None)
        if start is None:
            return None
        duration = time.monotonic() - start
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(f"[TIMER] {operation}: {duration:.2f}с")
        return duration

    # ===== Статистика обработки =====

    def stat_increment(self, counter: str, value: int = 1) -> None:
        """Увеличить счётчик статистики"""
        self._stats[counter] = self._stats.get(counter, 0) + value

    def stat_set(self, counter: str, value: int) -> None:
        """Установить значение счётчика"""
        self._stats[counter] = value

    def stat_get(self, counter: str) -> int:
        """Получить значение счётчика"""
        return self._stats.get(counter, 0)

    def log_stats_summary(self, label: str = "Текущая статистика") -> None:
        """Записать сводку статистики"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(f"[STATS] {label}:")
            for key, value in sorted(self._stats.items()):
                self.debug_logger.info(f"  {key}: {value}")

    def _log_final_stats(self) -> None:
        """Записать итоговую статистику при выходе"""
        if not self.debug_logger:
            return
        self.debug_logger.info("-" * 40)
        self.debug_logger.info("ИТОГОВАЯ СТАТИСТИКА:")
        for key, value in sorted(self._stats.items()):
            self.debug_logger.info(f"  {key}: {value}")
        # Активные воркеры (если есть незавершённые)
        if self._active_workers:
            self.debug_logger.warning(f"  Незавершённых воркеров: {len(self._active_workers)}")
            for name, info in self._active_workers.items():
                self.debug_logger.warning(f"    - {name}: запущен {info.get('start_time', '?')}")

    # ===== Мониторинг памяти =====

    def log_memory_usage(self, label: str = "") -> None:
        """Записать текущее использование памяти процессом"""
        if not self.debug_config.enabled or not self.debug_logger:
            return
        try:
            import psutil
            process = psutil.Process()
            mem = process.memory_info()
            rss_mb = mem.rss / (1024 * 1024)
            vms_mb = mem.vms / (1024 * 1024)
            prefix = f"[{label}] " if label else ""
            self.debug_logger.info(
                f"[MEMORY] {prefix}RSS: {rss_mb:.1f} MB, VMS: {vms_mb:.1f} MB"
            )
        except ImportError:
            # psutil не установлен — пробуем через resource (только Unix)
            try:
                import resource
                usage = resource.getrusage(resource.RUSAGE_SELF)
                self.debug_logger.info(f"[MEMORY] {label} maxrss: {usage.ru_maxrss / 1024:.1f} MB")
            except (ImportError, AttributeError):
                self.debug_logger.debug("[MEMORY] psutil не установлен, мониторинг памяти недоступен")

    # ===== Логирование воркеров =====

    def log_worker_start(self, worker_name: str, worker_type: str, **kwargs: Any) -> None:
        """Записать запуск воркера"""
        info = {
            "type": worker_type,
            "start_time": datetime.now().strftime("%H:%M:%S"),
            "thread": threading.current_thread().name,
        }
        info.update(kwargs)
        self._active_workers[worker_name] = info
        if self.debug_config.enabled and self.debug_logger:
            extra = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            self.debug_logger.info(
                f"[WORKER] Запуск: {worker_name} (тип={worker_type}, поток={info['thread']}"
                f"{', ' + extra if extra else ''})"
            )

    def log_worker_stop(self, worker_name: str, success: bool = True) -> None:
        """Записать завершение воркера"""
        info = self._active_workers.pop(worker_name, {})
        duration_str = ""
        if "start_monotonic" in info:
            dur = time.monotonic() - info["start_monotonic"]
            duration_str = f", длительность: {dur:.2f}с"
        status = "успешно" if success else "с ошибкой"
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(
                f"[WORKER] Стоп: {worker_name} ({status}{duration_str})"
            )

    def log_worker_progress(self, worker_name: str, current: int, total: int, detail: str = "") -> None:
        """Записать прогресс воркера"""
        if self.debug_config.enabled and self.debug_logger:
            pct = (current / total * 100) if total > 0 else 0
            msg = f"[WORKER] {worker_name}: {current}/{total} ({pct:.1f}%)"
            if detail:
                msg += f" — {detail}"
            self.debug_logger.debug(msg)

    # ===== Логирование выбора модов =====

    def log_mods_selection(self, selected: list[str], total_available: int) -> None:
        """Записать выбор модов пользователем"""
        if self.debug_config.enabled and self.debug_logger:
            count = len(selected)
            self.debug_logger.info(
                f"[MODS] Выбрано: {count} из {total_available} доступных модов"
            )
            if count <= 20:
                for mod_name in selected:
                    self.debug_logger.debug(f"  - {mod_name}")
            else:
                for mod_name in selected[:5]:
                    self.debug_logger.debug(f"  - {mod_name}")
                self.debug_logger.debug(f"  ... и ещё {count - 5}")

    # ===== Логирование ошибок парсинга =====

    def log_xml_error(self, file_path: str, error: str, is_warning: bool = False) -> None:
        """Записать ошибку парсинга XML"""
        if self.debug_config.enabled and self.debug_logger:
            level = "WARNING" if is_warning else "ERROR"
            self.debug_logger.debug(f"[XML_{level}] {file_path}: {error}")
            if is_warning:
                self._stats["warnings_count"] = self._stats.get("warnings_count", 0) + 1
            else:
                self._stats["errors_count"] = self._stats.get("errors_count", 0) + 1

    def log_xml_stats(self, files_ok: int, files_failed: int, total_tags: int) -> None:
        """Записать статистику парсинга XML"""
        if self.debug_config.enabled and self.debug_logger:
            total = files_ok + files_failed
            self.debug_logger.info(
                f"[XML_STATS] Файлов: {total} (OK={files_ok}, ошибок={files_failed}), тегов: {total_tags}"
            )

    def log_theme_change(self, old_theme: str, new_theme: str) -> None:
        """Записать изменение темы"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(f"[THEME] Тема изменена: {old_theme} -> {new_theme}")

    def log_language_change(self, old_lang: str, new_lang: str) -> None:
        """Записать изменение языка интерфейса"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(f"[LANGUAGE] Язык интерфейса: {old_lang} -> {new_lang}")

    def log_tab_switch(self, tab_name: str) -> None:
        """Записать переключение вкладки"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.debug(f"[TAB] Переключение на вкладку: {tab_name}")

    def log_translation_start(self, source: str, target: str, mode: str, mods_count: int) -> None:
        """Записать запуск перевода"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(
                f"[TRANSLATION] Запуск: {source} -> {target}, режим: {mode}, модов: {mods_count}"
            )
            self.timer_start("translation")
            self.log_memory_usage("перед переводом")

    def log_translation_complete(
        self, success: bool, duration: float, translated_count: int
    ) -> None:
        """Записать завершение перевода"""
        if self.debug_config.enabled and self.debug_logger:
            status = "УСПЕШНО" if success else "С ОШИБКАМИ"
            self.debug_logger.info(
                f"[TRANSLATION] Завершён: {status}, время: {duration:.1f}с, переведено: {translated_count}"
            )
            self.stat_increment("translations_done", translated_count)
            self.log_memory_usage("после перевода")

    def log_verification_start(self, mods_count: int, checks: list[str]) -> None:
        """Записать запуск верификации"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(
                f"[VERIFICATION] Запуск: модов: {mods_count}, проверки: {', '.join(checks)}"
            )
            self.timer_start("verification")
            self.log_memory_usage("перед верификацией")

    def log_verification_complete(
        self, success: bool, errors: int, warnings: int, total_checked: int
    ) -> None:
        """Записать завершение верификации"""
        if self.debug_config.enabled and self.debug_logger:
            duration = self.timer_stop("verification") or 0
            status = "УСПЕШНО" if success else "С ОШИБКАМИ"
            self.debug_logger.info(
                f"[VERIFICATION] Завершена: {status}, время: {duration:.1f}с, "
                f"проверено: {total_checked}, ошибок: {errors}, предупреждений: {warnings}"
            )
            self.stat_increment("errors_count", errors)
            self.stat_increment("warnings_count", warnings)
            self.log_memory_usage("после верификации")

    def log_file_operation(self, operation: str, path: str, details: str = "") -> None:
        """
        Записать файловую операцию.

        Args:
            operation: Тип операции (например, "open_file")
            path: Путь к файлу/папке
            details: Дополнительные детали
        """
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.file_operation(operation, path, details)

    def log_config_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """
        Записать изменение конфигурации.

        Args:
            key: Ключ конфигурации
            old_value: Старое значение
            new_value: Новое значение
        """
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.config_change(key, old_value, new_value)

    def log_status_change(self, message: str) -> None:
        """
        Записать изменение статуса.

        Args:
            message: Новое сообщение статуса
        """
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.gui_event("status_change", "StatusBar", message)

    def log_progress(self, action: str, value: int | None = None) -> None:
        """
        Записать действие с прогресс-баром.

        Args:
            action: Действие ("start", "stop", "update")
            value: Значение прогресса (0-100)
        """
        if self.debug_config.enabled and self.debug_logger:
            if value is not None:
                self.debug_logger.debug(f"Прогресс: {action} - {value}%")
            else:
                self.debug_logger.debug(f"Прогресс-бар: {action}")

    def log_error(self, message: str, exc: Exception | None = None) -> None:
        """
        Записать ошибку.

        Args:
            message: Сообщение об ошибке
            exc: Исключение (опционально)
        """
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.error(message, exc_info=exc is not None)
            if exc:
                self.debug_logger.exception(message, exc)

    def get_log_content(self, lines: int = 100) -> str:
        """
        Получить последние N строк лога.

        Args:
            lines: Количество строк для получения

        Returns:
            Содержимое лога
        """
        if self.debug_logger:
            return self.debug_logger.get_log_content(lines)
        return "Debug логгер не инициализирован"

    def clear_log(self) -> None:
        """Очистить лог-файл"""
        if self.debug_logger:
            self.debug_logger.clear_log()

    def _enable_debug(self) -> None:
        """Включить debug режим"""
        # Пересоздаём logger с новыми настройками
        self.debug_logger = get_debug_logger(self.debug_config)
        self.debug_logger.info("=" * 60)
        self.debug_logger.info("Debug-режим ВКЛЮЧЁН")
        self.debug_logger.info(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.debug_logger.info(f"Python: {sys.version}")
        self.debug_logger.info(f"Платформа: {sys.platform}")
        self.debug_logger.info("=" * 60)

    def _disable_debug(self) -> None:
        """Выключить debug режим"""
        if self.debug_logger:
            self.debug_logger.info("Debug-режим ВЫКЛЮЧЕН")

    def _update_window_title(self) -> None:
        """Обновить заголовок окна с пометкой [DEBUG]"""
        try:
            from gui.gui_i18n import i18n

            title = i18n.tr("gui_root_title", "RimWorld Translator Grabber V2+")
            if self.debug_config.enabled:
                title += " [🔧 DEBUG]"
            self.root.title(title)
        except Exception:
            pass

    def get_status_text(self) -> str:
        """
        Получить текст статуса debug режима.

        Returns:
            Текст для отображения в статус-баре
        """
        if self.debug_config.enabled:
            return "🔧 DEBUG активен"
        return ""
