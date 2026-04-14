# translation/engines/deeplx_engine.py
"""
Движок DeepLX (локальный прокси-сервер для DeepL).

DeepLX — это open-source проект, который имитирует запросы браузера к DeepL.
Позволяет использовать DeepL без API ключа и обходить региональные блокировки.

Требует запущенный DeepLX сервер на localhost:1188 (по умолчанию).
GitHub: https://github.com/OwO-Network/DeepLX

Для запуска:
  - Docker: docker run -d -p 1188:1188 owenthereal/deeplx
  - Или скачать бинарник с GitHub releases
"""

try:
    import requests

    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

from translation.engines.base import TranslationEngine


class DeepLXEngine(TranslationEngine):
    """Движок DeepL через локальный DeepLX сервер."""

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "ru",
        deeplx_url: str = "http://localhost:1188",
        proxy: dict | None = None,
    ):
        super().__init__(source_lang, target_lang, proxy)
        self.deeplx_url = deeplx_url.rstrip("/")
        self._initialized = False

        if _REQUESTS_AVAILABLE:
            self._initialized = self._check_connection()

    def _check_connection(self) -> bool:
        """Проверяет доступность DeepLX сервера."""
        try:
            resp = requests.get(
                f"{self.deeplx_url}/health",
                timeout=2,
                proxies=self.proxy,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def translate(self, text: str) -> str | None:
        if not self._initialized or not text or text.strip() == "":
            self.increment_error_count()
            return None

        try:
            # DeepLX API формат
            payload = {
                "text": text,
                "source_lang": self.source_lang if self.source_lang != "auto" else "auto",
                "target_lang": self.target_lang.upper(),
            }

            resp = requests.post(
                f"{self.deeplx_url}/translate",
                json=payload,
                timeout=15,
                proxies=self.proxy,
            )

            if resp.status_code == 200:
                data = resp.json()
                result = data.get("data") or data.get("result")
                if result:
                    self.reset_error_count()
                    return result

            self.increment_error_count()
            return None

        except requests.exceptions.Timeout:
            self.increment_error_count()
            return None
        except requests.exceptions.ConnectionError:
            self.increment_error_count()
            return None
        except Exception:
            self.increment_error_count()
            return None

    @property
    def name(self) -> str:
        return "deeplx"

    @property
    def description(self) -> str:
        return "DeepL (через DeepLX локальный сервер)"

    def is_available(self) -> bool:
        return self._initialized and _REQUESTS_AVAILABLE
