import os
from loguru import logger


def safe_walk(directory: str, max_depth: int = 10, follow_symlinks: bool = False) -> list[tuple[str, list[str], list[str]]]:
    """
    Безопасный обход директории с ограничением глубины и защитой от зацикливаний.
    """
    result = []
    visited = set()

    def walk_recursive(current_dir: str, depth: int):
        if depth > max_depth:
            return

        try:
            real_path = os.path.realpath(current_dir)
            if real_path in visited:
                return
            visited.add(real_path)

            entries = list(os.scandir(current_dir))
            dirs = []
            files = []

            for entry in entries:
                # Пропускаем скрытые файлы и системные папки Windows ($Recycle.Bin и т.д.)
                if entry.name.startswith(('.', '$')):
                    continue

                if entry.is_dir():
                    if not follow_symlinks and entry.is_symlink():
                        continue
                    dirs.append(entry.name)
                elif entry.is_file():
                    files.append(entry.name)

            # Добавляем в результат в любом случае (даже если папка пустая),
            # чтобы полностью сохранять структуру директорий как в os.walk
            result.append((current_dir, dirs, files))

            for d in dirs:
                walk_recursive(os.path.join(current_dir, d), depth + 1)

        except (PermissionError, OSError) as e:
            # Логируем ошибку для диагностики, но не прерываем выполнение
            logger.debug(f"Доступ ограничен или ошибка FS для {current_dir}: {e}")

    if os.path.exists(directory) and os.path.isdir(directory):
        walk_recursive(directory, 0)

    return result
