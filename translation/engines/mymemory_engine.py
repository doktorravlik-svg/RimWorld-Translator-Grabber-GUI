# translation/engines/mymemory_engine.py
"""
Движок MyMemory Translation.

Бесплатный переводчик с большим словарным запасом.
Часто использует движок DeepL внутри.
"""

from typing import Optional

try:
    from deep_translator import MyMemoryTranslator

    _MYMEMORY_AVAILABLE = True
except ImportError:
    _MYMEMORY_AVAILABLE = False

from translation.engines.base import TranslationEngine


class MyMemoryEngine(TranslationEngine):
    """Движок MyMemory Translator."""

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "ru",
        proxy: Optional[dict] = None,
    ):
        super().__init__(source_lang, target_lang, proxy)
        self._translator = None

        if _MYMEMORY_AVAILABLE:
            try:
                self._translator = MyMemoryTranslator(
                    source=self.source_lang,
                    target=self.target_lang,
                    proxies=self.proxy,
                )
                self._initialized = True
            except Exception:
                self._initialized = False

    def translate(self, text: str) -> Optional[str]:
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
