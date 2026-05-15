# workers/integrity_worker.py
"""
Worker для проверки целостности файлов.

Асинхронный worker, который проверяет целостность XML файлов модов RimWorld.
"""

import os

from loguru import logger
_default_logger = logger
from dataclasses import dataclass, field
from typing import Any

# ✅ НОВОЕ: Используем единый модуль для путей
from utils.path_utils import ensure_project_root_in_path

ensure_project_root_in_path()

from .base_worker import BaseWorker


@dataclass
class IntegrityResultDTO:
    """DTO для результатов проверки целостности."""

    success: bool = True
    files_checked: int = 0
    files_valid: int = 0
    files_invalid: int = 0
    warnings: int = 0
    errors: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


class IntegrityWorker(BaseWorker):
    """
    Worker для асинхронной проверки целостности.

    Args:
        mods_folder: Папка с модами
        language_filter: Язык для фильтрации (например, "Russian") или None для всех
        logger: Логгер
    """

    def __init__(
        self,
        mods_folder: str,
        language_filter: str | None = None,
        logger: Any | None = None,
    ):
        super().__init__()
        self.mods_folder = mods_folder
        self.language_filter = language_filter
        self.logger = logger or _default_logger

    def _run(self) -> IntegrityResultDTO:
        """Выполнить проверку целостности."""
        from integrity.integrity_checker import check_integrity

        self.logger.info(f"Начало проверки целостности: {self.mods_folder}")
        self._progress(0, 100, "Подсчёт файлов...")

        # ✅ ИСПРАВЛЕНО: Сначала быстро считаем общее количество XML файлов
        total_files = 0
        for root, dirs, files in os.walk(self.mods_folder):
            for filename in files:
                if filename.endswith(".xml"):
                    total_files += 1

        self.logger.info(f"Найдено файлов для проверки: {total_files}")
        self._progress(5, 100, f"Проверка {total_files} файлов...")

        # ✅ ИСПРАВЛЕНО: Инициализируем success=False
        result = IntegrityResultDTO(success=False)
        errors_list = []
        details_list = []
        files_count = 0  # ✅ ИСПРАВЛЕНО: Используем обычную переменную с nonlocal

        def log_callback(msg):
            """Собираем логи и обновляем прогресс."""
            nonlocal files_count  # ✅ ИСПРАВЛЕНО: Используем nonlocal вместо списка
            self.logger.info(msg)

            # ✅ ИСПРАВЛЕНО: Считаем только реальные файлы, не служебные сообщения
            if msg.startswith("[FILE]"):
                files_count += 1
                result.files_checked = files_count

            # Сохраняем ошибки и подробности
            if msg.startswith("  ❌"):
                errors_list.append(msg)
                result.files_invalid = len(errors_list)
            elif msg.startswith("  ⚠️"):
                details_list.append(msg)
                result.warnings = len(details_list)

            # ✅ ИСПРАВЛЕНО: Честный прогресс-бар на основе общего количества файлов
            if total_files > 0:
                progress = min(int((files_count / total_files) * 90), 90)
            else:
                progress = 0
            self._progress(progress, 100, f"Проверено: {files_count}/{total_files}")

        try:
            # Вызываем функцию проверки
            is_valid = check_integrity(
                mods_folder=self.mods_folder,
                language_filter=self.language_filter,
                log_callback=log_callback,
            )

            result.success = is_valid  # ✅ Устанавливаем результат проверки
            result.errors = errors_list
            result.details = details_list
            result.files_valid = result.files_checked - result.files_invalid

            self._progress(100, 100, "Проверка завершена")
            self.logger.info(
                f"Проверка завершена: {result.files_checked} файлов, "
                f"{result.files_valid} OK, {result.files_invalid} с ошибками"
            )

            return result

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            self.logger.error(f"Ошибка при проверке целостности: {e}")
            raise
