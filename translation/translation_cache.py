# translation/translation_cache.py
"""
Быстрый in-memory кэш переводов с TTL и ограничением размера.

Используется для ускорения повторных переводов без обращения к БД или API.
"""

from __future__ import annotations

from loguru import logger
import time
import hashlib
from typing import Any
import threading


class CacheEntry:
    """Запись в кэше с метаданными."""
    
    __slots__ = ('value', 'timestamp', 'access_count', 'last_access')
    
    def __init__(self, value: str, timestamp: float | None = None) -> None:
        self.value = value
        self.timestamp = timestamp or time.time()
        self.access_count = 0
        self.last_access = 0.0
    
    def is_expired(self, ttl: float) -> bool:
        """Проверяет, истёк ли срок жизни записи."""
        return (time.time() - self.timestamp) > ttl
    
    def touch(self) -> None:
        """Обновляет время последнего доступа."""
        self.access_count += 1
        self.last_access = time.time()


class TranslationCache:
    """
    In-memory кэш для переводов с TTL и ограничением размера.
    
    Поддерживает:
    - Автоматическую очистку просроченных записей
    - LRU eviction при превышении maxsize
    - Потокобезопасность
    - Статистику использования
    
    Args:
        maxsize: Максимальное количество записей (по умолчанию 2048)
        ttl: Время жизни записи в секундах (по умолчанию 1 час)
        enable_stats: Включить сбор статистики
    
    Example:
        >>> cache = TranslationCache(maxsize=1024, ttl=3600)
        >>> cache.set("Hello", "ru", "Привет")
        >>> cache.get("Hello", "ru")
        'Привет'
    """
    
    def __init__(
        self, 
        maxsize: int = 2048, 
        ttl: float = 3600.0,
        enable_stats: bool = True,
    ) -> None:
        self.maxsize = maxsize
        self.ttl = ttl
        self.enable_stats = enable_stats
        
        # Хранилище: key -> CacheEntry
        self._cache: dict[str, CacheEntry] = {}
        
        # Порядок доступа для LRU
        self._access_order: list[str] = []
        
        # Потокобезопасность
        self._lock = threading.RLock()
        
        # Статистика
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def _make_key(self, text: str, target_lang: str, source_lang: str = "") -> str:
        """Создаёт уникальный ключ кэша."""
        raw_key = f"{source_lang}:{target_lang}:{text}"
        # Для длинных текстов используем хэш
        if len(raw_key) > 200:
            text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:16]
            return f"{source_lang}:{target_lang}:{text_hash}"
        return raw_key
    
    def get(
        self, 
        text: str, 
        target_lang: str, 
        source_lang: str = "",
    ) -> str | None:
        """
        Получает перевод из кэша.
        
        Args:
            text: Оригинальный текст
            target_lang: Целевой язык
            source_lang: Исходный язык (опционально)
        
        Returns:
            Переведённый текст или None
        """
        key = self._make_key(text, target_lang, source_lang)
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                if self.enable_stats:
                    self._misses += 1
                return None
            
            # Проверяем TTL
            if entry.is_expired(self.ttl):
                self._remove(key)
                if self.enable_stats:
                    self._misses += 1
                return None
            
            # Обновляем доступ
            entry.touch()
            self._update_access_order(key)
            
            if self.enable_stats:
                self._hits += 1
            
            return entry.value
    
    def set(
        self, 
        text: str, 
        target_lang: str, 
        translated: str,
        source_lang: str = "",
    ) -> None:
        """
        Сохраняет перевод в кэш.
        
        Args:
            text: Оригинальный текст
            target_lang: Целевой язык
            translated: Переведённый текст
            source_lang: Исходный язык (опционально)
        """
        if not text or not translated:
            return
        
        key = self._make_key(text, target_lang, source_lang)
        
        with self._lock:
            # Если ключ уже существует — обновляем
            if key in self._cache:
                self._cache[key] = CacheEntry(translated)
                self._update_access_order(key)
                return
            
            # Eviction если превышен размер
            while len(self._cache) >= self.maxsize:
                self._evict_lru()
            
            # Добавляем новую запись
            self._cache[key] = CacheEntry(translated)
            self._access_order.append(key)
    
    def clear(self) -> None:
        """Очищает весь кэш."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            if self.enable_stats:
                self._hits = 0
                self._misses = 0
                self._evictions = 0
            logger.info("Кэш переводов очищен")
    
    def cleanup_expired(self) -> int:
        """
        Удаляет просроченные записи.
        
        Returns:
            Количество удалённых записей
        """
        removed = 0
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() 
                if entry.is_expired(self.ttl)
            ]
            for key in expired_keys:
                self._remove(key)
                removed += 1
        
        if removed > 0:
            logger.debug(f"Удалено {removed} просроченных записей из кэша")
        
        return removed
    
    def get_stats(self) -> dict[str, Any]:
        """
        Возвращает статистику кэша.
        
        Returns:
            Словарь со статистикой
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            
            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "evictions": self._evictions,
                "ttl": self.ttl,
            }
    
    def _remove(self, key: str) -> None:
        """Удаляет запись из кэша."""
        self._cache.pop(key, None)
        if key in self._access_order:
            self._access_order.remove(key)
    
    def _evict_lru(self) -> None:
        """Удаляет наименее используемую запись."""
        if not self._access_order:
            return
        
        # Находим LRU запись (первая в списке доступа)
        lru_key = self._access_order.pop(0)
        self._cache.pop(lru_key, None)
        
        if self.enable_stats:
            self._evictions += 1
        
        logger.debug(f"Evicted LRU запись из кэша: {lru_key[:50]}...")
    
    def _update_access_order(self, key: str) -> None:
        """Обновляет порядок доступа (перемещает в конец)."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def __len__(self) -> int:
        """Возвращает количество записей в кэше."""
        return len(self._cache)
    
    def __contains__(self, text: str) -> bool:
        """Проверяет наличие текста в кэше (без учёта языка)."""
        return any(
            text in key 
            for key in self._cache.keys()
        )
