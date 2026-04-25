# utils/error_handler.py
"""
Унифицированная обработка ошибок для всего приложения.

Согласно лучшим практикам Python (2024-2025):
- Используем конкретные исключения
- Логируем все ошибки
- Даем осмысленные сообщения
- Не "глотаем" исключения без логирования

Пример использования:
    from utils.error_handler import safe_execute, AppError
    
    @safe_execute(fallback_value=None)
    def risky_operation():
        return 1 / 0
        
    try:
        result = load_config("config.json")
    except AppError as e:
        logger.error(f"Failed to load config: {e}")
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AppError(Exception):
    """Базовое исключение для приложения."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class ConfigError(AppError):
    """Ошибка конфигурации."""

    pass


class FileError(AppError):
    """Ошибка работы с файлами."""

    pass


class NetworkError(AppError):
    """Ошибка сети (API переводчиков)."""

    pass


class ValidationError(AppError):
    """Ошибка валидации данных."""

    pass


def safe_execute(
    fallback: Any = None,
    logger_instance: logging.Logger | None = None,
    catch_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """
    Декоратор для безопасного выполнения функций.
    При ошибке возвращает fallback и логирует исключение.

    Args:
        fallback: Значение для возврата при ошибке
        logger_instance: Логгер (по умолчанию использует logger из этого модуля)
        catch_exceptions: Кортеж перехватываемых исключений

    Returns:
        Декорированную функцию

    Example:
        @safe_execute(fallback=[])
        def load_data():
            return risky_api_call()
    """
    log = logger_instance or logger

    def decorator(func: Callable[..., T]) -> Callable[..., T | Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T | Any:
            try:
                return func(*args, **kwargs)
            except catch_exceptions as e:
                log.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
                return fallback

        return wrapper

    return decorator


def safe_execute_method(
    fallback: Any = None,
    logger_instance: logging.Logger | None = None,
    catch_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """
    Декоратор для безопасного выполнения методов классов.
    Аналогичен safe_execute, но корректно работает с self/cls.
    """
    log = logger_instance or logger

    def decorator(func: Callable[..., T]) -> Callable[..., T | Any]:
        @functools.wraps(func)
        def wrapper(self, *args: Any, **kwargs: Any) -> T | Any:
            try:
                return func(self, *args, **kwargs)
            except catch_exceptions as e:
                class_name = self.__class__.__name__
                log.error(f"Ошибка в {class_name}.{func.__name__}: {e}", exc_info=True)
                return fallback

        return wrapper

    return decorator


def handle_file_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Декоратор для функций работы с файлами."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logger.error(f"Файл не найден: {e.filename}")
            raise FileError(f"Файл не найден: {e.filename}", e) from e
        except PermissionError as e:
            logger.error(f"Нет доступа к файлу: {e.filename}")
            raise FileError(f"Нет доступа к файлу: {e.filename}", e) from e
        except OSError as e:
            logger.error(f"Ошибка файловой системы: {e}")
            raise FileError(f"Ошибка файловой системы: {e}", e) from e

    return wrapper


def handle_config_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Декоратор для функций работы с конфигурацией."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except (FileError, OSError) as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            raise ConfigError(f"Ошибка загрузки конфигурации: {e}", e) from e
        except ValueError as e:
            logger.error(f"Неверный формат конфигурации: {e}")
            raise ConfigError(f"Неверный формат конфигурации: {e}", e) from e

    return wrapper


def handle_network_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Декоратор для функций сетевых запросов (API переводчиков)."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except ConnectionError as e:
            logger.error(f"Ошибка соединения: {e}")
            raise NetworkError(f"Ошибка соединения: {e}", e) from e
        except TimeoutError as e:
            logger.error(f"Таймаут запроса: {e}")
            raise NetworkError(f"Таймаут запроса: {e}", e) from e
        except OSError as e:
            logger.error(f"Сетевая ошибка: {e}")
            raise NetworkError(f"Сетевая ошибка: {e}", e) from e

    return wrapper


def setup_logging(level: int = logging.INFO, log_file: str | None = None) -> None:
    """
    Настройка логирования для всего приложения.

    Args:
        level: Уровень логирования
        log_file: Путь к файлу логов (опционально)
    """
    # Формат логогов
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)

    # File handler (если указан файл)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except OSError as e:
            print(f"Не удалось создать файл логов {log_file}: {e}")
