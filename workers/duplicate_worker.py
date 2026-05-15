# workers/duplicate_worker.py
"""
Worker для слияния дубликатов.

Асинхронный worker, который находит и объединяет дубликаты в модах RimWorld.
"""

from loguru import logger
_default_logger = logger
import os
from dataclasses import dataclass, field
from typing import Any

# ✅ НОВОЕ: Используем единый модуль для путей
from utils.path_utils import ensure_project_root_in_path

ensure_project_root_in_path()

from .base_worker import BaseWorker


@dataclass
class DuplicateResultDTO:
    """DTO для результатов слияния дубликатов."""

    success: bool = True
    files_processed: int = 0
    duplicates_found: int = 0
    duplicates_merged: int = 0
    backups_created: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DuplicateWorker(BaseWorker):
    """
    Worker для асинхронного слияния дубликатов.

    Args:
        mods_folder: Папка с модами
        output_folder: Папка вывода (для бэкапов)
        auto_merge: Автоматически объединять дубликаты
        create_backup: Создавать резервные копии
        logger: Логгер
    """

    def __init__(
        self,
        mods_folder: str,
        output_folder: str = "",
        auto_merge: bool = True,
        create_backup: bool = True,
        logger: Any | None = None,
    ):
        super().__init__()
        self.mods_folder = mods_folder
        self.output_folder = output_folder or os.path.join(mods_folder, "Duplicates_Backup")
        self.auto_merge = auto_merge
        self.create_backup = create_backup
        self.logger = logger or _default_logger

    def _run(self) -> DuplicateResultDTO:
        """Выполнить слияние дубликатов."""
        from duplicates.duplicate_merger import run_duplicate_merger

        self.logger.info(f"Начало слияния дубликатов: {self.mods_folder}")
        self._progress(0, 100, "Сканирование модов...")

        result = DuplicateResultDTO()

        try:
            # Вызываем существующую функцию слияния
            merge_result = run_duplicate_merger(
                mods_folder=self.mods_folder,
                output_folder=self.output_folder,
                auto_merge=self.auto_merge,
                create_backup=self.create_backup,
                log_callback=lambda msg: self._log_and_progress(msg, result),
            )

            if merge_result:
                result.files_processed = merge_result.get("files_processed", 0)
                result.duplicates_found = merge_result.get("duplicates_found", 0)
                result.duplicates_merged = merge_result.get("duplicates_merged", 0)
                result.backups_created = merge_result.get("backups_created", 0)
                result.errors = merge_result.get("errors", [])
                result.warnings = merge_result.get("warnings", [])

            self._progress(100, 100, "Слияние завершено")
            result.success = len(result.errors) == 0

            return result

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            self.logger.error(f"Ошибка при слиянии дубликатов: {e}")
            raise

    def _log_and_progress(self, message: str, result: DuplicateResultDTO):
        """Логирование и обновление прогресса."""
        self.logger.info(message)

        # Прогресс на основе этапа обработки
        if result.duplicates_found == 0 and result.duplicates_merged == 0:
            # Ещё не processed
            progress = 50
        elif result.duplicates_found > 0:
            progress = 75
        else:
            progress = 90

        self._progress(progress, 100, message)
