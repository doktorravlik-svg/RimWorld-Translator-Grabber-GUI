"""
Вспомогательные функции для логирования с использованием stack introspection.
Позволяют отслеживать, какие файлы и функции вызываются в данный момент.
"""

import inspect
from loguru import logger


def log_call_stack(message: str = "Call stack:", max_depth: int = 5, level: str = "DEBUG"):
    """
    Логирует текущий стек вызовов с указанием файла, функции и строки.
    
    Args:
        message: Сообщение перед стеком
        max_depth: Максимальная глубина стека (0 для всей стека)
        level: Уровень логирования (DEBUG, INFO, etc.)
    """
    try:
        stack = inspect.stack()
        # Пропускаем текущую функцию (log_call_stack)
        start_idx = 1
        end_idx = len(stack) if max_depth == 0 else min(start_idx + max_depth, len(stack))
        
        # Формируем сообщение о стеке
        from loguru import logger as log
        
        # Используем opt(depth) чтобы loguru правильно определил вызывающую функцию
        log.opt(depth=1).log(level, message)
        
        for i in range(start_idx, end_idx):
            frame_info = stack[i]
            filename = frame_info.filename
            lineno = frame_info.lineno
            func_name = frame_info.function
            indent = "  " * (i - start_idx)
            log.opt(depth=1).log(
                level,
                f"{indent}#{i - start_idx} {filename}:{lineno} {func_name}()"
            )
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
    
    Returns:
        Словарь с ключами: 'file', 'line', 'function', 'module'
    """
    try:
        # Пропускаем текущую функцию и get_current_caller_info
        frame = inspect.currentframe()
        if frame:
            # Идем на два уровня вверх (через f_back)
            caller_frame = frame.f_back
            if caller_frame:
                return {
                    "file": caller_frame.f_code.co_filename,
                    "line": caller_frame.f_lineno,
                    "function": caller_frame.f_code.co_name,
                    "module": caller_frame.f_globals.get("__name__", "unknown"),
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
