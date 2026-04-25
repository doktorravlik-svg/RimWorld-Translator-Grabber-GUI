# translation/engines/fallback_chain.py
"""
Fallback-цепочка движков перевода.

Автоматически переключается на следующий движок при ошибке.
Использует умную ротацию на основе статистики успешности.
"""

import time

from translation.engines.base import TranslationEngine


class FallbackChain:
    """
    Цепочка движков с автоматическим fallback и умной ротацией.

    При сбое одного движка автоматически переключается на следующий.
    Использует статистику успешности для приоритизации движков.

    Args:
        engines: Список движков в порядке приоритета
        target_lang: Целевой язык
        proxy: Прокси для всех движков
        retry_delay: Задержка между попытками (секунды)
        max_retries_per_engine: Макс. попыток на один движок
        smart_routing: Включить умную маршрутизацию (по умолчанию True)
    """

    def __init__(
        self,
        target_lang: str = "ru",
        engine_names: list[str] | None = None,
        proxy: dict | None = None,
        retry_delay: float = 0.8,
        max_retries_per_engine: int = 3,
        smart_routing: bool = True,
    ):
        self.target_lang = target_lang
        self.proxy = proxy
        self.retry_delay = retry_delay
        self.max_retries = max_retries_per_engine
        self.smart_routing = smart_routing

        # ✅ ВАЖНО: Инициализируем _error_log ДО создания движков
        self._error_log: list[str] = []
        self._max_error_log = 1000  # Максимум 1000 записей

        # Движки по умолчанию: Google -> MyMemory -> DeepL -> Bing -> DeepLX -> Translators
        if engine_names is None:
            engine_names = ["google", "mymemory", "deepl", "bing", "deeplx", "translators"]

        self.engines: list[TranslationEngine] = []
        for name in engine_names:
            engine = self._create_engine(name)
            if engine:
                self.engines.append(engine)

        self._current_engine_index = 0

        # ✅ НОВОЕ: Статистика успешности для умной ротации
        self._success_counts: dict[str, int] = {name: 0 for name in engine_names}
        self._total_attempts: dict[str, int] = {name: 0 for name in engine_names}

    def _create_engine(self, name: str) -> TranslationEngine | None:
        """Создаёт движок по имени."""
        try:
            if name == "google":
                from translation.engines.google_engine import GoogleEngine

                return GoogleEngine(target_lang=self.target_lang, proxy=self.proxy)
            elif name == "deepl":
                from translation.engines.deepl_engine import DeepLEngine

                return DeepLEngine(target_lang=self.target_lang, proxy=self.proxy)
            elif name == "mymemory":
                from translation.engines.mymemory_engine import MyMemoryEngine

                return MyMemoryEngine(target_lang=self.target_lang, proxy=self.proxy)
            elif name == "bing":
                from translation.engines.bing_engine import BingEngine

                return BingEngine(target_lang=self.target_lang, proxy=self.proxy)
            elif name == "libre":
                from translation.engines.libre_engine import LibreEngine

                return LibreEngine(target_lang=self.target_lang, proxy=self.proxy)
            elif name == "argos":
                from translation.engines.argos_engine import ArgosEngine

                return ArgosEngine(target_lang=self.target_lang, proxy=self.proxy)
            elif name == "deeplx":
                from translation.engines.deeplx_engine import DeepLXEngine

                return DeepLXEngine(target_lang=self.target_lang, proxy=self.proxy)
            elif name == "translators":
                from translation.engines.translators_engine import TranslatorsEngine

                return TranslatorsEngine(target_lang=self.target_lang, proxy=self.proxy)
        except Exception as e:
            error_msg = f"Не удалось создать движок {name}: {e}"
            self._error_log.append(error_msg)
            # ✅ ИСПРАВЛЕНО: Ротация error_log для предотвращения утечки памяти
            if len(self._error_log) > self._max_error_log:
                self._error_log = self._error_log[-self._max_error_log // 2 :]
            return None

    def _get_sorted_engines(self) -> list[TranslationEngine]:
        """
        Возвращает движки, отсортированные по успешности.

        Если smart_routing включён, сначала идут движки с наибольшим % успеха.
        """
        if not self.smart_routing:
            return self.engines

        def success_rate(engine):
            name = engine.name
            total = self._total_attempts.get(name, 0)
            if total == 0:
                return 1.0  # Новые движки в начале
            return self._success_counts.get(name, 0) / total

        return sorted(self.engines, key=success_rate, reverse=True)

    def translate(self, text: str) -> str | None:
        """
        Переводит текст с автоматическим fallback и умной ротацией.

        Пробует каждый движок по очереди, начиная с наиболее успешного.

        Args:
            text: Текст для перевода

        Returns:
            Переведённый текст или None
        """
        if not self.engines:
            return None

        # ✅ Умная сортировка по успешности
        sorted_engines = self._get_sorted_engines()

        for retry in range(self.max_retries):
            for engine in sorted_engines:
                if not engine.is_available():
                    continue

                # Обновляем статистику
                self._total_attempts[engine.name] = self._total_attempts.get(engine.name, 0) + 1

                try:
                    result = engine.translate(text)
                    if result:
                        # Запоминаем успешный движок
                        self._success_counts[engine.name] = (
                            self._success_counts.get(engine.name, 0) + 1
                        )
                        self._current_engine_index = self.engines.index(engine)
                        engine.reset_error_count()
                        return result
                except Exception as e:
                    engine.increment_error_count()
                    error_msg = f"Ошибка {engine.name}: {e}"
                    self._error_log.append(error_msg)
                    # ✅ ИСПРАВЛЕНО: Ротация error_log для предотвращения утечки памяти
                    if len(self._error_log) > self._max_error_log:
                        self._error_log = self._error_log[-self._max_error_log // 2 :]

                # Пауза перед следующей попыткой
                if self.retry_delay > 0:
                    time.sleep(self.retry_delay)

        return None

    def translate_batch(self, texts: list[str]) -> list[str | None]:
        """
        Переводит список текстов.

        Args:
            texts: Список текстов для перевода

        Returns:
            Список переведённых текстов
        """
        results = []
        for text in texts:
            result = self.translate(text)
            results.append(result if result else text)  # fallback на оригинал
        return results

    @property
    def available_engines(self) -> list[str]:
        """Возвращает список доступных движков."""
        return [e.name for e in self.engines if e.is_available()]

    @property
    def current_engine(self) -> str | None:
        """Название текущего движка."""
        if self.engines:
            return self.engines[self._current_engine_index].name
        return None

    @property
    def error_log(self) -> list[str]:
        """Журнал ошибок."""
        return self._error_log.copy()

    def clear_error_log(self):
        """Очищает журнал ошибок."""
        self._error_log.clear()

    def add_engine(self, name: str):
        """Добавляет новый движок в цепочку."""
        engine = self._create_engine(name)
        if engine:
            self.engines.append(engine)

    def remove_engine(self, name: str):
        """Удаляет движок из цепочки."""
        self.engines = [e for e in self.engines if e.name.lower() != name.lower()]

    def get_stats(self) -> dict:
        """
        Возвращает статистику по движкам.

        Returns:
            Словарь со статистикой
        """
        stats = {}
        for engine in self.engines:
            name = engine.name
            stats[name] = {
                "available": engine.is_available(),
                "errors": engine.error_count,
                "success_count": self._success_counts.get(name, 0),
                "total_attempts": self._total_attempts.get(name, 0),
                "success_rate": self._get_success_rate(name),
            }
        return stats

    def _get_success_rate(self, engine_name: str) -> float:
        """Возвращает процент успешных переводов для движка."""
        total = self._total_attempts.get(engine_name, 0)
        if total == 0:
            return 0.0
        success = self._success_counts.get(engine_name, 0)
        return (success / total) * 100

    def reset_routing_stats(self):
        """Сбрасывает статистику маршрутизации."""
        for name in self._success_counts:
            self._success_counts[name] = 0
        for name in self._total_attempts:
            self._total_attempts[name] = 0

    def set_smart_routing(self, enabled: bool):
        """Включает/отключает умную маршрутизацию."""
        self.smart_routing = enabled
