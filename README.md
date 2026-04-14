# 🌍 RimWorld Translator Grabber

**Автоматизированный инструмент для перевода и управления модами RimWorld**

![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

---

## 📖 Описание

RimWorld Translator Grabber — мощный инструмент для автоматизации перевода модов RimWorld на различные языки. Поддерживает 8+ движков перевода, интеллектуальную маршрутизацию, кэширование, глоссарии и полноценный редактор переводов.

---

## ✨ Возможности

### 🔄 Перевод
- ✅ **8+ движков перевода**: Google Translate, MyMemory, DeepL, Bing, DeepLX, Translators, LibreTranslate, Argos Translate
- ✅ **Fallback-цепочка**: Автоматическое переключение на следующий движок при ошибке
- ✅ **Умная маршрутизация**: Автоприоритизация движков по успешности переводов
- ✅ **Кэширование**: In-memory кэш с TTL для ускорения повторных переводов
- ✅ **База переводов**: SQLite для хранения уже переведённых текстов
- ✅ **Глоссарий**: Пользовательские словари для специфичных терминов
- ✅ **Умное разбиение**: Автоматическое разбиение длинных текстов на чанки
- ✅ **Rate Limiting**: Защита от бана по IP

### 🎨 Интерфейс
- ✅ **Современный GUI**: ttkbootstrap с поддержкой тем
- ✅ **Многоязычность**: Интерфейс на 5+ языках
- ✅ **Визуальный редактор**: Редактирование переводов с подсветкой синтаксиса
- ✅ **Дерево модов**: Удобная навигация по модам с фильтрацией
- ✅ **Статус-бар**: Подробная информация о процессе перевода с тултипами

### 🛠️ Инструменты
- ✅ **Верификация**: Проверка качества перевода (пакетный вывод без подвисаний)
- ✅ **Поиск дубликатов**: Обнаружение повторяющихся строк с контекстным меню
- ✅ **Фильтры**: Гибкая фильтрация по тегам, статусам, языкам (повторное применение без потери данных)
- ✅ **Зависимости**: Проверка зависимостей модов
- ✅ **Целостность**: Проверка файлов на ошибки (отдельное окно результатов)
- ✅ **Редактор переводов**: 
  - Загрузка отдельных XML файлов ИЛИ целых папок Keyed
  - Сравнение с оригиналом (Diff) — посимвольные изменения
  - Глоссарий терминов
  - История версий файлов
  - Подсказки и проверка орфографии
  - Drag & Drop файлов
- ✅ **Экспорт отчётов**: TXT, JSON, CSV формат

---

## 🚀 Установка

### Требования
- Python 3.14+
- Windows 10/11

### Шаги установки

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/yourusername/rimworld-translator-grabber.git
cd rimworld-translator-grabber
```

2. **Создайте виртуальное окружение:**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

4. **Запустите приложение:**
```bash
# GUI (рекомендуется)
python run_gui.py

# Или через батник
run_gui.bat

# CLI (командная строка)
python main.py <путь_к_моду>
```

---

## 📚 Использование

### Базовый перевод

```python
from translation.translator import AutoTranslator

# Создаём переводчик
translator = AutoTranslator(
    enabled=True,
    source_lang="English",
    target_lang="Russian",
    engine_names=["google", "deepl", "bing"],
)

# Переводим текст
result = translator.translate("Hello, world!")
print(result)  # Привет, мир!
```

### Пакетный перевод

```python
texts = [
    "Hello, world!",
    "Welcome to RimWorld",
    "New colony established",
]

results = translator.translate_batch(texts)
for original, translated in zip(texts, results):
    print(f"{original} -> {translated}")
```

### Использование глоссария

```python
from translation.glossary import Glossary

# Создаём глоссарий
glossary = Glossary("glossary.json")
glossary.add_term("RimWorld", "РимМир")
glossary.add_term("colonist", "колонист")

# Применяем к тексту
result = glossary.apply_to_text("Welcome to RimWorld, colonist!")
```

### Настройка кэша

```python
from translation.translation_cache import TranslationCache

# Создаём кэш с настройками
cache = TranslationCache(
    maxsize=4096,      # Максимум записей
    ttl=7200,          # Время жизни: 2 часа
    enable_stats=True  # Сбор статистики
)

# Статистика
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
```

---

## 🏗️ Архитектура

```
rimworld-translator-grabber/
├── config/                  # Конфигурация
│   ├── config_manager.py    # Управление настройками
│   ├── paths_config.py      # Пути к файлам
│   └── language_constants.py# Константы локализации
├── translation/             # Модуль перевода
│   ├── translator.py        # Основной переводчик
│   ├── translation_cache.py # In-memory кэш
│   ├── constants.py         # Константы
│   ├── glossary.py          # Глоссарий
│   ├── proxy_manager.py     # Управление прокси
│   ├── text_splitter.py     # Разбиение текста
│   └── engines/             # Движки перевода
│       ├── base.py          # Базовый класс
│       ├── fallback_chain.py# Fallback-цепочка
│       ├── google_engine.py # Google Translate
│       ├── deepl_engine.py  # DeepL
│       └── ...
├── gui/                     # Графический интерфейс
│   ├── gui.py               # Главное окно
│   ├── core/                # Ядро UI (tab_manager, ui_builder, menu_builder)
│   ├── tabs/                # Вкладки
│   │   └── editor/          # Модули редактора (перенесены из gui_translation_editor.py)
│   │       ├── editor_toolbar.py      # Панель инструментов
│   │       ├── editor_file_browser.py # Вкладка выбора файлов
│   │       └── editor_dialog.py       # Точка входа в диалог
│   ├── components/          # Компоненты UI (статус-бар, логу и т.д.)
│   ├── handlers/            # Обработчики событий (batch-логирование)
│   ├── dialogs/             # Диалоги (целостность, импорт, глоссарий)
│   ├── help/                # Справка и подсказки (JSON файлы)
│   │   ├── help_loader.py   # Загрузчик справки
│   │   ├── editor_help_ru.json
│   │   ├── editor_help_en.json
│   │   ├── editor_tooltips_ru.json
│   │   └── editor_tooltips_en.json
│   └── styling/             # Темы, шрифты, цвета
├── verification/            # Верификация
├── workers/                 # Фоновые задачи (потокобезопасные)
├── integrity/               # Проверка целостности XML
├── signals/                 # Шина сигналов (упрощена — мёртвый код удалён)
├── utils/                   # Утилиты
│   ├── error_handler.py     # Обработка ошибок
│   ├── ui_helpers.py        # UI хелперы (debounce)
│   └── ...
├── locales/                 # Локализация интерфейса
│   ├── ru.json
│   ├── en.json
│   └── ...
└── docs/                    # Документация
```

---

## 🔧 Конфигурация

### Настройки переводчика

```python
{
    "source_language": "English",
    "target_language": "Russian",
    "translation_mode": "separate",  # separate | inplace
    "engines": ["google", "mymemory", "deepl"],
    "smart_routing": True,
    "rate_limit_delay": 0.5,
    "max_chunk_size": 450,
    "split_long_text": True,
}
```

### Глоссарий (JSON)

```json
{
    "terms": {
        "RimWorld": "РимМир",
        "colonist": "колонист",
        "raid": "рейд"
    }
}
```

---

## 🧪 Тестирование

```bash
# Запустить все тесты
pytest

# Запустить тесты переводчика
python -m translation.translator

# Проверить покрытие
pytest --cov=translation --cov-report=html
```

---

## 📊 Производительность

| Операция | Без кэша | С кэшем | Улучшение |
|----------|----------|---------|-----------|
| Повторный перевод | 500ms | <1ms | **500x** |
| Пакетный (100 строк) | 50s | 5s | **10x** |
| С глоссарием | +10ms | +10ms | — |

---

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

## 📝 История изменений (2026-04)

### v2.0+ — Крупные улучшения

#### 🐛 Исправления
- **Верификация без подвисаний**: Пакетная вставка результатов (`log_batch`) вместо построчной — O(n²) → O(n)
- **Логирование в панель**: `ModsManagerTab` и `TranslationEditorTab` теперь пишут в лог-панель, а не в консоль
- **SignalBus очищен**: Удалён мёртвый код (`_worker_thread`, `_event_queue`, `start/stop`) — никогда не использовался
- **Исправлена геометрия редактора**: Все виджеты в `edit_panel` используют `grid()` вместо смешивания `pack` + `grid`
- **Фильтры без потери данных**: Все вкладки хранят `_all_*_items` для корректного повторного применения фильтров
- **Обработчик ошибок сканирования дубликатов**: Переменная `e` теперь правильно захватывается в except блоке

#### ✨ Новые возможности
- **Контекстное меню дубликатов**: Правый клик → Выбрать/Снять выбор, Открыть папку, Информация
- **Diff в редакторе**: Посимвольное сравнение оригинала и перевода с подсветкой (🟥 Удалено | 🟨 Изменено | 🟩 Добавлено)
- **Обновлённая справка редактора**: Подробное описание всех функций, горячих клавиш и функции Diff
- **Тултипы кнопок редактора**: Diff, Глоссарий и другие кнопки теперь имеют подсказки
- **Расширенное логирование открытия файлов**: Подробные логи для отладки проблем с загрузкой файлов в редакторе
- **Выбор папки в редакторе**: Кнопка 📁 «Открыть папку» для загрузки всех Keyed файлов сразу
- **Окно целостности**: Отдельный диалог с деревом ошибок, фильтрами и экспортом отчётов
- **Тултипы в статус-баре**: Наведение на счётчики показывает что они означают
- **Все моды видны**: Моды без About.xml и с ошибками парсинга теперь отображаются

#### 🏗️ Архитектура
- **Разделение редактора**: `TranslationEditorTab` и `WrappingToolbar` вынесены в `gui/tabs/editor/`
- **Убраны лимиты**: Верификация показывает все результаты (было [:20], [:5], [:3], [:10])
- **Увеличены лимиты**: Дубликаты [:4]→[:20], mass_edit [:50]→[:100], integrity [:80]→[:150]
- **Удалён дублирующийся `__init__`**: `editor_file_browser.py` имел два `__init__` метода
- **Единый стиль фильтров**: Все вкладки используют `_all_*_items` для хранения элементов дерева

---

## 📝 Добавление нового языка интерфейса

См. [locales/README.md](locales/README.md)

### Справка и подсказки

Справка и тултипы хранятся в отдельных JSON файлах в `gui/help/`:

```
gui/help/
├── editor_help_ru.json      # Справка на русском
├── editor_help_en.json      # Справка на английском
├── editor_tooltips_ru.json  # Тултипы на русском
└── editor_tooltips_en.json  # Тултипы на английском
```

Для добавления нового языка:
1. Скопируйте `editor_help_ru.json` → `editor_help_<код>.json`
2. Скопируйте `editor_tooltips_ru.json` → `editor_tooltips_<код>.json`
3. Переведите содержимое
4. Загрузчик автоматически использует fallback на `ru` если файл не найден

Подробности: [gui/help/README.md](gui/help/README.md)

---

## 📄 Лицензия

MIT License — см. файл [LICENSE](LICENSE)

---

## 🙏 Благодарности

- [deep-translator](https://github.com/nidhaloff/deep-translator) — библиотека для перевода
- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) — современный UI
- [RimWorld](https://rimworldgame.com/) — великолепная игра

---



---

*Сделано с ❤️ для сообщества RimWorld*
