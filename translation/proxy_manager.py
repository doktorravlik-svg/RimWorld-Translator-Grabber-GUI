# translation/proxy_manager.py
"""
Менеджер прокси для обхода блокировок.

Автоматически парсит свежие прокси из открытых источников,
проверяет их работоспособность и ротирует при ошибках.
"""

import random
import time
from typing import Any

try:
    import requests

    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


class ProxyManager:
    """
    Менеджер прокси с авто-парсингом и ротацией.

    Args:
        auto_update: Автоматически обновлять список прокси
        max_proxies: Максимальное количество прокси в пуле
        timeout: Таймаут проверки прокси (секунды)
    """

    # Источники бесплатных прокси
    PROXY_SOURCES = [
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&timeout=7000&country=all&anonymity=all",
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all",
    ]

    def __init__(
        self,
        auto_update: bool = True,
        max_proxies: int = 100,
        timeout: int = 10,
    ):
        self.max_proxies = max_proxies
        self.timeout = timeout
        self._proxies: list[str] = []
        self._last_update: float = 0
        self._update_interval: int = 300  # 5 минут
        self._blacklist: set[str] = set()

        if auto_update and _REQUESTS_AVAILABLE:
            self.update_proxies()

    def update_proxies(self) -> int:
        """
        Обновляет список прокси из открытых источников.

        Returns:
            Количество загруженных прокси
        """
        if not _REQUESTS_AVAILABLE:
            return 0

        new_proxies = []

        for source_url in self.PROXY_SOURCES:
            try:
                response = requests.get(source_url, timeout=self.timeout)
                if response.status_code == 200:
                    # Разные форматы ответов
                    lines = response.text.strip().split("\n")
                    for line in lines:
                        line = line.strip()
                        if self._is_valid_proxy(line):
                            new_proxies.append(line)
            except Exception:
                continue

        # Фильтруем чёрный список
        self._proxies = [p for p in new_proxies[: self.max_proxies] if p not in self._blacklist]
        self._last_update = time.time()

        return len(self._proxies)

    def get_proxy(self) -> dict | None:
        """
        Возвращает случайный прокси в формате для requests.

        Returns:
            Словарь {"http": "...", "https": "..."} или None
        """
        if not self._proxies:
            return None

        proxy = random.choice(self._proxies)
        return {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}",
        }

    def blacklist_proxy(self, proxy: str) -> None:
        """Добавляет прокси в чёрный список.

        Args:
            proxy: Строка прокси для добавления в чёрный список
        """
        clean_proxy = proxy.replace("http://", "").replace("https://", "")
        self._blacklist.add(clean_proxy)
        self._proxies = [p for p in self._proxies if p != clean_proxy]

    def add_proxy(self, proxy: str) -> None:
        """
        Добавляет прокси вручную.

        Args:
            proxy: Строка прокси для добавления
        """
        clean_proxy = proxy.replace("http://", "").replace("https://", "")
        if self._is_valid_proxy(clean_proxy) and clean_proxy not in self._blacklist:
            self._proxies.append(clean_proxy)

    def remove_proxy(self, proxy: str) -> None:
        """
        Удаляет прокси из пула.

        Args:
            proxy: Строка прокси для удаления
        """
        clean_proxy = proxy.replace("http://", "").replace("https://", "")
        self._proxies = [p for p in self._proxies if p != clean_proxy]

    @property
    def proxy_count(self) -> int:
        """Количество прокси в пуле."""
        return len(self._proxies)

    @property
    def needs_update(self) -> bool:
        """
        Нужно ли обновить список прокси.

        Returns:
            True если прошло больше 5 минут с последнего обновления
        """
        return (time.time() - self._last_update) > self._update_interval

    def _is_valid_proxy(self, proxy: str) -> bool:
        """
        Проверяет формат прокси.

        Args:
            proxy: Строка прокси для проверки (формат ip:port)

        Returns:
            True если прокси валидного формата, False иначе
        """
        if not proxy:
            return False
        # Простая проверка формата ip:port
        parts = proxy.strip().split(":")
        if len(parts) == 2:
            try:
                ip, port = parts
                # Проверяем, что port - число
                int(port)
                # Простая проверка IP
                ip_parts = ip.split(".")
                if len(ip_parts) == 4:
                    return all(p.isdigit() and 0 <= int(p) <= 255 for p in ip_parts)
            except (ValueError, TypeError):
                pass
        return False

    def get_stats(self) -> dict[str, Any]:
        """
        Статистика менеджера прокси.

        Returns:
            Словарь со статистикой, включающий:
                - total_proxies: Количество прокси в пуле
                - blacklisted: Количество заблокированных прокси
                - last_update: Время последнего обновления
                - needs_update: Нужно ли обновить список
        """
        return {
            "total_proxies": len(self._proxies),
            "blacklisted": len(self._blacklist),
            "last_update": self._last_update,
            "needs_update": self.needs_update,
        }
