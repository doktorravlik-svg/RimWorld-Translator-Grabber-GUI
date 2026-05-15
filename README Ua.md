# 🌍 RimWorld Translator Grabber

**Автоматизований інструмент для перекладу та управління модами RimWorld**

![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

---

## 📖 Опис

RimWorld Translator Grabber — потужний інструмент для автоматизації перекладу модів RimWorld на різні мови. Підтримує 8+ рушіїв перекладу, інтелектуальну маршрутизацію, кешування, глосарії та повноцінний редактор перекладів.

---

## ✨ Функціонал

### 🔄 Переклад

- ✅ **8+ рушіїв перекладу**: Google Translate, MyMemory, DeepL, Bing, DeepLX, Translators, LibreTranslate, Argos Translate
- ✅ **Fallback-ланцюжок**: Автоматичне перемикання на наступний рушій при помилці
- ✅ **Умна маршрутизація**: Автопріоритезація рушіїв за успішністю перекладів
- ✅ **Кешування**: In-memory кеш з TTL для прискорення повторних перекладів
- ✅ **База перекладів**: SQLite сховище для вже переведених текстів
- ✅ **Глосарій**: Користувальницькі словники для специфічних термінів
- ✅ **Умне розби́ння**: Автоматичне чанкінг довгих текстів
- ✅ **Rate Limiting**: Захист від бану по IP

### 🎨 Інтерфейс

- ✅ **Сучасний GUI**: ttkbootstrap з підтримкою тем
- ✅ **Многомовність**: Інтерфейс на 5+ мовах
- ✅ **Візуальний редактор**: Редагування перекладів із підсвічуванням синтаксису
- ✅ **Дерево модів**: Зручна навігація по модах з фільтрацією
- ✅ **Статус-бар**: Детальна інформація про процес перекладу з тултипами

### 🛠️ Інструменти

- ✅ **Верифікація**: Перевірка якості перекладу (пакетний вивід без підвисань)
- ✅ **Пошук дублікатів**: Виявлення повторюваних рядків із контекстним меню
- ✅ **Фільтри**: Гнучка фільтрація за тегами, статусами, мовами (повторне застосування без втрати даних)
- ✅ **Залежності**: Перевірка залежностей модів
- ✅ **Цілосність**: Перевірка файлів на помилки (окремий вікно результатів)
- ✅ **Редактор перекладів**:
  - Завантаження окремих XML файлів АБО цілих папок Keyed;
  - Порівняння з оригіналом (Diff) — посимвольні зміни;
  - Глосарій термінів;
  - Історія версій файлів;
  - Підказки та перевірка орфографії;
  - Drag & Drop файлів.
- ✅ **Експорт звітів**: TXT, JSON, CSV формати

---

## 🚀 Встановлення

### Вимоги

- Python: 3.14+
- Platform: Windows 10/11

### Кроки встановлення

1. **Клонуйте репозиторій:**

   ```bash
   git clone https://github.com/yourusername/rimworld-translator-grabber.git
   cd rimworld-translator-grabber
   ```

2. **Створіть віртуальне оточення:**

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Встановіть залежності:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Запустіть додаток:**

   ```bash
   # GUI (рекомендується)
   python run_gui.py
   
   # Або через батник
   run_gui.bat
   
   # CLI (командний рядок)
   python main.py <шлях_до_моду>
   ```

---

## 📚 Використання

### Базовий переклад

```python
from translation.translator import AutoTranslator

# Створюємо перекладач
translator = AutoTranslator(
    enabled=True,
    source_lang="English",
    target_lang="Russian",
    engine_names=["google", "deepl", "bing"],
)

# Перекладаємо текст
result = translator.translate("Hello, world!")
print(result)  # Привіт, світ!
```

### Пакетний переклад

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

### Використання глосарію

```python
from translation.glossary import Glossary

# Створюємо глосарій (категорія визначається автоматично)
glossary = Glossary()
glossary.add("RimWorld", "РимМир", category="auto")
glossary.add("colonist", "колоніст", category="auto")

# Або завантажити з JSON-файлів за категоріями (створюються автоматично)
# Файли зберігаються в папці config/:
#   - glossary_game.json      (ігрові терміни)
#   - glossary_seed.json      (базові терміни)
#   - glossary_user.json      (користувацькі терміни)
#   - glossary_auto.json      (авто-витягнуті терміни)
#   - glossary_general.json  (загальні терміни)

# Застосуємо до тексту
result = glossary.apply_to_text("Welcome to RimWorld, colonist!")
```

### Налаштування кешу

```python
from translation.translation_cache import TranslationCache

# Створюємо кеш з налаштуваннями
cache = TranslationCache(
    maxsize=4096,      # Максимум записів
    ttl=7200,          # Час життя: 2 години
    enable_stats=True  # Збір статистики
)

# Статистика
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
```

---

## 🏗️ Архітектура

```
rimworld-translator-grabber/
├── collectors/              # Колектори даних модів
│   └── collectors.py
├── config/                  # Конфігурація + файли глосарію
│   ├── config_manager.py
│   ├── paths_config.py
│   ├── language_constants.py
│   ├── glossary_game.json      # Ігрові терміни (авто-генерація)
│   ├── glossary_seed.json      # Базові терміни (авто-генерація)
│   ├── glossary_user.json      # Користувацькі терміни (авто-генерація)
│   ├── glossary_auto.json      # Авто-витягнуті терміни (авто-генерація)
│   ├── glossary_general.json  # Загальні терміни (авто-генерація)
│   ├── grabber_settings.py
│   ├── debug_config.py
│   └── mods_config.py
├── core/                    # Ядро програми
│   ├── core_models.py
│   └── logger.py
├── dto/                     # Об'єкти передачі даних
│   ├── mappers.py
│   └── verification_dto.py
├── duplicates/              # Виявлення та злиття дублікатів
│   └── duplicate_merger.py
├── gui/                     # Графічний інтерфейс
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
│   │   └── editor/          # Редактор перекладів
│   │       ├── editor_dialog.py
│   │       ├── editor_file_browser.py
│   │       ├── editor_toolbar.py
│   │       ├── diff_viewer.py
│   │       ├── quality_checker.py
│   │       └── syntax_highlighter.py
│   ├── components/          # UI компоненти
│   │   ├── statusbar.py
│   │   ├── scrolled_frame.py
│   │   └── ...
│   ├── dialogs/             # Діалогові вікна
│   │   ├── import_translations_dialog.py
│   │   ├── glossary_editor_dialog.py
│   │   ├── integrity_results_dialog.py
│   │   ├── mass_edit_dialog.py
│   │   └── ...
│   ├── handlers/            # Обробники подій
│   │   └── gui_handlers.py
│   ├── actions/             # Дії
│   │   └── game_data_loader.py
│   ├── help/                # Довідка та підказки (JSON)
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
│   └── styling/             # Теми та стилі
│       ├── theme_manager.py
│       ├── color_manager.py
│       ├── font_manager.py
│       └── icon_manager.py
├── helpers/                # Допоміжні утиліти
│   └── editor_history.py
├── integrity/              # Перевірка цілісності
│   ├── integrity_checker.py
│   ├── mod_verifier.py
│   └── game_data_processor.py
├── language/               # Правила мов
│   ├── language_rules.py
│   ├── rules_engine.py
│   ├── rules_validation.py
│   └── rules_constants.py
├── locales/                # Локалізація інтерфейсу
│   ├── ru.json
│   ├── en.json
│   ├── ua.json
│   └── ja.json
├── scanner/                # Сканер модів RimWorld
│   └── mod_scanner.py
├── scripts/                # Утиліти та скрипти
├── signals/                # Шина подій
│   ├── signal_bus.py
│   └── events.py
├── translation/            # Модуль перекладу
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
│   └── engines/            # Рушії перекладу (8+)
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
├── utils/                  # Загальні утиліти
│   ├── error_handler.py
│   ├── ui_helpers.py
│   ├── xml_utils.py
│   ├── path_utils.py
│   ├── rimworld_xml.py
│   └── ...
├── verification/           # Верифікація та перевірка
│   ├── translation_validator.py
│   ├── conflict_detector.py
│   ├── report_generator.py
│   ├── verification_coordinator.py
│   └── xml_parser.py
└── workers/                # Фонові воркери (потокобезпечні)
    ├── translation_worker.py
    ├── duplicate_worker.py
    ├── integrity_worker.py
    ├── verification_worker.py
    └── base_worker.py
```

---

## 🔧 Конфігурація

### Налаштування перекладача

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

### Глосарій (JSON)

```json
{
    "terms": {
        "RimWorld": "РимМир",
        "colonist": "колоніст",
        "raid": "рейд"
    }
}
```

---

## 🧪 Тестування

```bash
# Запустити всі тести
pytest

# Запустити тести перекладача
python -m translation.translator

# Перевірити покриття
pytest --cov=translation --cov-report=html
```

---

## 📊 Продуктивність

| Операція | Без кешу | З кешем | Покращення |
|----------|----------|---------|------------|
| Повторний переклад | 500ms | <1ms | **500x** |
| Пакетний (100 рядків) | 50s | 5s | **10x** |
| З глосарієм | +10ms | +10ms | — |

---

## 🤝 Внесок у проект

1. Форкніть репозиторій
2. Створіть гілку (`git checkout -b feature/amazing-feature`)
3. Зафіксуйте зміни (`git commit -m 'Add amazing feature'`)
4. Відправте в гілку (`git push origin feature/amazing-feature`)
5. Відкрийте Pull Request

---

## 📝 Історія змін (2026-04)

### v2.0+ — Великі покращення

#### 🐛 Виправлення

- **Верифікація без підвисань**: Пакетна вставка результатів (`log_batch`) замість пострядкової — O(n²) → O(n).
- **Логівання в панель**: `ModsManagerTab` і `TranslationEditorTab` тепер пишуть у лог-панель, а не в консоль.
- **SignalBus очищено**: Видалено мёртвий код (`_worker_thread`, `_event_queue`, `start/stop`) — ніколи не використовувався.
- **Виправлена геометрія редактора**: Усі виджети в `edit_panel` використовують `grid()` замість змішування `pack` + `grid`.
- **Фільтри без втрати даних**: Усі вкладки зберігають `_all_*_items` для коректного повторного застосування фільтрів.
- **Обробник помилок сканування дублікатів**: Змінна `e` тепер правильно захоплюється в except блоці.

#### ✨ Нові можливості

- **Контекстне меню дублікатів**: Правий клік → Обрати/Зняти вибір, Відкрити папку, Інформація.
- **Diff у редакторі**: Посимвольне порівняння оригіналу та перекладу з підсвічуванням (🟥 Видалено | 🟨 Змінено | 🟩 Додано).
- **Оновлена допомога редактора**: Детальний опис усіх функцій, гарячих клавіш і функції Diff.
- **Тултипи кнопок редактора**: Diff, Глосарій та інші кнопки тепер мають підказки.
- **Розширене логівання відкриття файлів**: Детальні логи для налагодження проблем із завантаженням файлів у редакторі.
- **Вибір папки в редакторі**: Кнопка 📁 «Відкрити папку» для завантаження всіх Keyed файлів одразу.
- **Окно цілосності**: Окремий діалог з деревом помилок, фільтрами та експортом звітів.
- **Тултипи в статус-барі**: Наведення на лічильники показує що вони означають.
- **Усі моди видимі**: Моди без About.xml і з помилками парсинга тепер відображаються.

#### 🏗️ Архітектура

- **Розділення редактора**: `TranslationEditorTab` і `WrappingToolbar` винесено в `gui/tabs/editor/`.
- **Убрані ліміти**: Верифікація показує всі результати (було [:20], [:5], [:3], [:10]).
- **Збільшено ліміти**: Дублікати [:4]→[:20], mass_edit [:50]→[:100], integrity [:80]→[:150].
- **Видалено дублюючий `__init__`**: `editor_file_browser.py` мав два `__init__` методи.
- **Єдиний стиль фільтрів**: Усі вкладки використовують `_all_*_items` для зберігання елементів дерева.

---

## 🔍 Система верифікації (16 перевірок)

Проект включає 16 автоматичних перевірок якості перекладів, поділених на 2 категорії:

### 🏗️ Стандартні перевірки (8)
- **about_xml** — Коректність About.xml
- **dependencies** — Перевірка залежностей модів
- **translation_structure** — Структура XML-перекладів
- **smart_revision** — Застарілі переклади (через fuzzy-зіставлення)
- **fuzzy_pollution** — Масові fuzzy-співпадіння
- **anchor_consistency** — Зглагування якорів з Core
- **cross_mod_conflicts** — Крос-мод конфлікти
- **structural_integrity** — Цілісність XML та змінних {0}

### 🌐 Лінгвістичні перевірки (8)
- **case_inspector** — Перевірка відмінків після прийменників (для, від, з, у та ін.)
- **yo_inspector** — Виявлення пропущеної букви «Ё»
- **style_lint** — Стилістичний контроль (пасивний стан, канцеляризми)
- **lang_detector** — Детектор неперекладеного англійського тексту
- **rulepack_validator** — Валідація RulePackDef (синтаксис, токени, ваги)
- **grammar_consistency** — Зглагування рідів/відмінків у списках
- **llm_detector** — Детектор машинного перекладу (галюцинації)
- **format_tag_validator** — Теги форматування та [PAWN_gender ? : ] токени

---

## 📝 Додавання нової мови інтерфейсу


Див. [locales/README.md](locales/README.md)

### Допомога та тултипи

Допомога та тултипи зберігаються у окремих JSON файлах в `gui/help/`:

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

Для додавання нової мови див. [gui/help/README.md](gui/help/README.md).

---

## 📄 Ліцензія

MIT License — див. файл [LICENSE](LICENSE).

---

## 🙏 Подяки

- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) — сучасний UI
- [RimWorld](https://rimworldgame.com/) — неймовірна гра

---


---

*Зроблено з ❤️ для спільноти RimWorld*
