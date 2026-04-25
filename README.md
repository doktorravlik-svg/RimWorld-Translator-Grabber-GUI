# 🌍 RimWorld Translator Grabber

**Automated tool for translating and managing RimWorld mods**

![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

---

## 📖 Description

RimWorld Translator Grabber is a powerful tool for automating the translation of RimWorld mods into multiple languages. It supports 8+ translation engines, intelligent routing, caching, glossaries, and a full-featured translation editor.

---

## ✨ Features

### 🔄 Translation

- ✅ **8+ translation engines**: Google Translate, MyMemory, DeepL, Bing, DeepLX, Translators, LibreTranslate, Argos Translate
- ✅ **Fallback chain**: Automatically switches to the next engine on error
- ✅ **Smart routing**: Auto-prioritizes engines by translation success
- ✅ **Caching**: In-memory cache with TTL to speed up repeated translations
- ✅ **Translation database**: SQLite storage for already translated texts
- ✅ **Glossary**: Custom dictionaries for domain-specific terms
- ✅ **Smart splitting**: Automatic chunking of long texts
- ✅ **Rate limiting**: Protection against IP bans

### 🎨 Interface

- ✅ **Modern GUI**: Built with ttkbootstrap and theme support
- ✅ **Multilingual UI**: Interface available in 5+ languages
- ✅ **Visual editor**: Translation editing with syntax highlighting
- ✅ **Mods tree**: Easy navigation of mods with filtering
- ✅ **Status bar**: Detailed translation process info with tooltips

### 🛠️ Tools

- ✅ **Verification**: Translation quality checks (batch output without freezes)
- ✅ **Duplicate search**: Detects repeated strings with context menu
- ✅ **Filters**: Flexible filtering by tags, statuses, languages (reapply without data loss)
- ✅ **Dependencies**: Checks mod dependencies
- ✅ **Integrity**: File error checking (separate results window)
- ✅ **Translation editor**:
  - Load individual XML files or entire Keyed folders;
  - Compare with original (Diff) — character-level changes;
  - Glossary terms;
  - File version history;
  - Hints and spellcheck;
  - Drag & drop files.
- ✅ **Export reports**: TXT, JSON, CSV formats

---

## 🚀 Installation

### Requirements

- Python: 3.14+
- Platform: Windows 10/11

### Installation Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/rimworld-translator-grabber.git
   cd rimworld-translator-grabber
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**

   ```bash
   # GUI (recommended)
   python run_gui.py
   
   # Or via batch file
   run_gui.bat
   
   # CLI (command line)
   python main.py <path_to_mod>
   ```

---

## 📚 Usage

### Basic translation

```python
from translation.translator import AutoTranslator

# Create translator
translator = AutoTranslator(
    enabled=True,
    source_lang="English",
    target_lang="Russian",
    engine_names=["google", "deepl", "bing"],
)

# Translate text
result = translator.translate("Hello, world!")
print(result)  # Привет, мир!
```

### Batch translation

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

### Using a glossary

```python
from translation.glossary import Glossary

# Create glossary
glossary = Glossary("glossary.json")
glossary.add_term("RimWorld", "РимМир")
glossary.add_term("colonist", "колонист")

# Apply to text
result = glossary.apply_to_text("Welcome to RimWorld, colonist!")
```

### Cache configuration

```python
from translation.translation_cache import TranslationCache

# Create cache with settings
cache = TranslationCache(
    maxsize=4096,      # Maximum entries
    ttl=7200,          # Time-to-live: 2 hours
    enable_stats=True  # Collect statistics
)

# Stats
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
```

---

## 🏗️ Architecture

```
rimworld-translator-grabber/
├── collectors/              # Mod data collectors
│   └── collectors.py
├── config/                  # Configuration
│   ├── config_manager.py
│   ├── paths_config.py
│   ├── language_constants.py
│   ├── glossary.json
│   ├── grabber_settings.py
│   ├── debug_config.py
│   └── mods_config.py
├── core/                    # Application core
│   ├── core_models.py
│   └── logger.py
├── dto/                     # Data transfer objects
│   ├── mappers.py
│   └── verification_dto.py
├── duplicates/              # Duplicate detection and merging
│   └── duplicate_merger.py
├── gui/                     # Graphical interface
│   ├── core/                # UI core
│   │   ├── tab_manager.py
│   │   ├── ui_builder.py
│   │   └── menu_builder.py
│   ├── tabs/                # Tabs
│   │   ├── gui_mods_tab.py
│   │   ├── gui_tab_translation.py
│   │   ├── gui_filters_tab.py
│   │   ├── gui_tab_settings.py
│   │   ├── gui_tab_duplicates.py
│   │   ├── gui_tab_verification.py
│   │   ├── gui_dependencies.py
│   │   ├── gui_translation_editor.py
│   │   └── editor/          # Translation editor
│   │       ├── editor_dialog.py
│   │       ├── editor_file_browser.py
│   │       ├── editor_toolbar.py
│   │       ├── diff_viewer.py
│   │       ├── quality_checker.py
│   │       └── syntax_highlighter.py
│   ├── components/          # UI components
│   │   ├── statusbar.py
│   │   ├── scrolled_frame.py
│   │   └── ...
│   ├── dialogs/             # Dialog windows
│   │   ├── import_translations_dialog.py
│   │   ├── glossary_editor_dialog.py
│   │   ├── integrity_results_dialog.py
│   │   ├── mass_edit_dialog.py
│   │   └── ...
│   ├── handlers/            # Event handlers
│   │   └── gui_handlers.py
│   ├── actions/             # Actions
│   │   └── game_data_loader.py
│   ├── help/                # Help and tooltips (JSON)
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
│   └── styling/             # Themes and styles
│        ├── theme_manager.py
│        ├── color_manager.py
│        ├── font_manager.py
│        └── icon_manager.py
├── helpers/                 # Helper utilities
│   └── editor_history.py
├── integrity/               # Integrity checking
│   ├── integrity_checker.py
│   ├── mod_verifier.py
│   └── game_data_processor.py
├── language/                # Language rules
│   ├── language_rules.py
│   ├── rules_engine.py
│   ├── rules_validation.py
│   └── rules_constants.py
├── locales/                 # Interface localization
│   ├── ru.json
│   ├── en.json
│   ├── ua.json
│   └── ja.json
├── scanner/                 # Mod scanner
│   └── mod_scanner.py
├── scripts/                 # Utilities and scripts
├── signals/                 # Event bus
│   ├── signal_bus.py
│   └── events.py
├── translation/             # Translation module
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
│   └── engines/             # Translation engines (8+)
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
├── utils/                   # General utilities
│   ├── error_handler.py
│   ├── ui_helpers.py
│   ├── xml_utils.py
│   ├── path_utils.py
│   ├── rimworld_xml.py
│   └── ...
├── verification/            # Verification and checking
│   ├── translation_validator.py
│   ├── conflict_detector.py
│   ├── report_generator.py
│   ├── verification_coordinator.py
│   └── xml_parser.py
└── workers/                 # Background workers
    ├── translation_worker.py
    ├── duplicate_worker.py
    ├── integrity_worker.py
    ├── verification_worker.py
    └── base_worker.py
```

---

## 🔧 Configuration

### Translator settings

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

### Glossary (JSON)

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

## 🧪 Testing

```bash
# Run all tests
pytest

# Run translator tests
python -m translation.translator

# Check coverage
pytest --cov=translation --cov-report=html
```

---

## 📊 Performance

| Operation | Without cache | With cache | Improvement |
|-----------|---------------|------------|-------------|
| Repeat translation | 500ms | <1ms | **500x** |
| Batch (100 lines) | 50s | 5s | **10x** |
| With glossary | +10ms | +10ms | — |

---

## 🤝 Contributing

1. Fork the repository
2. Create a branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 Changelog (2026-04)

### v2.0+ — Major improvements

#### 🐛 Fixes

- **Verification without freezes**: batch insertion of results (`log_batch`) instead of line-by-line — O(n²) → O(n).
- **Logging to panel**: `ModsManagerTab` and `TranslationEditorTab` now write to the log panel instead of the console.
- **SignalBus cleaned**: removed dead code (`_worker_thread`, `_event_queue`, `start/stop`) — never used.
- **Editor geometry fixed**: all widgets in `edit_panel` use `grid()` instead of mixing `pack` + `grid`.
- **Filters without data loss**: all tabs store `_all_*_items` for correct reapplication of filters.
- **Duplicate-scan error handler**: variable `e` is now correctly captured in the except block.

#### ✨ New features

- **Context menu for duplicates**: right-click → Select/Deselect, Open folder, Info.
- **Diff in editor**: character-level comparison of original and translation with highlighting (🟥 Removed | 🟨 Changed | 🟩 Added).
- **Updated editor help**: detailed description of all features, hotkeys, and Diff.
- **Tooltips for editor buttons**: Diff, Glossary and other buttons now have hints.
- **Extended file-open logging**: detailed logs for debugging file loading issues in the editor.
- **Folder selection in editor**: 📁 "Open folder" button to load all Keyed files at once.
- **Integrity window**: separate dialog with error tree, filters, and report export.
- **Status bar tooltips**: hovering counters shows what they mean.
- **All mods visible**: mods without About.xml and with parsing errors are now displayed.

#### 🏗️ Architecture

- **Editor split**: `TranslationEditorTab` and `WrappingToolbar` moved to `gui/tabs/editor/`.
- **Limits removed**: verification shows all results (previously [:20], [:5], [:3], [:10]).
- **Limits increased**: duplicates [:4]→[:20], mass_edit [:50]→[:100], integrity [:80]→[:150].
- **Duplicate `__init__` removed**: `editor_file_browser.py` had two `__init__` methods.
- **Unified filter style**: all tabs use `_all_*_items` to store tree elements.

---

## 📝 Adding a new UI language

See [locales/README.md](locales/README.md)

### Help and tooltips

Help and tooltips are stored as separate JSON files in `gui/help/`:

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

To add a new 

1. Copy `editor_help_ru.json` → `editor_help_<code>.json`
2. Copy `editor_tooltips_ru.json` → `editor_tooltips_<code>.json`
3. Translate the contents
4. The loader will automatically fall back to `ru` if a file is missing

Details: [gui/help/README.md](gui/help/README.md)

---

## 📄 License

MIT License — see the [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgements

- [deep-translator](https://github.com/nidhaloff/deep-translator) — translation library
- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) — modern UI
- [RimWorld](https://rimworldgame.com/) — the great game

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/rimworld-translator-grabber/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/rimworld-translator-grabber/discussions)


---

*Made with ❤️ for the RimWorld community*
