# translation/text_splitter.py
"""
Умное разбиение текста на части для перевода.

Разбивает текст по границам предложений, сохраняя контекст
и не превышая лимит символов для API переводчиков.
"""

import re
from typing import Optional


def split_text(text: str, max_chars: int = 450) -> list[str]:
    """
    Разбивает текст на части по точкам, не превышая лимит символов.

    Алгоритм:
    1. Разбивает текст на предложения по знакам препинания (.!?)
    2. Объединяет предложения в чанки до max_chars символов
    3. Если одно предложение длиннее max_chars — разбивает по пробелам

    Args:
        text: Исходный текст
        max_chars: Максимальная длина чанка (по умолчанию 450)

    Returns:
        Список текстовых чанков
    """
    if not text or len(text) <= max_chars:
        return [text] if text else []

    # Разбиваем по границам предложений
    # (?<=[.!?])\s+ — ищем пробелы после .!?
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Если предложение само по себе длиннее лимита
        if len(sentence) > max_chars:
            # Сохраняем текущий чанк
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            # Разбиваем длинное предложение по пробелам
            sub_chunks = _split_long_sentence(sentence, max_chars)
            chunks.extend(sub_chunks)
            continue

        # Пробуем добавить предложение в текущий чанк
        if current_chunk:
            test_chunk = current_chunk + " " + sentence
        else:
            test_chunk = sentence

        if len(test_chunk) <= max_chars:
            current_chunk = test_chunk
        else:
            # Сохраняем текущий чанк и начинаем новый
            chunks.append(current_chunk.strip())
            current_chunk = sentence

    # Добавляем последний чанк
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def _split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    """Разбивает длинное предложение по пробелам или словам."""
    chunks = []
    current = ""

    # Пробуем разбить по пробелам
    words = sentence.split()

    for word in words:
        if current:
            test = current + " " + word
        else:
            test = word

        if len(test) <= max_chars:
            current = test
        else:
            if current:
                chunks.append(current)
            # Если слово само длиннее лимита — режем жёстко
            if len(word) > max_chars:
                chunks.extend(_split_word_hard(word, max_chars))
                current = ""
            else:
                current = word

    if current:
        chunks.append(current)

    return chunks


def _split_word_hard(word: str, max_chars: int) -> list[str]:
    """Жёсткое разбиение длинного слова по символам."""
    return [word[i:i + max_chars] for i in range(0, len(word), max_chars)]


def join_translated_chunks(translated_chunks: list[Optional[str]]) -> str:
    """
    Объединяет переведённые чанки обратно в один текст.

    Args:
        translated_chunks: Список переведённых чанков (может быть None)

    Returns:
        Объединённый текст
    """
    parts = []
    for chunk in translated_chunks:
        if chunk is not None:
            parts.append(chunk)
    return " ".join(parts)


def split_text_for_translation(
    text: str,
    max_chars: int = 450,
    join_after: bool = True,
) -> tuple[list[str], bool]:
    """
    Универсальная функция разбиения текста для перевода.

    Args:
        text: Исходный текст
        max_chars: Максимальная длина чанка
        join_after: Нужно ли объединять после перевода

    Returns:
        Кортеж (список чанков, флаг что текст был разбит)
    """
    original_length = len(text)
    chunks = split_text(text, max_chars)
    was_split = len(chunks) > 1

    return chunks, was_split
