# 📚 Справка и подсказки

Эта директория содержит файлы справки и подсказок для различных вкладок приложения.

## 📁 Структура

```
gui/help/
├── __init__.py                    # Инициализация модуля
├── help_loader.py                 # Загрузчик справки и подсказок
│
├── editor_help_ru.json            # Справка редактора на русском
├── editor_help_ua.json            # Справка редактора на украинском
├── editor_help_en.json            # Справка редактора на английском
├── editor_help_ja.json            # Справка редактора на японском
│
├── editor_tooltips_ru.json        # Тултипы редактора на русском
├── editor_tooltips_ua.json        # Тултипы редактора на украинском
├── editor_tooltips_en.json        # Тултипы редактора на английском
├── editor_tooltips_ja.json        # Тултипы редактора на японском
│
├── duplicates_help_ru.json        # Справка дубликатов на русском
├── duplicates_help_ua.json        # Справка дубликатов на украинском
├── duplicates_help_en.json        # Справка дубликатов на английском
├── duplicates_help_ja.json        # Справка дубликатов на японском
│
├── filters_help_ru.json           # Справка фильтров на русском
├── verification_help_ru.json      # Справка верификации на русском
├── translation_help_ru.json       # Справка перевода на русском
├── dependencies_help_ru.json      # Справка зависимостей на русском
│
└── README.md                      # Документация модуля
```

## 🔧 Использование

### Загрузка справки

```python
from gui.help.help_loader import (
    load_editor_help, format_editor_help_text,
    load_duplicates_help, format_duplicates_help_text,
    load_filters_help, format_filters_help_text,
    load_verification_help, format_verification_help_text,
    load_translation_help, format_translation_help_text,
    load_dependencies_help, format_dependencies_help_text,
    load_editor_tooltips, get_tooltip
)

# Справка редактора
help_data = load_editor_help()
help_text = format_editor_help_text(help_data)

# Справка дубликатов
help_data = load_duplicates_help()
help_text = format_duplicates_help_text(help_data)

# Справка фильтров
help_data = load_filters_help()
help_text = format_filters_help_text(help_data)

# Справка верификации
help_data = load_verification_help()
help_text = format_verification_help_text(help_data)

# Справка перевода
help_data = load_translation_help()
help_text = format_translation_help_text(help_data)

# Справка зависимостей
help_data = load_dependencies_help()
help_text = format_dependencies_help_text(help_data)

# Тултипы
tooltips = load_editor_tooltips()
tip_text = get_tooltip(tooltips, "diff")
```

## 🌍 Поддерживаемые языки

| Вкладка | 🇷🇺 RU | 🇺🇦 UA | 🇬🇧 EN | 🇯🇵 JA |
|---------|-------|-------|-------|-------|
| ✏️ Редактор | ✅ | ✅ | ✅ | ✅ |
| 🔄 Дубликаты | ✅ | ✅ | ✅ | ✅ |
| 📝 Фильтры | ✅ | 🔄 | 🔄 | 🔄 |
| ✅ Верификация | ✅ | 🔄 | 🔄 | 🔄 |
| 🌐 Перевод | ✅ | 🔄 | 🔄 | 🔄 |
| 🔗 Зависимости | ✅ | 🔄 | 🔄 | 🔄 |

✅ — полный перевод | 🔄 — используется fallback на русский

## 🔁 Fallback цепочка

Загрузчик автоматически ищет файлы в следующем порядке:
1. Запрошенный язык (например, `ua`)
2. Украинский (`ua`)
3. Английский (`en`)
4. Русский (`ru`) — финальный fallback

## 📝 Формат справки

```json
{
    "title": "📖 Справка по вкладке",
    "sections": {
        "section_key": {
            "title": "📂 ЗАГОЛОВОК СЕКЦИИ",
            "items": [
                "Пункт 1",
                "Пункт 2"
            ]
        }
    }
}
```

## 📝 Формат тултипов

```json
{
    "key_подсказки": {
        "text": "Краткий текст",
        "detail": "Детальное описание (опционально)"
    }
}
```

Если есть `detail`, тултип объединит `text` и `detail` через `\n`.

## 🌍 Добавление нового языка

### Справка

1. Создайте копию `<вкладка>_help_ru.json` → `<вкладка>_help_<код_языка>.json`
2. Переведите содержимое файлов
3. Загрузчик автоматически использует fallback если файл не найден

### Тултипы

1. Создайте копию `editor_tooltips_ru.json` → `editor_tooltips_<код_языка>.json`
2. Переведите содержимое файлов
3. Загрузчик автоматически использует fallback если файл не найден

## 📊 Статистика

| Тип | Файлов | Секций | Тултипов |
|-----|--------|--------|----------|
| Справка редактора | 4 | 10 × 4 = 40 | — |
| Справка дубликатов | 4 | 8 × 4 = 32 | — |
| Справка фильтров | 1 | 7 | — |
| Справка верификации | 1 | 7 | — |
| Справка перевода | 1 | 7 | — |
| Справка зависимостей | 1 | 6 | — |
| Тултипы редактора | 4 | — | 18 × 4 = 72 |
| **Итого** | **16** | **99** | **72** |
