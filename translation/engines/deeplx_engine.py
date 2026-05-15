# translation/engines/deeplx_engine.py
"""
Движок DeepLX (локальный прокси-сервер для DeepL).

DeepLX — это open-source проект, который имитирует запросы браузера к DeepL.
Позволяет использовать DeepL без API ключа и обходить региональные блокировки.

Автоматически запускает deeplx_windows_amd64.exe если сервер не доступен.
Расположение .exe: env/deeplx_windows_amd64.exe относительно корня проекта.
"""

import os
import subprocess
import sys
import time

try:
    import requests

    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

import atexit

from translation.engines.base import TranslationEngine


# Путь к исполняемому файлу DeepLX относительно корня проекта
DEEPLX_EXE_RELATIVE_PATH = "env/deeplx_windows_amd64.exe"


class DeepLXEngine(TranslationEngine):
    """Движок DeepL через локальный DeepLX сервер."""

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "ru",
        deeplx_url: str = "http://localhost:1188",
        proxy: dict | None = None,
        auto_start_exe: bool = True,
    ):
        super().__init__(source_lang, target_lang, proxy)
        self.deeplx_url = deeplx_url.rstrip("/")
        self.auto_start_exe = auto_start_exe
        self._process = None  # Ссылка на запущенный процесс
        self._initialized = False
        
        # ✅ РЕГИСТРАЦИЯ ATE XIT: авто-очистка при выходе из программы
        atexit.register(self.stop)
        
        # ✅ Добавляем логирование для отладки
        print(f"[DeepLXEngine] __init__: deeplx_url={self.deeplx_url}, auto_start={auto_start_exe}")
        
        if _REQUESTS_AVAILABLE:
            try:
                self._initialized = self._check_connection()
                print(f"[DeepLXEngine] _check_connection returned: {self._initialized}")
            except Exception as e:
                print(f"[DeepLXEngine] Exception in __init__: {e}")
                self._initialized = False
        else:
            print("[DeepLXEngine] requests not available")

    def _get_exe_path(self) -> str | None:
        """Находит путь к deeplx_windows_amd64.exe."""
        # Получаем корень проекта (где находится gui.py или run_gui.py)
        project_root = os.environ.get("DEEPLX_PROJECT_ROOT")
        if not project_root:
            # Определяем корень проекта автоматически
            current_file = os.path.abspath(__file__)
            # translators/engines/deeplx_engine.py -> project_root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

        exe_path = os.path.join(project_root, DEEPLX_EXE_RELATIVE_PATH)
        if os.path.exists(exe_path):
            return exe_path
        return None

    def _start_exe(self) -> bool:
        """Запускает deeplx_windows_amd64.exe."""
        exe_path = self._get_exe_path()
        if not exe_path:
            return False

        try:
            # Запускаем в фоновом режиме без создания окна консоли
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW

            self._process = subprocess.Popen(
                [exe_path],
                cwd=os.path.dirname(exe_path),
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Ждём пока сервер поднимется (максимум 10 секунд)
            for _ in range(20):
                if self._check_connection():
                    return True
                time.sleep(0.5)

            return False
        except Exception:
            return False

    def _check_connection(self) -> bool:
        """Проверяет доступность DeepLX сервера."""
        if not _REQUESTS_AVAILABLE:
            return False
        try:
            # ✅ ИСПРАВЛЕНО: DeepLX не имеет /health эндпоинта
            # Проверяем через GET запрос к корню или через пробный перевод
            try:
                # Пробуем корень сервера
                resp = requests.get(
                    self.deeplx_url,
                    timeout=2,
                )
                if resp.status_code in (200, 404):  # Сервер отвечает
                    print(f"[DeepLXEngine] Сервер отвечает: status={resp.status_code}")
                    return True
            except Exception:
                pass
            
            # Альтернативно: пробный запрос перевода
            resp = requests.post(
                f"{self.deeplx_url}/translate",
                json={"text": "test", "target_lang": "en"},
                timeout=2,
            )
            # 200, 400 (bad request но сервер жив) или 429 (rate limit) = сервер жив
            if resp.status_code in (200, 400, 429):
                print(f"[DeepLXEngine] Сервер работает: status={resp.status_code}")
                return True
        except requests.exceptions.ConnectionError:
            print(f"[DeepLXEngine] Сервер не доступен по адресу {self.deeplx_url}")
        except Exception as e:
            print(f"[DeepLXEngine] Ошибка проверки соединения: {e}")
        
        # Если не доступен и включён автозапуск — пробуем запустить .exe
        if self.auto_start_exe:
            print("[DeepLXEngine] Попытка запуска deeplx_windows_amd64.exe...")
            return self._start_exe()
        
        return False

    def translate(self, text: str) -> str | None:
        if not self._initialized or not text or text.strip() == "":
            # Пробуем переинициализироваться
            if _REQUESTS_AVAILABLE:
                self._initialized = self._check_connection()
            if not self._initialized:
                self.increment_error_count()
                return None

        try:
            source = self.source_lang if self.source_lang != "auto" else "auto"
            payload = {
                "q": text,
                "source": source,
                "target": self.target_lang,
            }

            resp = requests.post(
                f"{self.deeplx_url}/translate",
                json=payload,
                timeout=15,
                proxies=self.proxy,
            )

            if resp.status_code == 200:
                data = resp.json()
                result = data.get("responseData", {}).get("translatedText")
                if not result:
                    result = data.get("data", {}).get("translations", [{}])[0].get("translatedText")
                if not result:
                    result = data.get("result") or data.get("translatedText")
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

    def stop(self):
        """Останавливает запущенный процесс DeepLX."""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                pass
            self._process = None
