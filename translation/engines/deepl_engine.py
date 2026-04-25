# translation/engines/deepl_engine.py
"""
Движок DeepL (через веб-интерфейс, без API ключа).

Использует deep_translator.DeepL для перевода через веб-интерфейс.
Бесплатно, но с лимитами и возможными блокировками.
"""

from typing import Optional

try:
    from deep_translator import DeepL

    _DEEPL_AVAILABLE = True
except ImportError:
    _DEEPL_AVAILABLE = False

from translation.engines.base import TranslationEngine


class DeepLEngine(TranslationEngine):
    """Движок DeepL через веб-интерфейс."""

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "ru",
        proxy: Optional[dict] = None,
    ):
        super().__init__(source_lang, target_lang, proxy)
        self._translator = None

        if _DEEPL_AVAILABLE:
            try:
                # DeepL требует конкретные коды языков
                source = "auto" if self.source_lang == "auto" else self.source_lang
                self._translator = DeepL(
                    source=source,
                    target=self.target_lang,
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
