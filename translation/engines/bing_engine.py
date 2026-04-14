# translation/engines/bing_engine.py
"""
Движок Bing Microsoft Translator.

Хорошая альтернатива Google Translate.
"""

from typing import Optional

try:
    from deep_translator import MicrosoftTranslator

    _BING_AVAILABLE = True
except ImportError:
    _BING_AVAILABLE = False

from translation.engines.base import TranslationEngine


class BingEngine(TranslationEngine):
    """Движок Bing Microsoft Translator."""

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "ru",
        proxy: Optional[dict] = None,
    ):
        super().__init__(source_lang, target_lang, proxy)
        self._translator = None

        if _BING_AVAILABLE:
            try:
                self._translator = MicrosoftTranslator(
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
