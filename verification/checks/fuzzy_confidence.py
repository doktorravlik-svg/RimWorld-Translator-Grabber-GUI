# verification/checks/fuzzy_confidence.py
"""
Анализ уверенности fuzzy-совпадений.
Собирает все теги, которые были сопоставлены через RapidFuzz,
и фильтрует те, у которых score < 85%.

Исправления:
- Добавлен штрафной коэффициент для строк короче 5 символов
- Учет длины строки при расчете уверенности
- Штраф за существенную разницу в длине исходной и целевой строки
"""


from ..checks_base import VerificationCheck
from ..verification_coordinator import CheckResult


class FuzzyConfidenceCheck(VerificationCheck):
    """
    Анализ уверенности fuzzy-совпадений.
    Собирает все теги, которые были сопоставлены через RapidFuzz,
    и фильтрует те, у которых score < 85%.

    Учитывает длину строки: короткие строки (<5 символов) получают
    штраф за высокую вероятность ложноположенных совпадений.

    Дополнительно штрафует совпадения, где исходная и целевая строки
    существенно различаются по длине (>50% разницы), так как после
    очистки тегов/цифр такие строки не должны считаться идентичными.
    """

    # Пороговые значения
    MIN_CONFIDENCE_THRESHOLD = 85.0
    MIN_STRING_LENGTH_FOR_FULL_CONFIDENCE = 5
    SHORT_STRING_PENALTY_FACTOR = 0.7  # Штраф для коротких строк
    MAX_LENGTH_RATIO_DIFF = 0.5  # Макс. допустимая разница в длине (50%)
    LENGTH_DIFF_PENALTY = 20.0  # Штраф в процентах при превышении разницы

    @property
    def name(self) -> str:
        return "fuzzy_confidence"

    @property
    def description(self) -> str:
        return (
            "Оценка уверенности fuzzy-совпадений (порог 85%, с учетом длины строки "
            "и разницы длин исходной/целевой строки)"
        )

    def _calculate_adjusted_confidence(
        self,
        source_length: int,
        target_length: int,
        base_score: float,
    ) -> float:
        """
        Рассчитывает скорректированную уверенность с учётом:
          - длины каждой из сравниваемых строк
          - разницы в длине между строками

        Args:
            source_length: Длина исходной строки
            target_length: Длина целевой (переведённой/очищенной) строки
            base_score: Базовая уверенность от RapidFuzz

        Returns:
            Скорректированная уверенность (0-100)
        """
        adjusted = base_score

        # 1. Штраф за короткую исходную строку
        if source_length < self.MIN_STRING_LENGTH_FOR_FULL_CONFIDENCE:
            length_ratio = source_length / self.MIN_STRING_LENGTH_FOR_FULL_CONFIDENCE
            penalty = (1 - length_ratio) * 30 * (1 - self.SHORT_STRING_PENALTY_FACTOR)
            adjusted -= penalty

        # 2. Штраф за разницу в длине между source и target
        if source_length > 0 and target_length > 0:
            length_diff_ratio = abs(source_length - target_length) / max(source_length, target_length)
            if length_diff_ratio > self.MAX_LENGTH_RATIO_DIFF:
                adjusted -= self.LENGTH_DIFF_PENALTY

        return max(0.0, adjusted)

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        """
        Выполняет проверку уверенности fuzzy-совпадений.

        Требует интеграции со статистикой из per_def_generator.
        В будущем будет анализировать логи и кэш fuzzy-совпадений.
        """
        # Этот чек работает на уровне already-generated DefInjected файлов
        # Он анализирует логи или кэш fuzzy-совпадений (нужен сбор статистики при генерации)
        # Пока вернём info — требуется интеграция с логами или кэшем
        return CheckResult(
            check_name=self.name,
            passed=True,
            severity="info",
            message=(
                "Требует интеграции статистики fuzzy_matches из per_def_generator. "
                f"Порог уверенности: {self.MIN_CONFIDENCE_THRESHOLD}%, "
                f"штраф для строк <5 символов: {30 * (1 - self.SHORT_STRING_PENALTY_FACTOR):.0f}%, "
                f"штраф за разницу длин >{self.MAX_LENGTH_RATIO_DIFF:.0%}: {self.LENGTH_DIFF_PENALTY}%"
            ),
        )
