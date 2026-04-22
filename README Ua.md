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

# Створюємо глосарій
glossary = Glossary("glossary.json")
glossary.add_term("RimWorld", "РимМир")
glossary.add_term("colonist", "колоніст")

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
├── config/                  # Конфігурація
│   ├── config_manager.py    # Менеджер налаштувань
│   ├── paths_config.py      # Шляхи до файлів
│   └── language_constants.py# Константи локалізації
├── translation/             # Модуль перекладу
│   ├── translator.py        # Основний перекладач
│   ├── translation_cache.py # In-memory кеш
│   ├── constants.py         # Константи
│   ├── glossary.py          # Глосарій
│   ├── proxy_manager.py     # Управління проксі
│   ├── text_splitter.py     # Розби́ння тексту
│   └── engines/             # Рушії перекладу
│       ├── base.py          # Базовий клас
│       ├── fallback_chain.py# Fallback-ланцюжок
│       ├── google_engine.py # Google Translate
│       ├── deepl_engine.py  # DeepL
│       └── ...
├── gui/                     # Графічний інтерфейс
│   ├── gui.py               # Основне вікно
│   ├── core/                # Ядро UI (tab_manager, ui_builder, menu_builder)
│   ├── tabs/                # Вкладки
│   │   └── editor/          # Модулі редактора (перенесено з gui_translation_editor.py)
│   │       ├── editor_toolbar.py      # Панель інструментів
│   │       ├── editor_file_browser.py # Вкладка вибору файлів
│   │       └── editor_dialog.py       # Точка входу в діалог
│   ├── components/          # Компоненти UI (статус-бар, лог тощо)
│   ├── handlers/            # Обробники подій (batch-логівання)
│   ├── dialogs/             # Діалоги (цілосність, імпорт, глосарій)
│   ├── help/                # Допомога та тултипи (JSON файли)
│   │   ├── help_loader.py   # Загрузчик допомоги
│   │   ├── editor_help_ru.json
│   │   ├── editor_help_en.json
│   │   ├── editor_tooltips_ru.json
│   │   └── editor_tooltips_en.json
│   └── styling/             # Тьми, шрифти, кольори
├── verification/            # Верифікація
├── workers/                 # Фонові задачі (потокобезпечні)
├── integrity/               # Перевірка цілосності XML
├── signals/                 # Шина сигналів (спрощено — мёртвий код видалено)
├── utils/                   # Утиліти
│   ├── error_handler.py     # Обробка помилок
│   ├── ui_helpers.py        # UI хелпери (debounce)
│   └── ...
├── locales/                 # Локалізація інтерфейсу
│   ├── ru.json
│   ├── en.json
│   └── ...
└── docs/                    # Документація
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

## 📝 Додавання нової мови інтерфейсу

Див. [locales/README.md](locales/README.md)

### Допомога та тултипи

Допомога та тултипи зберігаються у окремих JSON файлах в `gui/help/`:

```
gui/help/
├── editor_help_ru.json      # Допомога на російській
├── editor_help_en.json      # Допомога на англійській
├── editor_tooltips_ru.json  # Тултипи на російській
└── editor_tooltips_en.json  # Тултипи на англійській
```

Для додавання нової мови:

1. Скопіюйте `editor_help_ru.json` → `editor_help_<код>.json`
2. Скопіюйте `editor_tooltips_ru.json` → `editor_tooltips_<код>.json`
3. Перекладіть вміст
4. Загрузчик автоматично використає fallback на `ru`, якщо файл не знайдено

Деталі: [gui/help/README.md](gui/help/README.md)

---

## 📄 Ліцензія

MIT License — див. файл [LICENSE](LICENSE).

---

## 🙏 Подяки

- [deep-translator](https://github.com/nidhaloff/deep-translator) — бібліотека для перекладу
- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) — сучасний UI
- [RimWorld](https://rimworldgame.com/) — неймовірна гра

---

## 📞 Підтримка

- **Issues**: [GitHub Issues](https://github.com/yourusername/rimworld-translator-grabber/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/rimworld-translator-grabber/discussions)
- **Email**: <your.email@example.com>

---

*Зроблено з ❤️ для спільноти RimWorld*
