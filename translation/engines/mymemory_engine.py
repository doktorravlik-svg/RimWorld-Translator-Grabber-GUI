# translation/engines/mymemory_engine.py
"""
Движок MyMemory Translation.

Бесплатный переводчик с большим словарным запасом.
Часто использует движок DeepL внутри.
"""

try:
    from deep_translator import MyMemoryTranslator

    _MYMEMORY_AVAILABLE = True
except ImportError:
    _MYMEMORY_AVAILABLE = False

from translation.engines.base import TranslationEngine
from translation.constants import LANGUAGE_CODE_MAP


class MyMemoryEngine(TranslationEngine):
    """Движок MyMemory Translator."""

    _LANG_MAP = {
        "en": "english",
        "ru": "russian",
        "de": "german",
        "fr": "french",
        "es": "spanish",
        "it": "italian",
        "pt": "portuguese",
        "zh": "chinese simplified",
        "ja": "japanese",
        "ko": "korean",
        "ar": "arabic",
    }

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "ru",
        proxy: dict | None = None,
    ):
        super().__init__(source_lang, target_lang, proxy)
        self._translator = None

        if _MYMEMORY_AVAILABLE:
            try:
                source = self._get_mymemory_lang(self.source_lang)
                target = self._get_mymemory_lang(self.target_lang)
                self._translator = MyMemoryTranslator(
                    source=source,
                    target=target,
                    proxies=self.proxy,
                )
                self._initialized = True
            except Exception:
                self._initialized = False

    def _get_mymemory_lang(self, lang: str) -> str:
        if lang == "auto":
            return "auto"
        return self._LANG_MAP.get(lang, lang)

    def translate(self, text: str) -> str | None:
        if not self._initialized or not self._translator:
            self.increment_error_count()
            return None

        try:
            result = self._translator.translate(text)
            self.reset_error_count()
            return result
        except Exception:
            self.increment_error_count()
            return None
