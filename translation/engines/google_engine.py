# translation/engines/google_engine.py
"""
Движок Google Translate.

Использует deep_translator.GoogleTranslator для перевода.
Самый стабильный бесплатный движок.
"""

try:
    from deep_translator import GoogleTranslator

    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False

from translation.engines.base import TranslationEngine


class GoogleEngine(TranslationEngine):
    """Движок Google Translate."""

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "ru",
        proxy: dict | None = None,
    ):
        super().__init__(source_lang, target_lang, proxy)
        self._translator = None

        if _GOOGLE_AVAILABLE:
            try:
                self._translator = GoogleTranslator(
                    source="auto",
                    target=self.target_lang,
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
