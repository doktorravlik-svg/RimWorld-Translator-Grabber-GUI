# logger.py
"""
Модуль логирования для RimWorld Translator.

Предоставляет класс Logger для записи логов в файл и консоль,
с поддержкой разных уровней (INFO, WARN, ERROR, DEBUG).
"""

import time
import traceback


class Logger:
    """
    Логгер для записи событий в файл и оповещения GUI.

    Создает лог-файл с временными метками и поддерживает
    разные уровни важности сообщений.
    """

    def __init__(self, enabled=True, debug=False, path="translator.log", gui_callback=None):
        """
        Инициализация логгера.

        Args:
            enabled: Включить логирование в файл
            debug: Включить режим отладки (DEBUG сообщения)
            path: Путь к лог-файлу
            gui_callback: Callback для отправки сообщений в GUI
        """
        self.enabled = enabled
        self.debug_mode = debug
        self.path = path
        self.gui_callback = gui_callback
        if self.enabled:
            try:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write("\n\n=== New session: " + time.strftime("%Y-%m-%d %H:%M:%S") + " ===\n")
            except Exception:
                pass

    def _write(self, line):
        """Записать строку в лог-файл."""
        if not self.enabled:
            return
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def info(self, msg):
        """Записать информационное сообщение."""
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] INFO: {msg}"
        print(line)
        self._write(line)
        if self.gui_callback:
            self.gui_callback(line)

    def warn(self, msg):
        """Записать предупреждение."""
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARN: {msg}"
        print(line)
        self._write(line)
        if self.gui_callback:
            self.gui_callback(line)

    def error(self, msg):
        """Записать сообщение об ошибке."""
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {msg}"
        print(line)
        self._write(line)

    def debug(self, msg):
        """Записать отладочное сообщение (только при включенном debug)."""
        if not self.debug_mode:
            return
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DEBUG: {msg}"
        print(line)
        self._write(line)

    def exception(self, exc):
        """Записать информацию об исключении с traceback."""
        tb = traceback.format_exc()
        self.error("Exception: " + str(exc))
        self._write(tb)
