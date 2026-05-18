# workers/verification_worker.py
"""
Worker для асинхронной верификации переводов.

Этот модуль предоставляет VerificationWorker, который выполняет
верификацию переводов в отдельном потоке, используя VerificationCoordinator.
"""

from loguru import logger
_default_logger = logger  # Save reference to module-level logger
from typing import Any

# Импорт базового класса
# Импорт DTO и мапперов
from dto import (
    VerificationResultDTO,
    VerificationSummaryDTO,
    map_verification_result,
    map_verification_summary,
)

# Импорт модулей верификации
from verification import VerificationCoordinator
# ✅ НОВОЕ: Используем единый модуль для путей
from utils.path_utils import ensure_project_root_in_path
from .base_worker import BaseWorker

# Call ensure_project_root_in_path after all imports
ensure_project_root_in_path()


class VerificationWorker(BaseWorker):
    """
    Worker для асинхронной верификации переводов.

    Выполняет верификацию модов в отдельном потоке, используя
    VerificationCoordinator, и преобразует результаты в DTO.

    Пример использования:
        worker = VerificationWorker(
            mods_folder="C:/RimWorld/Mods",
            checks=["about", "dependencies", "translations"]
        )
        worker.on_progress(lambda p, t, m: print(f"{p}/{t}: {m}"))
        worker.on_complete(lambda r: print(f"Results: {len(r.results)}"))
        worker.on_error(lambda e: print(f"Error: {e}"))
        worker.start()
    """

    def __init__(
        self,
        mods_folder: str,
        checks: list[str] | None = None,
        logger: Any | None = None,
        language: str = "Russian",
        game_path: str | None = None,
    ):
        """
        Инициализация VerificationWorker.

        Args:
            mods_folder: Путь к папке с модами
            checks: Список названий проверок для выполнения (None - все проверки)
            logger: Логгер для вывода сообщений
            language: Язык для верификации ('Russian', 'English', etc.)
            game_path: Путь к папке RimWorld (для загрузки официальных данных)
        """
        super().__init__()

        self.mods_folder = mods_folder
        self.checks = checks or []
        self.logger = logger or _default_logger
        self.language = language
        self.game_path = game_path  # Сохраняем

        # Координатор верификации
        self._coordinator: VerificationCoordinator | None = None

        # Результаты в внутреннем формате
        self._internal_results: list[Any] = []

    def _run(self) -> VerificationSummaryDTO:
        """
        Основная логика выполнения верификации.

        Returns:
            VerificationSummaryDTO с результатами верификации

        Raises:
            Exception: Любая ошибка в процессе верификации
        """
        self.logger.info(f"Начало верификации: {self.mods_folder}")
        self._progress(0, 100, "Инициализация...")

        try:
            # Создание координатора
            self._coordinator = VerificationCoordinator(
                mods_path=self.mods_folder,
                logger=self.logger,
                language=self.language,  # Передаём язык
                game_path=self.game_path,  # Передаём путь к игре
            )

            # Регистрация проверок
            if self.checks:
                self._register_checks()

            # Добавление listener для прогресса
            self._coordinator.add_listener(_WorkerListener(self))

            # Запуск верификации
            self._progress(10, 100, "Сканирование модов...")
            results = self._coordinator.run_verification()

            self._internal_results = results

            # Преобразование в DTO
            self._progress(90, 100, "Преобразование результатов...")
            dto_results = self._map_results(results)

            # Создание summary
            summary = self._create_summary(dto_results)

            self._progress(100, 100, "Верификация завершена")
            self.logger.info(f"Верификация завершена. Проверено модов: {len(results)}")

            return summary

        except Exception as e:
            self.logger.error(f"Ошибка верификации: {e}")
            raise

    def _register_checks(self) -> None:
        """Зарегистрировать выбранные проверки"""
        if not self._coordinator:
            return

        # Сначала удаляем все проверки
        self._coordinator.checks.clear()

        # Регистрируем только выбранные
        check_mapping = {
            "about": "about_xml",
            "dependencies": "dependencies",
            "translations": "translation_structure",
            "structure": "translation_structure",
        }

        for check_name in self.checks:
            # Проверяем, есть ли встроенные проверки с таким именем
            # В реальной реализации здесь может быть динамическая загрузка
            pass

        # Перерегистрируем встроенные проверки
        self._coordinator._register_default_checks()

        # Фильтруем по именам
        if self.checks:
            filtered = []
            for check in self._coordinator.checks:
                if check.name in self.checks or check_mapping.get(check.name) in self.checks:
                    filtered.append(check)
            self._coordinator.checks = filtered

    def _map_results(self, results: list[Any]) -> list[VerificationResultDTO]:
        """
        Преобразовать внутренние результаты в DTO.

        Args:
            results: Список VerificationResult

        Returns:
            Список VerificationResultDTO
        """
        dto_results = []

        for result in results:
            try:
                dto = map_verification_result(result)
                dto_results.append(dto)
            except Exception as e:
                self.logger.warning(f"Ошибка маппинга результата {result.mod_id}: {e}")

        return dto_results

    def _create_summary(self, results: list[VerificationResultDTO]) -> VerificationSummaryDTO:
        """
        Создать сводку результатов.

        Args:
            results: Список DTO результатов

        Returns:
            VerificationSummaryDTO
        """
        # Используем функцию маппинга с внутренними результатами
        summary = map_verification_summary(
            results=self._internal_results,  # Используем внутренние результаты для маппинга
            global_conflicts=self._coordinator.global_conflicts if self._coordinator else [],
            mods_path=self.mods_folder,
        )

        return summary

    @property
    def coordinator(self) -> VerificationCoordinator | None:
        """Получить доступ к координатору верификации"""
        return self._coordinator

    @property
    def internal_results(self) -> list[Any]:
        """Получить внутренние результаты верификации"""
        return self._internal_results


class _WorkerListener:
    """Internal listener for progress updates"""

    def __init__(self, worker: VerificationWorker):
        self.worker = worker

    def on_mod_discovered(self, mod_info: dict) -> None:
        """Called when a mod is discovered"""
        self.worker._progress(20, 100, f"Найден мод: {mod_info.get('mod_name', 'Unknown')}")

    def on_mod_verified(self, result: Any) -> None:
        """Called after a mod is verified"""
        self.worker._progress(50, 100, f"Проверен мод: {result.mod_name}")

    def on_conflict_detected(self, conflict: Any) -> None:
        """Called when a conflict is detected"""
        pass  # Можно логировать

    def on_error(self, error: str, context: dict) -> None:
        """Called when an error occurs"""
        self.worker._progress(0, 100, f"Ошибка: {error}")

    def on_progress(self, current: int, total: int, message: str) -> None:
        """Called on progress update"""
        # Масштабируем прогресс: 20-80% от общего
        scaled = 20 + int(current / total * 60)
        self.worker._progress(scaled, 100, message)
