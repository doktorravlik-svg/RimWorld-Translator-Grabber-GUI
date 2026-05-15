# utils/backup_manager.py
"""
Централизованный менеджер резервных копий.

Управление бекапами:
- Создание бекапов с уникальными именами
- Ограничение количества бекапов
- Автоматическая очистка старых бекапов
- Предотвращение дублирования
"""

import os
import shutil
from datetime import datetime
from typing import Optional


class BackupManager:
    """
    Менеджер резервных копий.
    
    Args:
        max_backups: Максимальное количество бекапов для одной папки (по умолчанию 3)
        cleanup_old: Удалять ли старые бекапы при создании нового
    """
    
    def __init__(self, max_backups: int = 3, cleanup_old: bool = True):
        self.max_backups = max_backups
        self.cleanup_old = cleanup_old
    
    def create_backup(
        self, 
        folder_path: str, 
        backup_name: Optional[str] = None,
        logger=None
    ) -> Optional[str]:
        """
        Создать резервную копию папки.
        
        Args:
            folder_path: Путь к папке для бекапа
            backup_name: Имя бекапа (по умолчанию: folder_backup_YYYYMMDD_HHMMSS)
            logger: Логгер
            
        Returns:
            Путь к бекапу или None если ошибка
        """
        if not os.path.exists(folder_path):
            if logger:
                logger.warning(f"Папка не существует: {folder_path}")
            return None
        
        # Получаем папку для бекапов (рядом с оригиналом или в специальной директории)
        parent_dir = os.path.dirname(folder_path)
        folder_name = os.path.basename(folder_path)
        
        # Формируем имя бекапа
        if backup_name:
            backup_dir = os.path.join(parent_dir, backup_name)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(parent_dir, f"{folder_name}_backup_{timestamp}")
        
        # ✅ ПРОВЕРКА: Если бекап уже существует - не создаём дубликат
        if os.path.exists(backup_dir):
            if logger:
                logger.debug(f"Бекап уже существует: {backup_dir}")
            return backup_dir
        
        try:
            shutil.copytree(folder_path, backup_dir)
            if logger:
                logger.info(f"✅ Создан бекап: {backup_dir}")
            
            # ✅ Принудительная очистка для Windows - даём ОС время освободить дескрипторы
            import gc
            gc.collect()
            
            # ✅ Небольшая задержка для Windows (файловые дескрипторы)
            import time
            time.sleep(3)
            
            # ✅ ОЧИСТКА: Удаляем старые бекапы если включено
            if self.cleanup_old:
                self._cleanup_old_backups(parent_dir, folder_name, logger)
            
            return backup_dir
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Ошибка создания бекапа: {e}")
            return None
    
    def _cleanup_old_backups(self, parent_dir: str, folder_name: str, logger=None):
        """
        Удаляет старые бекапы, оставляя только max_backups последних.
        
        Args:
            parent_dir: Родительская папка
            folder_name: Имя оригинальной папки
            logger: Логгер
        """
        # Находим все бекапы для этой папки
        backup_prefix = f"{folder_name}_backup_"
        backups = []
        
        try:
            for item in os.listdir(parent_dir):
                if item.startswith(backup_prefix):
                    full_path = os.path.join(parent_dir, item)
                    if os.path.isdir(full_path):
                        # Получаем timestamp из имени
                        timestamp_str = item.replace(backup_prefix, "")
                        backups.append((timestamp_str, full_path))
            
            # Сортируем по timestamp (новые сначала)
            backups.sort(reverse=True)
            
            # Удаляем лишние
            if len(backups) > self.max_backups:
                to_delete = backups[self.max_backups:]
                for timestamp_str, backup_path in to_delete:
                    try:
                        shutil.rmtree(backup_path)
                        if logger:
                            logger.info(f"🗑️ Удалён старый бекап: {backup_path}")
                    except Exception as e:
                        if logger:
                            logger.warning(f"Не удалось удалить бекап {backup_path}: {e}")
                            
        except Exception as e:
            if logger:
                logger.debug(f"Ошибка при очистке бекапов: {e}")
    
    def list_backups(self, folder_path: str) -> list[str]:
        """
        Список всех бекапов для папки.
        
        Args:
            folder_path: Путь к оригинальной папке
            
        Returns:
            Список путей к бекапам
        """
        parent_dir = os.path.dirname(folder_path)
        folder_name = os.path.basename(folder_path)
        backup_prefix = f"{folder_name}_backup_"
        
        backups = []
        try:
            for item in os.listdir(parent_dir):
                if item.startswith(backup_prefix):
                    full_path = os.path.join(parent_dir, item)
                    if os.path.isdir(full_path):
                        backups.append(full_path)
        except Exception:
            pass
        
        return sorted(backups, reverse=True)  # Новые сначала
    
    def delete_backup(self, backup_path: str, logger=None) -> bool:
        """
        Удалить конкретный бекап.
        
        Args:
            backup_path: Путь к бекапу
            logger: Логгер
            
        Returns:
            True если успешно удалён
        """
        try:
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
                if logger:
                    logger.info(f"🗑️ Удалён бекап: {backup_path}")
                return True
            return False
        except Exception as e:
            if logger:
                logger.error(f"Ошибка удаления бекапа: {e}")
            return False


# Глобальный экземпляр для удобства
_backup_manager = BackupManager(max_backups=3, cleanup_old=True)


def get_backup_manager() -> BackupManager:
    """Получить глобальный менеджер бекапов."""
    return _backup_manager


def create_backup(folder_path: str, logger=None, backup_name: str = None) -> Optional[str]:
    """
    Удобная функция для создания бекапа через глобальный менеджер.
    
    Args:
        folder_path: Путь к папке
        logger: Логгер
        backup_name: Имя бекапа (опционально)
        
    Returns:
        Путь к бекапу или None
    """
    return _backup_manager.create_backup(folder_path, backup_name, logger)
