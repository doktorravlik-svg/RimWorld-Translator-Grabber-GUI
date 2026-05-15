# utils/loguru_setup.py
"""
Настройка системы логирования на базе loguru.

Заменяет стандартный модуль logging на loguru с поддержкой:
- Перехвата логов от сторонних библиотек через InterceptHandler
- Переключения между режимами INFO и DEBUG
- Единого формата вывода
- Поддержки extra через .bind()
- Раздельных sink для разных уровней
- Фильтрации логов по контексту
"""

import inspect
import logging
import sys
from itertools import takewhile
from pathlib import Path
from typing import Callable, Literal

import loguru
from loguru import logger

# Флаг для предотвращения повторной настройки с удалением sinks
_setup_done = False
_current_config = {}
# ID sinks, добавленных через setup_logging()
_sink_ids: list[int] = []
_console_sink_id = None


class InterceptHandler(logging.Handler):
    """
    Перехватчик логов из стандартного logging в loguru.

    Позволяет перенаправлять сообщения от сторонних библиотек,
    использующих стандартный logging, в loguru с сохранением уровня.

    Использует интроспекцию стека (stack introspection) для
    определения правильного контекста вызова.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Перехватывает запись лога и перенаправляет в loguru."""
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Stack introspection: используем inspect.currentframe() для
        # определения реального места вызова (пропуская фреймы logging)
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def _context_filter(record: dict, context_key: str, allowed_values: list[str]) -> bool:
    """
    Фильтр для направления логов в разные файлы на основе контекста из .bind().

    Args:
        record: Запись лога от loguru
        context_key: Ключ в extra (например, 'module' или 'category')
        allowed_values: Список разрешенных значений для данного sink

    Returns:
        True если запись должна быть записана в данный sink
    """
    extra = record.get("extra", {})
    value = extra.get(context_key)
    return value in allowed_values or value is None


def create_module_filter(module_name: str) -> Callable[[dict], bool]:
    """
    Создает фильтр для конкретного модуля.

    Args:
        module_name: Имя модуля (например, 'translation', 'verification')

    Returns:
        Функция-фильтр для использования в sink
    """

    def filter_func(record: dict) -> bool:
        name = record.get("name", "")
        extra = record.get("extra", {})
        bound_module = extra.get("module")

        if bound_module:
            return bound_module == module_name

        return name.startswith(module_name)

    return filter_func


def setup_logging(
    debug_mode: bool = False,
    log_file: str | None = None,
    warning_log_file: str | None = None,
    rotation: str = "10 MB",
    retention: str = "1 week",
) -> None:
    """
    Настраивает систему логирования loguru.

    Args:
        debug_mode: Если True, включает режим DEBUG с подробной информацией
                    (файл, строка, функция). В режиме INFO также видны все сообщения.
        log_file: Путь к основному файлу лога (все уровни).
        warning_log_file: Путь к файлу для WARNING+ (с enqueue=True для потокобезопасности).
        rotation: Размер файла для ротации.
        retention: Время хранения старых логов.

    Returns:
        None

    Примеры:
        setup_logging(debug_mode=False)  # Только INFO и выше в консоли
        setup_logging(debug_mode=True)   # DEBUG с подробной информацией
    """
    global _setup_done, _current_config, _sink_ids

    # Проверяем, нужно ли обновлять конфигурацию
    new_config = {
        "debug_mode": debug_mode,
        "log_file": log_file,
        "warning_log_file": warning_log_file,
        "rotation": rotation,
        "retention": retention,
    }

    if _setup_done and new_config == _current_config:
        return  # Конфигурация не изменилась, ничего не делаем

    # Удаляем только свои sinks (добавленные этим вызовом ранее)
    for sink_id in _sink_ids:
        try:
            logger.remove(sink_id)
        except Exception:
            pass
    _sink_ids.clear()

    _setup_done = True
    _current_config = new_config

    # Базовый формат с поддержкой extra
    base_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
    )

    if debug_mode:
        console_format = (
            base_format
            + "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
              "<cyan>{extra}</cyan> - "
              "<level>{message}</level>"
        )
        console_level = "DEBUG"
    else:
        console_format = (
            base_format
            + "<cyan>{name}:{function}:{line}</cyan> - "
            "<level>{message}</level>"
        )
        console_level = "INFO"

    sink_id = logger.add(
        sys.stdout,
        format=console_format,
        level=console_level,
        colorize=True,
    )
    _sink_ids.append(sink_id)
    _console_sink_id = sink_id

    # Основной файл лога (все уровни, с поддержкой backtrace и diagnose)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        def patch_record(record):
            """Добавляет информацию о стеке вызовов в запись лога."""
            # Получаем информацию о вызывающем коде
            record["extra"]["module"] = record.get("name", "unknown")
            record["extra"]["func"] = record.get("function", "unknown")
            record["extra"]["lineno"] = record.get("line", 0)
            return record

        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "<level>{name}:{function}:{line}</level> | "
            "{message}"
            "{exception}\n"
        )

        sink_id = logger.add(
            log_file,
            format=file_format,
            level="DEBUG",
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
            catch=True,
        )
        _sink_ids.append(sink_id)

    # Отдельный sink для WARNING и выше с enqueue=True
    if warning_log_file:
        warning_path = Path(warning_log_file)
        warning_path.parent.mkdir(parents=True, exist_ok=True)

        warning_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "<level>{name}:{function}:{line}</level> | "
            "{message}"
            "{exception}\n"
        )

        sink_id = logger.add(
            warning_log_file,
            format=warning_format,
            level="WARNING",
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
            enqueue=True,
            backtrace=True,
            diagnose=True,
            catch=True,
        )
        _sink_ids.append(sink_id)

    _intercept_standard_logging(console_level)


def _intercept_standard_logging(level: str = "INFO") -> None:
    """
    Перехватывает логи из стандартного модуля logging.

    Настраивает перенаправление всех логов из стандартного logging
    в loguru через InterceptHandler.

    Args:
        level: Минимальный уровень логирования для перехвата.
    """
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True

    logging.getLogger().setLevel(getattr(logging, level, logging.INFO))


def is_logging_setup() -> bool:
    """
    Проверяет, была ли выполнена настройка логирования.

    Returns:
        True если setup_logging() уже был вызван
    """
    return _setup_done


def get_logger(name: str | None = None, **bind_kwargs):
    """
    Возвращает экземпляр logger из loguru с опциональным bind().

    Args:
        name: Имя логгера (используется для совместимости, в loguru игнорируется).
        **bind_kwargs: Аргументы для привязки через .bind() (например, module='translation').

    Returns:
        Экземпляр logger из loguru (возможно с привязанным контекстом).
    """
    if bind_kwargs:
        return logger.bind(**bind_kwargs)
    return logger


def set_debug_mode(enabled: bool) -> None:
    """
    Переключает режим логирования в процессе работы.

    Args:
        enabled: True для включения DEBUG режима, False для INFO.
    """
    global _console_sink_id

    # Удаляем только console sink, если он был добавлен через setup_logging
    if _console_sink_id is not None:
        try:
            logger.remove(_console_sink_id)
        except Exception:
            pass
        _console_sink_id = None

    if enabled:
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
            "<cyan>{extra}</cyan> - "
            "<level>{message}</level>"
        )
        console_level = "DEBUG"
    else:
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra}</cyan> - "
            "<level>{message}</level>"
        )
        console_level = "INFO"

    _console_sink_id = logger.add(
        sys.stdout,
        format=console_format,
        level=console_level,
        colorize=True,
    )

    _intercept_standard_logging(console_level)


def add_module_sink(
    module_name: str,
    log_file: str,
    level: str = "DEBUG",
    rotation: str = "10 MB",
    retention: str = "1 week",
) -> int:
    """
    Добавляет отдельный sink для конкретного модуля.

    Args:
        module_name: Имя модуля (например, 'translation', 'verification')
        log_file: Путь к файлу лога
        level: Минимальный уровень логирования
        rotation: Размер файла для ротации
        retention: Время хранения старых логов

    Returns:
        ID sink (для возможного удаления через logger.remove(id))
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{extra} - "
        "{message}"
    )

    filter_func = create_module_filter(module_name)

    sink_id = logger.add(
        log_file,
        format=file_format,
        level=level,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        filter=filter_func,
        backtrace=True,
        diagnose=True,
    )

    return sink_id


def catch_main_loop(func: Callable) -> Callable:
    """
    Декоратор для защиты главного цикла обработки.

    Ловит все исключения, логирует их с подробным backtrace
    и diagnose, предотвращая падение приложения.

    Args:
        func: Функция для защиты

    Returns:
        Обернутая функция
    """

    @logger.catch(reraise=False, backtrace=True, diagnose=True)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def get_call_stack(exclude_loguru: bool = True) -> list[dict[str, str | int]]:
    """
    Возвращает информацию о стеке вызовов через интроспекцию.

    Использует inspect.currentframe() для обхода стека.
    Полезно для отладки и логирования контекста выполнения.

    Args:
        exclude_loguru: Исключить внутренние фреймы loguru из результата

    Returns:
        Список словарей с информацией о каждом фрейме:
        - filename: путь к файлу
        - lineno: номер строки
        - function: имя функции
        - code_context: контекст кода (если доступен)
    """
    frames = []
    frame = inspect.currentframe()

    # Пропускаем текущий фрейм (get_call_stack)
    frame = frame.f_back

    loguru_path = str(loguru.__file__) if hasattr(loguru, '__file__') else ''

    while frame:
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        func_name = frame.f_code.co_name

        # Фильтрация внутренних фреймов loguru
        if exclude_loguru and 'loguru' in filename:
            frame = frame.f_back
            continue

        frames.append({
            'filename': filename,
            'lineno': lineno,
            'function': func_name,
        })

        frame = frame.f_back

    frames.reverse()
    return frames


def format_call_stack(stack: list[dict[str, str | int]] | None = None,
                      separator: str = ' > ') -> str:
    """
    Форматирует стек вызовов в читаемую строку.

    Args:
        stack: Стек вызовов от get_call_stack(). Если None, получает текущий.
        separator: Разделитель между уровнями стека

    Returns:
        Отформатированная строка вида:
        file:func:line > file:func:line > ...
    """
    if stack is None:
        stack = get_call_stack()

    return separator.join(
        f"{s['filename']}:{s['function']}:{s['lineno']}"
        for s in stack
    )


def log_with_stack(level: str, message: str, **kwargs) -> None:
    """
    Логирует сообщение с добавлением информации о стеке вызовов.

    Использует stack introspection для добавления контекста вызова.
    Полезно для отслеживания цепочки вызовов в сложных операциях.

    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Сообщение для логирования
        **kwargs: Дополнительные аргументы для bind()
    """
    stack_str = format_call_stack()
    extra = {'call_stack': stack_str}
    extra.update(kwargs)

    log_func = getattr(logger, level.lower(), logger.info)
    log_func("{message} | stack: {extra[call_stack]}", extra=extra)


def log_error_with_context(message: str, exc: Exception | None = None, **kwargs) -> None:
    """
    Логирует ошибку с полным контекстом: модуль, функция, стек вызовов.

    Используется для детального логирования ошибок с указанием точного места,
    где возникла проблема, и цепочки вызовов.

    Args:
        message: Описание ошибки
        exc: Исключение (если есть)
        **kwargs: Дополнительные аргументы для bind()
    """
    stack = get_call_stack(exclude_loguru=True)
    stack_str = format_call_stack(stack)

    extra = {
        'call_stack': stack_str,
        'error_location': f"{stack[-1]['filename']}:{stack[-1]['function']}:{stack[-1]['lineno']}" if stack else 'unknown'
    }
    extra.update(kwargs)

    if exc:
        logger.opt(exception=exc).bind(**extra).error(f"{message}: {exc}")
    else:
        logger.bind(**extra).error(f"{message} | context: {stack_str}")


def trace_function_call(func_name: str | None = None):
    """
    Декоратор для трассировки вызовов функции с логированием стека.

    Логирует начало и конец выполнения функции, что позволяет
    отслеживать, в каком модуле и функции произошла ошибка.

    Args:
        func_name: Имя функции для логирования (по умолчанию - реальное имя)
    """
    def decorator(func):
        name = func_name or func.__name__
        def wrapper(*args, **kwargs):
            logger.debug(f"→ Вход в {name}()")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"← Выход из {name}()")
                return result
            except Exception as e:
                stack = get_call_stack(exclude_loguru=True)
                logger.opt(exception=e).error(
                    f"✗ Ошибка в {name}() | "
                    f"Контекст: {format_call_stack(stack)}"
                )
                raise
        return wrapper
    return decorator
