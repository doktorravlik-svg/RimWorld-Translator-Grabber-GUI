import os
from typing import List, Tuple

def safe_walk(directory: str, max_depth: int = 10, follow_symlinks: bool = False) -> List[Tuple[str, List[str], List[str]]]:
    """
    Безопасный обход директории. Исправлены ошибки путей и наполнения списков.
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
                if entry.name.startswith(('.', '$')):
                    continue
                
                if entry.is_dir():
                    if not follow_symlinks and entry.is_symlink():
                        continue
                    dirs.append(entry.name)
                elif entry.is_file():
                    files.append(entry.name)
            
            if files or dirs:
                result.append((current_dir, dirs, files))
            
            for d in dirs:
                # Передаем полный путь для рекурсии
                walk_recursive(os.path.join(current_dir, d), depth + 1)
                
        except (PermissionError, OSError):
            pass
    
    if os.path.exists(directory) and os.path.isdir(directory):
        walk_recursive(directory, 0)
        
    return result
