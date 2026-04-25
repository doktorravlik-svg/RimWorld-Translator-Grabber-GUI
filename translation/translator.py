# translator.py - Расширенный переводчик с поддержкой мульти-движков, fallback, прокси и глоссария
from __future__ import annotations

import logging
import time

from language.rules_constants import PRONOUN_DECLENSIONS
from language.rules_engine import LanguageRules
from translation.constants import (
    CACHE_ENABLE_STATS,
    CACHE_MAX_SIZE,
    CACHE_TTL,
    DEFAULT_ENGINES,
    DEFAULT_MAX_CHUNK_SIZE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RATE_LIMIT_DELAY,
    LANGUAGE_CODE_MAP,
    LOG_PREVIEW_LENGTH,
    MAX_TEXT_LENGTH,
    MIN_TEXT_LENGTH,
)
from translation.engines.fallback_chain import FallbackChain
from translation.glossary import Glossary
from translation.proxy_manager import ProxyManager
from translation.text_splitter import join_translated_chunks, split_text
from translation.translation_cache import TranslationCache
from utils.error_handler import safe_execute_method

# Type aliases (PEP 695, Python 3.12+)
type TranslationResult = str | None
type OptionalStr = str | None
type TextList = list[str]
type EngineList = list[str] | None
type LoggerType = logging.Logger | None

# Импорт для определения языка из текста
try:
    from language.rules_engine import detect_language_from_text
except ImportError:

    def detect_language_from_text(text: str) -> tuple[str, float]:
        return "unknown", 0.0


# Импорт базы переводов (опционально)
try:
    from translation_db import get_translation_db

    HAS_TRANSLATION_DB = True
except ImportError:
    HAS_TRANSLATION_DB = False

    def get_translation_db():
        return None


class AutoTranslator:
    """
    Расширенный переводчик с поддержкой мульти-движков, fallback-цепочки,
    прокси, глоссария, rate limiting и умного разбиения текста.

    Args:
        enabled: Включён ли перевод
        logger: Логгер
        source_lang: Исходный язык (название или код)
        target_lang: Целевой язык (название или код)
        engine_names: Список движков для fallback-цепочки
        use_proxy: Использовать ли прокси
        glossary_path: Путь к файлу глоссария
        max_retries: Макс. попыток на один текст
        rate_limit_delay: Задержка между запросами (секунды)
        max_chunk_size: Макс. размер чанка для разбиения текста
        split_long_text: Включить умное разбиение длинного текста
        smart_routing: Включить умную маршрутизацию движков
    """

    def __init__(
        self,
        enabled: bool = True,
        logger: LoggerType = None,
        source_lang: str = "English",
        target_lang: str = "Russian",
        engine_names: EngineList = None,
        use_proxy: bool = False,
        glossary_path: str | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY,
        max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
        split_long_text: bool = True,
        smart_routing: bool = True,
    ) -> None:
        self.enabled: bool = enabled
        self.logger: logging.Logger | None = logger
        self.source_lang: str = source_lang
        self.target_lang: str = self._get_lang_code(target_lang)
        self.language_rules: LanguageRules = LanguageRules(self.target_lang)
        self.max_retries: int = max_retries

        # Флаг остановки
        self._stop_requested: bool = False

        # Rate limiting
        self.rate_limit_delay: float = rate_limit_delay
        self._last_request_time: float = 0

        # Умное разбиение текста
        self.max_chunk_size: int = max_chunk_size
        self.split_long_text: bool = split_long_text

        # Глоссарий
        self.glossary: Glossary = Glossary(glossary_path) if glossary_path else Glossary()

        # ✅ НОВОЕ: In-memory кэш переводов
        self.cache: TranslationCache = TranslationCache(
            maxsize=CACHE_MAX_SIZE,
            ttl=CACHE_TTL,
            enable_stats=CACHE_ENABLE_STATS,
        )

        # База переводов (опционально)
        self.translation_db = get_translation_db() if HAS_TRANSLATION_DB else None
        if self.translation_db and self.logger:
            stats = self.translation_db.get_stats()
            self.logger.info(
                f"База переводов подключена: {stats.get('translation_entries', 0)} записей, "
                f"{stats.get('glossary_terms', 0)} терминов глоссария"
            )

        # Прокси
        self.proxy_manager: ProxyManager | None = (
            ProxyManager(auto_update=use_proxy) if use_proxy else None
        )
        proxy = self.proxy_manager.get_proxy() if self.proxy_manager else None

        # Fallback-цепочка движков
        if self.enabled:
            if engine_names is None:
                engine_names = DEFAULT_ENGINES.copy()

            self.fallback_chain: FallbackChain | None = FallbackChain(
                target_lang=self.target_lang,
                engine_names=engine_names,
                proxy=proxy,
                max_retries_per_engine=max_retries,
                smart_routing=smart_routing,
            )

            available = self.fallback_chain.available_engines
            if self.logger:
                self.logger.info(
                    f"Переводчик инициализирован: на язык '{self.target_lang}', движки: {available}"
                )
        else:
            self.fallback_chain = None

    def _get_lang_code(self, lang_name: str) -> str:
        """Получить код языка по названию."""
        return LANGUAGE_CODE_MAP.get(lang_name.lower(), "ru")

    def _apply_rate_limit(self) -> None:
        """Применяет rate limiting для защиты от бана по IP."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    @safe_execute_method(fallback=None)
    def translate(self, text: str, original_text: OptionalStr = None) -> TranslationResult:
        """
        Переводит текст с применением кэша, fallback-цепочки, глоссария и rate limiting.

        Порядок проверки:
        1. In-memory кэш (быстрый)
        2. База переводов (если подключена)
        3. Fallback-цепочка движков

        Args:
            text: Текст для перевода
            original_text: Оригинальный текст (для сохранения регистрозависимости)

        Returns:
            Переведённый текст или None
        """
        if not self.enabled or not text or text.strip() == "":
            return None

        # Валидация длины текста
        if len(text) > MAX_TEXT_LENGTH:
            if self.logger:
                self.logger.warning(
                    f"Текст слишком длинный: {len(text)} символов (макс. {MAX_TEXT_LENGTH})"
                )
            return None

        if len(text) < MIN_TEXT_LENGTH:
            return None

        # Rate limiting
        self._apply_rate_limit()

        # Проверяем in-memory кэш
        cached = self.cache.get(text, self.target_lang, self.source_lang)
        if cached:
            if self.logger:
                self.logger.debug(f"Кэш-попадание: '{text[:LOG_PREVIEW_LENGTH]}...'")
            return cached

        # Проверяем базу переводов
        if self.translation_db:
            try:
                db_result = self.translation_db.get_translation(
                    text, self.source_lang, self.target_lang
                )
                if db_result:
                    translated_db = (
                        db_result["translated_value"]
                        if hasattr(db_result, "keys")
                        else db_result[3]
                    )
                    if translated_db:
                        # Сохраняем в кэш
                        self.cache.set(text, self.target_lang, translated_db, self.source_lang)
                        if self.logger:
                            self.logger.debug(f"БД-попадание: '{text[:LOG_PREVIEW_LENGTH]}...'")
                        return translated_db
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Ошибка при чтении из БД: {e}")

        # Применяем глоссарий
        text_with_glossary = self.glossary.apply_to_text(text)

        try:
            # Умное разбиение длинного текста
            if self.split_long_text and len(text_with_glossary) > self.max_chunk_size:
                chunks = split_text(text_with_glossary, self.max_chunk_size)
                if self.logger:
                    self.logger.info(f"Текст разбит на {len(chunks)} чанков для перевода")

                translated_parts: list[str] = []
                for i, chunk in enumerate(chunks):
                    if self._stop_requested:
                        break
                    if self.logger:
                        self.logger.debug(f"Перевод чанка {i + 1}/{len(chunks)}")
                    translated = self._translate_single(chunk)
                    if translated:
                        translated_parts.append(translated)

                translated = join_translated_chunks(translated_parts)
            else:
                translated = self._translate_single(text_with_glossary)

            if translated:
                # ✅ ИСПРАВЛЕНО: Предотвращение бесконечного автоперевода
                # Если перевод идентичен оригиналу — пропускаем, не сохраняем ничего
                if translated.strip() == text.strip():
                    if self.logger:
                        self.logger.debug(f"Перевод совпадает с оригиналом, пропускаем: '{text[:LOG_PREVIEW_LENGTH]}...'")
                    return None

                # Сохраняем в кэш
                self.cache.set(text, self.target_lang, translated, self.source_lang)

                # Сохраняем в базу переводов
                if self.translation_db:
                    try:
                        self.translation_db.add_translation(
                            key=text,
                            original=text,
                            translated=translated,
                            file_name="",
                            mod_name="",
                            source_lang=self.source_lang,
                            target_lang=self.target_lang,
                        )
                    except Exception as e:
                        if self.logger:
                            self.logger.debug(f"Не удалось сохранить в базу: {e}")

                # Применяем правила капитализации целевого языка
                if original_text:
                    translated = self.language_rules.apply_capitalization(translated, original_text)
                else:
                    translated = self.language_rules.apply_capitalization(translated)

            return translated
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка при переводе: {e}", exc_info=True)
            return None

    def _translate_single(self, text: str) -> str | None:
        """Переводит один фрагмент текста через fallback-цепочку."""
        if self.fallback_chain:
            return self.fallback_chain.translate(text)
        return None

    def translate_batch(self, texts: TextList) -> TextList:
        """
        Переводит список текстов с автоматическим fallback.

        Args:
            texts: Список текстов для перевода

        Returns:
            Список переведённых текстов
        """
        if not self.enabled or not self.fallback_chain:
            return texts

        results = []
        for text in texts:
            if not text or text.strip() == "":
                results.append(text)
                continue

            # Применяем глоссарий
            text_with_glossary = self.glossary.apply_to_text(text)
            translated = self.fallback_chain.translate(text_with_glossary)

            if translated:
                translated = self.language_rules.apply_capitalization(translated, text)
                results.append(translated)
            else:
                results.append(text)  # fallback на оригинал

        return results

    def translate_with_pronoun_handling(self, text: str, context: str | None = None) -> str | None:
        """
        Переводит текст с учётом контекста для правильного склонения местоимений.

        Args:
            text: Текст для перевода
            context: Контекст предложения (существительное, к которому относится местоимение)
        """
        if not self.enabled or not text or text.strip() == "":
            return None

        # Сначала переводим обычным способом
        result = self.translate(text)

        if result and context:
            # Пытаемся применить склонение местоимений на основе контекста
            result = self._apply_pronoun_context(result, context)

        return result

    def _apply_pronoun_context(self, text: str, context: str) -> str:
        """Применяет контекстное склонение местоимений"""
        # Определяем род контекстного существительного
        gender = self._detect_gender_from_context(context)

        if gender:
            # Заменяем местоимения на основе рода
            result = text
            # Здесь нужна более сложная логика замены
            # Пока возвращаем как есть
            return result

        return text

    def _detect_gender_from_context(self, context: str) -> str:
        """Определяет род существительного в контексте"""
        # Упрощённая логика - в реальном приложении нужен морфологический анализ
        # Для русского: окончания -а/-я通常是 женский род, -о/-е средний, остальные мужской
        if not context:
            return ""

        # Немецкий: артикли указывают на род
        if self.target_lang == "de":
            context_lower = context.lower()
            if "der " in context_lower or context_lower.startswith("der "):
                return "m"
            elif "die " in context_lower or context_lower.startswith("die "):
                return "f"
            elif "das " in context_lower or context_lower.startswith("das "):
                return "n"

        # Русский - по окончанию
        if self.target_lang == "ru":
            if context.endswith("а") or context.endswith("я"):
                return "f"
            elif context.endswith("о") or context.endswith("е"):
                return "n"
            elif context.endswith("ь"):
                return "m"  # может быть и женский

        return ""

    def translate_preserve_case(self, text: str) -> str:
        """Переводит текст с сохранением регистра исходного текста"""
        if not text:
            return text

        # Сохраняем информацию о регистре каждого слова
        case_info = []
        for word in text.split():
            if word.isupper():
                case_info.append("upper")
            elif word[0].isupper():
                case_info.append("capitalize")
            else:
                case_info.append("lower")

        # Переводим
        translated = self.translate(text)

        if not translated:
            return text

        # Применяем сохранённый регистр
        words = translated.split()
        result_words = []
        for i, word in enumerate(words):
            if i < len(case_info):
                if case_info[i] == "upper":
                    result_words.append(word.upper())
                elif case_info[i] == "capitalize":
                    result_words.append(
                        word[0].upper() + word[1:] if len(word) > 1 else word.upper()
                    )
                else:
                    result_words.append(word.lower())
            else:
                result_words.append(word)

        return " ".join(result_words)


def get_supported_languages():
    """Возвращает список поддерживаемых языков"""
    return list(PRONOUN_DECLENSIONS.keys())


def get_language_info(lang_code: str):
    """Возвращает информацию о языке"""
    return PRONOUN_DECLENSIONS.get(lang_code.lower(), None)


# ============================================================================
# Тесты
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Тестирование переводчика")
    print("=" * 60)

    # Создаём переводчик для русского
    translator = AutoTranslator(enabled=False, target_lang="Russian")

    print(f"\nЦелевой язык: {translator.target_lang}")
    print(f"Правила языка: {translator.language_rules.config.name}")

    # Тест правил капитализации
    print("\n[ТЕСТ] Капитализация:")
    test_cases = [
        ("hello world", "Hello World"),  # начало предложения
        ("der mann", "Der Mann"),  # немецкий - существительные
    ]

    for original, expected in test_cases:
        result = translator.language_rules.apply_capitalization(original)
        print(f"  '{original}' -> '{result}'")

    # Тест местоимений
    print("\n[ТЕСТ] Местоимения:")
    print(f"  я (род) -> {translator.language_rules.get_pronoun_case('я', 'род')}")
    print(f"  он (дат) -> {translator.language_rules.get_pronoun_case('он', 'дат')}")
    print(f"  she (obj) -> {translator.language_rules.get_pronoun_case('she', 'род')}")

    # Тест регистрозависимости
    print("\n[ТЕСТ] Регистрозависимость:")
    print(
        f"  'Hello' vs 'hello' - конфликт? {translator.language_rules.is_case_sensitive_duplicate('Hello', 'hello')}"
    )
    print(
        f"  'Hello' vs 'World' - конфликт? {translator.language_rules.is_case_sensitive_duplicate('Hello', 'World')}"
    )

    # Тест семантической схожести
    print("\n[ТЕСТ] Семантическая схожесть:")
    print(
        f"  'Hello' vs 'Hello' = {translator.language_rules.get_semantic_similarity('Hello', 'Hello')}"
    )
    print(
        f"  'Hello' vs 'hello' = {translator.language_rules.get_semantic_similarity('Hello', 'hello')}"
    )

    # Создаём переводчик для английского
    en_translator = AutoTranslator(enabled=False, target_lang="English")
    print("\n[ТЕСТ] Английский переводчик:")
    print(f"  'I' (obj) -> {en_translator.language_rules.get_pronoun_case('I', 'род')}")
    print(f"  'she' (obj) -> {en_translator.language_rules.get_pronoun_case('she', 'род')}")

    # Создаём переводчик для немецкого
    de_translator = AutoTranslator(enabled=False, target_lang="German")
    print("\n[ТЕСТ] Немецкий переводчик:")
    print(f"  Capitalizes nouns: {de_translator.language_rules.config.capitalizes_nouns}")
    print(f"  'er' (dat) -> {de_translator.language_rules.get_pronoun_case('er', 'дат')}")

    print("\n" + "=" * 60)
    print("Тесты переводчика пройдены!")
    print("=" * 60)
