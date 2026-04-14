# workers/base_worker.py
"""
Базовый класс для асинхронных worker-ов.

Этот модуль предоставляет базовый класс BaseWorker с поддержкой:
- Запуска/остановки в отдельном потоке
- Callback-ов для прогресса, результата и ошибок
- Потокобезопасной передачи данных через queue.Queue
- ✅ ИСПРАВЛЕНО: Безопасные callback-и для Tkinter через root.after()
"""

import queue
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class BaseWorker(ABC):
    """
    Базовый класс для асинхронных worker-ов.

    Предоставляет инфраструктуру для запуска задач в отдельном потоке
    с callback-ами для прогресса, результата и ошибок.

    ✅ ИСПРАВЛЕНО: Callback-и вызываются через root.after() для безопасности Tkinter.

    Пример использования:
        class MyWorker(BaseWorker):
            def _run(self):
                # Логика выполнения
                for i in range(100):
                    self._progress(i, 100, "Обработка...")
                    time.sleep(0.1)
                return {"result": "success"}

        worker = MyWorker()
        worker.set_tk_root(root)  # ✅ Обязательно для Tkinter safety
        worker.on_progress(lambda p, t, m: print(f"{p}/{t}: {m}"))
        worker.on_complete(lambda r: print(f"Result: {r}"))
        worker.on_error(lambda e: print(f"Error: {e}"))
        worker.start()
    """

    def __init__(self):
        """Инициализация базового worker-а"""
        # Поток выполнения
        self._thread: threading.Thread | None = None

        # Флаги состояния
        self._is_running = False
        self._stop_requested = False

        # Очереди для потокобезопасной коммуникации
        self._progress_queue: queue.Queue = queue.Queue()
        self._result_queue: queue.Queue = queue.Queue()
        self._error_queue: queue.Queue = queue.Queue()

        # Callback-и
        self._progress_callback: Callable[[int, int, str], None] | None = None
        self._complete_callback: Callable[[Any], None] | None = None
        self._error_callback: Callable[[Exception], None] | None = None

        # ✅ НОВОЕ: Ссылка на Tk root для безопасных callback-ов
        self._tk_root = None

        # Результат выполнения
        self._result: Any = None
        self._error: Exception | None = None

        # Lock для синхронизации
        self._lock = threading.Lock()

    def set_tk_root(self, root) -> "BaseWorker":
        """
        Установить Tk root для безопасных callback-ов.

        Args:
            root: Tkinter root window

        Returns:
            Self для цепочки вызовов
        """
        self._tk_root = root
        return self

    # =========================================================================
    # Callback методы
    # =========================================================================

    def on_progress(self, callback: Callable[[int, int, str], None]) -> "BaseWorker":
        """
        Установить callback для прогресса.

        Args:
            callback: Функция вида (current, total, message)

        Returns:
            Self для цепочки вызовов
        """
        self._progress_callback = callback
        return self

    def on_complete(self, callback: Callable[[Any], None]) -> "BaseWorker":
        """
        Установить callback для результата.

        Args:
            callback: Функция вида (result)

        Returns:
            Self для цепочки вызовов
        """
        self._complete_callback = callback
        return self

    def on_error(self, callback: Callable[[Exception], None]) -> "BaseWorker":
        """
        Установить callback для ошибки.

        Args:
            callback: Функция вида (exception)

        Returns:
            Self для цепочки вызовов
        """
        self._error_callback = callback
        return self

    # =========================================================================
    # Управление потоком
    # =========================================================================

    def start(self) -> None:
        """
        Запустить worker в отдельном потоке.

        Raises:
            RuntimeError: Если worker уже запущен
        """
        with self._lock:
            if self._is_running:
                raise RuntimeError("Worker already running")

            # Сброс состояния
            self._stop_requested = False
            self._result = None
            self._error = None

            # Очистка очередей
            while not self._progress_queue.empty():
                try:
                    self._progress_queue.get_nowait()
                except queue.Empty:
                    break
            while not self._result_queue.empty():
                try:
                    self._result_queue.get_nowait()
                except queue.Empty:
                    break
            while not self._error_queue.empty():
                try:
                    self._error_queue.get_nowait()
                except queue.Empty:
                    break

            # Запуск потока
            self._is_running = True
            self._thread = threading.Thread(target=self._thread_worker, daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """
        Остановить worker.

        Args:
            timeout: Максимальное время ожидания завершения потока (сек)
        """
        self._stop_requested = True

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        with self._lock:
            self._is_running = False

    def is_running(self) -> bool:
        """
        Проверить, запущен ли worker.

        Returns:
            True если worker запущен
        """
        with self._lock:
            return self._is_running

    def wait(self, timeout: float | None = None) -> Any:
        """
        Ожидать завершения работы и получить результат.

        Args:
            timeout: Максимальное время ожидания (сек), None - бесконечно

        Returns:
            Результат выполнения

        Raises:
            Exception: ошибка если worker завершился с ошибкой
        """
        if self._thread:
            self._thread.join(timeout=timeout)

        if self._error:
            raise self._error

        return self._result

    # =========================================================================
    # Внутренние методы
    # =========================================================================

    def _thread_worker(self) -> None:
        """
        Worker-поток, который выполняет основную работу.

        Обрабатывает очереди и вызывает callbacks в основном потоке через root.after().
        """
        try:
            # Выполнение основной работы
            result = self._run()

            # Проверка остановки
            if self._stop_requested:
                return

            # Отправка результата
            self._result_queue.put(result)
            self._result = result

            # ✅ ИСПРАВЛЕНО: Вызов callback результата через root.after()
            if self._complete_callback:
                self._safe_callback(self._complete_callback, result)

        except Exception as e:
            # Сохранение ошибки
            self._error_queue.put(e)
            self._error = e

            # ✅ ИСПРАВЛЕНО: Вызов callback ошибки через root.after()
            if self._error_callback:
                self._safe_callback(self._error_callback, e)

        finally:
            with self._lock:
                self._is_running = False

    def _safe_callback(self, callback, *args, **kwargs):
        """
        Безопасно вызывает callback через root.after() если установлен Tk root.

        Args:
            callback: Функция для вызова
            *args: Аргументы для callback
            **kwargs: Именованные аргументы для callback
        """
        if self._tk_root:
            # ✅ Безопасный вызов через основной поток
            self._tk_root.after(0, callback, *args, **kwargs)
        else:
            # ⚠️ Fallback на прямой вызов (небезопасно для Tkinter)
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"Warning: Callback error: {e}")

    def _progress(self, current: int, total: int, message: str = "") -> None:
        """
        Отправить обновление прогресса.

        Args:
            current: Текущее значение
            total: Всего значений
            message: Сообщение о текущем действии
        """
        self._progress_queue.put((current, total, message))

        # ✅ ИСПРАВЛЕНО: Вызов callback прогресса через root.after()
        if self._progress_callback:
            self._safe_callback(self._progress_callback, current, total, message)

    @abstractmethod
    def _run(self) -> Any:
        """
        Основная логика выполнения worker-а.

        Этот метод должен быть переопределён в подклассах.

        Returns:
            Результат выполнения

        Raises:
            Exception: Любая ошибка в процессе выполнения
        """
        pass

    # =========================================================================
    # Дополнительные методы
    # =========================================================================

    def get_progress(self) -> tuple | None:
        """
        Получить последнее значение прогресса из очереди.

        Returns:
            Кортеж (current, total, message) или None
        """
        try:
            return self._progress_queue.get_nowait()
        except queue.Empty:
            return None

    @property
    def result(self) -> Any:
        """Получить результат выполнения"""
        return self._result

    @property
    def error(self) -> Exception | None:
        """Получить ошибку выполнения"""
        return self._error
