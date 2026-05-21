"""
Вспомогательные функции для логирования с использованием stack introspection.
Позволяют отслеживать, какие файлы и функции вызываются в данный момент.
"""

import sys
from loguru import logger


def log_call_stack(message: str = "Call stack:", max_depth: int = 5, level: str = "DEBUG"):
    """
    Логирует текущий стек вызовов с указанием файла, функции и строки.
    Использует sys._getframe для улучшенной производительности.

    Args:
        message: Сообщение перед стеком
        max_depth: Максимальная глубина стека (0 для всей стека)
        level: Уровень логирования (DEBUG, INFO, etc.)
    """
    try:
        from loguru import logger as log

        log.opt(depth=1).log(level, message)

        frame = sys._getframe(1)  # Пропускаем текущую функцию
        depth = 0
        while frame and (max_depth == 0 or depth < max_depth):
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            func_name = frame.f_code.co_name
            indent = "  " * depth

            log.opt(depth=1).log(
                level,
                f"{indent}#{depth} {filename}:{lineno} {func_name}()"
            )
            frame = frame.f_back
            depth += 1
    except Exception as e:
        logger.error(f"Ошибка при логировании стека: {e}")


def log_function_entry(logger_instance=None, level: str = "DEBUG"):
    """
    Декоратор для логирования входа в функцию и выхода из неё.
    Использует stack introspection для определения имени функции.

    Usage:
        @log_function_entry()
        def my_function():
            pass
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Получаем информацию о функции
            func_name = func.__name__
            module_name = func.__module__

            log = logger_instance or logger
            log.opt(depth=1).log(level, f"→ Вход в {module_name}.{func_name}()")
            try:
                result = func(*args, **kwargs)
                log.opt(depth=1).log(level, f"← Выход из {module_name}.{func_name}()")
                return result
            except Exception as e:
                log.opt(depth=1).log("ERROR", f"✗ Ошибка в {module_name}.{func_name}(): {e}")
                raise

        return wrapper
    return decorator


def get_current_caller_info() -> dict:
    """
    Возвращает информацию о вызывающей функции.
    Использует sys._getframe для улучшенной производительности.

    Returns:
        Словарь с ключами: 'file', 'line', 'function', 'module'
    """
    try:
        frame = sys._getframe(1)  # Пропускаем текущую функцию
        if frame:
            return {
                "file": frame.f_code.co_filename,
                "line": frame.f_lineno,
                "function": frame.f_code.co_name,
                "module": frame.f_globals.get("__name__", "unknown"),
            }
    except Exception:
        pass

    return {"file": "unknown", "line": 0, "function": "unknown", "module": "unknown"}


# Пример использования:
if __name__ == "__main__":
    # Логирование стека
    log_call_stack("Текущий стек вызовов:", max_depth=3)

    # Использование декоратора
    @log_function_entry()
    def example_function():
        log_call_stack("Внутри example_function:", max_depth=2)

    example_function()

    # Получение информации о вызывающей функции
    info = get_current_caller_info()
    logger.info(f"Вызывающая функция: {info['module']}.{info['function']}() в {info['file']}:{info['line']}")
