# translation/engines/translators_engine.py
"""
Движок на основе библиотеки `translators`.

Библиотека `translators` поддерживает 20+ переводчиков:
- DeepL, Google, Bing, Baidu, Youdao, Yandex, и др.
- Работает через веб-интерфейсы (без API ключей)
- Автоматически обходит некоторые защиты через имитацию браузера

Установка: pip install translators

Используется как запасной вариант при бане основных движков.
"""

try:
    import translators as ts

    _TRANSLATORS_AVAILABLE = True
except ImportError:
    _TRANSLATORS_AVAILABLE = False

from translation.engines.base import TranslationEngine

# Маппинг языковых кодов для translators
LANG_CODE_MAP = {
    "ru": "ru",
    "en": "en",
    "de": "de",
    "fr": "fr",
    "es": "es",
    "zh-CN": "zh-CN",
    "ja": "ja",
    "uk": "uk",
    "pl": "pl",
    "pt": "pt",
    "it": "it",
}

# Доступные суб-движки в порядке приоритета
SUB_ENGINE_PRIORITY = [
    "deepl",
    "google",
    "bing",
    "yandex",
    "baidu",
]


class TranslatorsEngine(TranslationEngine):
    """Движок на базе библиотеки translators (20+ переводчиков)."""

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "ru",
        proxy: dict | None = None,
        sub_engine: str | None = None,
    ):
        super().__init__(source_lang, target_lang, proxy)
        self._sub_engine = sub_engine  # Конкретный суб-движок (deepl, google...)
        self._initialized = _TRANSLATORS_AVAILABLE

    def translate(self, text: str) -> str | None:
        if not self._initialized or not text or text.strip() == "":
            self.increment_error_count()
            return None

        # Пробуем каждый суб-движок по порядку
        engines_to_try = [self._sub_engine] if self._sub_engine else SUB_ENGINE_PRIORITY

        for engine_name in engines_to_try:
            try:
                result = ts.translate_text(
                    text,
                    translator=engine_name,
                    from_language=self.source_lang,
                    to_language=self._get_target_code(),
                    sleep_seconds=0.5,  # Rate limiting встроенный
                )
                if result:
                    self.reset_error_count()
                    return result
            except Exception:
                continue

        self.increment_error_count()
        return None

    def _get_target_code(self) -> str:
        """Получает код целевого языка для translators."""
        return LANG_CODE_MAP.get(self.target_lang, self.target_lang)

    @property
    def name(self) -> str:
        return "translators"

    @property
    def description(self) -> str:
        engine_info = f" (суб-движок: {self._sub_engine})" if self._sub_engine else ""
        return f"Translators{engine_info} (20+ переводчиков)"

    def is_available(self) -> bool:
        return self._initialized
