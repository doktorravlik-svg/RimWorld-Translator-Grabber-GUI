# translation/engines/libre_engine.py
"""
Движок LibreTranslate.

Полностью открытый движок перевода.
Требует запущенный сервер LibreTranslate (локальный или удалённый).
"""

try:
    import requests

    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

from translation.engines.base import TranslationEngine


class LibreEngine(TranslationEngine):
    """
    Движок LibreTranslate.

    Args:
        base_url: URL сервера LibreTranslate (по умолчанию http://localhost:5000)
        api_key: API ключ (для публичных серверов)
    """

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "ru",
        proxy: dict | None = None,
        base_url: str = "http://localhost:5000",
        api_key: str | None = None,
    ):
        super().__init__(source_lang, target_lang, proxy)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

        if _REQUESTS_AVAILABLE:
            try:
                # Проверяем доступность сервера
                response = requests.get(
                    f"{self.base_url}/languages",
                    timeout=5,
                    proxies=self.proxy,
                )
                self._initialized = response.status_code == 200
            except Exception:
                self._initialized = False

    def translate(self, text: str) -> str | None:
        if not self._initialized or not _REQUESTS_AVAILABLE:
            self.increment_error_count()
            return None

        try:
            payload = {
                "q": text,
                "source": "auto",
                "target": self.target_lang,
                "format": "text",
            }
            if self.api_key:
                payload["api_key"] = self.api_key

            response = requests.post(
                f"{self.base_url}/translate",
                json=payload,
                timeout=30,
                proxies=self.proxy,
            )

            if response.status_code == 200:
                self.reset_error_count()
                return response.json().get("translatedText")
            else:
                self.increment_error_count()
                return None
        except Exception:
            self.increment_error_count()
            return None
