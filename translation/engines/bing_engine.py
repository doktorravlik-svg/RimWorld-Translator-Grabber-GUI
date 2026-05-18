# translation/engines/bing_engine.py
"""
Движок Bing Microsoft Translator.

Хорошая альтернатива Google Translate.
"""

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
        proxy: dict | None = None,
    ):
        super().__init__(source_lang, target_lang, proxy)
        self._translator = None

        if _BING_AVAILABLE:
            try:
                import os
                api_key = os.environ.get("MICROSOFT_API_KEY")
                if not api_key:
                    self._initialized = False
                    return
                self._translator = MicrosoftTranslator(
                    source="auto",
                    target=self.target_lang,
                    api_key=api_key,
                    proxies=self.proxy,
                )
                self._initialized = True
            except Exception:
                self._initialized = False

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
