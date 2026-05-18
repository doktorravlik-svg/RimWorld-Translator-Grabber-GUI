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

# Создать глоссарий (категория определяется автоматически)
glossary = Glossary()
glossary.add("RimWorld", "РимМир", category="auto")
glossary.add("colonist", "колонист", category="auto")

# Или загрузить из JSON-файлов по категориям (создаются автоматически)
# Файлы хранятся в папке config/:
#   - glossary_game.json      (игровые термины)
#   - glossary_seed.json      (базовые термины)
#   - glossary_user.json      (пользовательские термины)
#   - glossary_auto.json      (авто-извлеченные термины)
#   - glossary_general.json  (общие термины)

# Применить к тексту
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
├── collectors/              # Коллекторы данных модов
│   └── collectors.py
├── config/                  # Конфигурация + файлы глоссария
│   ├── config_manager.py
│   ├── paths_config.py
│   ├── language_constants.py
│   ├── glossary_game.json      # Игровые термины (авто-генерация)
│   ├── glossary_seed.json      # Базовые термины (авто-генерация)
│   ├── glossary_user.json      # Пользовательские термины (авто-генерация)
│   ├── glossary_auto.json      # Авто-извлечённые термины (авто-генерация)
│   ├── glossary_general.json  # Общие термины (авто-генерация)
│   ├── grabber_settings.py
│   ├── debug_config.py
│   └── mods_config.py
├── core/                    # Ядро приложения
│   ├── core_models.py
│   └── logger.py
├── dto/                     # Объекты передачи данных
│   ├── mappers.py
│   └── verification_dto.py
├── duplicates/              # Обнаружение и слияние дубликатов
│   └── duplicate_merger.py
├── gui/                     # Графический интерфейс
│   ├── core/                # Ядро UI
│   │   ├── tab_manager.py
│   │   ├── ui_builder.py
│   │   └── menu_builder.py
│   ├── tabs/                # Вкладки
│   │   ├── gui_mods_tab.py
│   │   ├── gui_tab_translation.py
│   │   ├── gui_filters_tab.py
│   │   ├── gui_tab_settings.py
│   │   ├── gui_tab_duplicates.py
│   │   ├── gui_tab_verification.py
│   │   ├── gui_dependencies.py
│   │   ├── gui_translation_editor.py
│   │   └── editor/          # Редактор переводов
│   │       ├── editor_dialog.py
│   │       ├── editor_file_browser.py
│   │       ├── editor_toolbar.py
│   │       ├── diff_viewer.py
│   │       ├── quality_checker.py
│   │       └── syntax_highlighter.py
│   ├── components/          # UI компоненты
│   │   ├── statusbar.py
│   │   ├── scrolled_frame.py
│   │   └── ...
│   ├── dialogs/             # Диалоговые окна
│   │   ├── import_translations_dialog.py
│   │   ├── glossary_editor_dialog.py
│   │   ├── integrity_results_dialog.py
│   │   ├── mass_edit_dialog.py
│   │   └── ...
│   ├── handlers/            # Обработчики событий
│   │   └── gui_handlers.py
│   ├── actions/             # Действия
│   │   └── game_data_loader.py
│   ├── help/                # Справка и тултипы (JSON)
│   │   ├── help_loader.py
│   │   ├── editor_help_ru.json
│   │   ├── editor_help_en.json
│   │   ├── editor_help_ua.json
│   │   ├── editor_help_ja.json
│   │   ├── editor_tooltips_ru.json
│   │   ├── editor_tooltips_en.json
│   │   ├── editor_tooltips_ua.json
│   │   ├── editor_tooltips_ja.json
│   │   ├── duplicates_help_ru.json
│   │   ├── duplicates_help_ua.json
│   │   ├── duplicates_help_en.json
│   │   ├── duplicates_help_ja.json
│   │   ├── filters_help_ru.json
│   │   ├── translation_help_ru.json
│   │   ├── verification_help_ru.json
│   │   └── dependencies_help_ru.json
│   └── styling/             # Темы и стили
│       ├── theme_manager.py
│       ├── color_manager.py
│       ├── font_manager.py
│       └── icon_manager.py
├── helpers/                # Вспомогательные утилиты
│   └── editor_history.py
├── integrity/              # Проверка целостности
│   ├── integrity_checker.py
│   ├── mod_verifier.py
│   └── game_data_processor.py
├── language/               # Правила языков
│   ├── language_rules.py
│   ├── rules_engine.py
│   ├── rules_validation.py
│   └── rules_constants.py
├── locales/                # Локализация интерфейса
│   ├── ru.json
│   ├── en.json
│   ├── ua.json
│   └── ja.json
├── scanner/                # Сканер модов
│   └── mod_scanner.py
├── scripts/                # Утилиты и скрипты
├── signals/                # Шина событий
│   ├── signal_bus.py
│   └── events.py
├── translation/            # Модуль перевода
│   ├── translator.py
│   ├── translation_cache.py
│   ├── glossary.py
│   ├── matching.py
│   ├── importer.py
│   ├── keyed_merge.py
│   ├── translation_merger.py
│   ├── translation_utils.py
│   ├── anchor_manager.py
│   ├── per_def_generator.py
│   ├── per_def.py
│   ├── per_def_utils.py
│   ├── obsolete_detector.py
│   ├── proxy_manager.py
│   ├── text_splitter.py
│   ├── constants.py
│   └── engines/            # Движки перевода (8+)
│       ├── base.py
│       ├── fallback_chain.py
│       ├── google_engine.py
│       ├── deepl_engine.py
│       ├── bing_engine.py
│       ├── mymemory_engine.py
│       ├── deeplx_engine.py
│       ├── libre_engine.py
│       ├── translators_engine.py
│       └── argos_engine.py
├── utils/                  # Общие утилиты
│   ├── error_handler.py
│   ├── ui_helpers.py
│   ├── xml_utils.py
│   ├── path_utils.py
│   ├── rimworld_xml.py
│   └── ...
├── verification/           # Верификация и проверка
│   ├── translation_validator.py
│   ├── conflict_detector.py
│   ├── report_generator.py
│   ├── verification_coordinator.py
│   └── xml_parser.py
└── workers/                # Фоновые воркеры
    ├── translation_worker.py
    ├── duplicate_worker.py
    ├── integrity_worker.py
    ├── verification_worker.py
    └── base_worker.py
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

## 🔍 Система верификации (16 проверок)

Проект включает 16 автоматических проверок, разделённых на 2 категории:

### 🏗️ Стандартные проверки (8)
- **about_xml** — Корректность About.xml
- **dependencies** — Проверка зависимостей модов
- **translation_structure** — Структура XML переводов
- **smart_revision** — Устаревшие переводы (через fuzzy-сопоставление)
- **fuzzy_pollution** — Массовые fuzzy-совпадения
- **anchor_consistency** — Согласованность якорей с Core
- **cross_mod_conflicts** — Кросс-мод конфликты
- **structural_integrity** — Целостность XML и переменных {0}

### 🌐 Лингвистические проверки (8)
- **case_inspector** — Проверка падежей после предлогов (для, от, из, у и т.д.)
- **yo_inspector** — Выявление пропущенной буквы «Ё»
- **style_lint** — Стилистический контроль (пассивный залог, канцелярит)
- **lang_detector** — Детектор непереведённого английского текста
- **rulepack_validator** — Валидация RulePackDef (синтаксис, токены, веса)
- **grammar_consistency** — Согласование родов/падежей в списках
- **llm_detector** — Детектор машинного перевода (галлюцинации)
- **format_tag_validator** — Теги форматирования и [PAWN_gender ? : ] токены

---

## 📝 Добавление нового языка интерфейса

См. [locales/README.md](locales/README.md)

### Справка и подсказки

Справка и тултипы хранятся в отдельных JSON файлах в `gui/help/`:

```
gui/help/
├── __init__.py
├── help_loader.py
├── editor_help_ru.json
├── editor_help_ua.json
├── editor_help_en.json
├── editor_help_ja.json
├── editor_tooltips_ru.json
├── editor_tooltips_ua.json
├── editor_tooltips_en.json
├── editor_tooltips_ja.json
├── duplicates_help_ru.json
├── duplicates_help_ua.json
├── duplicates_help_en.json
├── duplicates_help_ja.json
├── filters_help_ru.json
├── translation_help_ru.json
├── verification_help_ru.json
└── dependencies_help_ru.json
```

Для добавления нового языка см. [gui/help/README.md](gui/help/README.md).

---

## 📄 Лицензия

MIT License — см. файл [LICENSE](LICENSE)

---

## 🙏 Благодарности

- [deep-translator](https://github.com/nidhaloff/deep-translator) — библиотека для перевода
- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) — современный UI
- [RimWorld](https://rimworldgame.com/) — великолепная игра

---

## 📞 Поддержка

- **Issues**: [GitHub Issues](https://github.com/yourusername/rimworld-translator-grabber/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/rimworld-translator-grabber/discussions)


---

*Сделано с ❤️ для сообщества RimWorld*
