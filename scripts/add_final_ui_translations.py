#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Добавление последних ~50 ключей для UI"""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"

NEW_KEYS = {
    # gui_translation_editor.py - status indicators
    "editor_status_loading": {"ru": "⏳ Загрузка...", "en": "⏳ Loading...", "ua": "⏳ Завантаження...", "ja": "⏳ ロード中..."},
    "editor_status_unsaved": {"ru": "🔴 Не сохранено", "en": "🔴 Unsaved", "ua": "🔴 Не збережено", "ja": "🔴 未保存"},
    "editor_status_saved": {"ru": "✅ Сохранено", "en": "✅ Saved", "ua": "✅ Збережено", "ja": "✅ 保存済み"},
    
    # file types
    "filetype_xml": {"ru": "XML файлы", "en": "XML files", "ua": "XML файли", "ja": "XMLファイル"},
    "filetype_csv": {"ru": "CSV файлы", "en": "CSV files", "ua": "CSV файли", "ja": "CSVファイル"},
    "filetype_all": {"ru": "Все файлы", "en": "All files", "ua": "Всі файли", "ja": "すべてのファイル"},
    "filetype_txt": {"ru": "Text файлы", "en": "Text files", "ua": "Text файли", "ja": "Textファイル"},
    "filetype_json": {"ru": "JSON файлы", "en": "JSON files", "ua": "JSON файли", "ja": "JSONファイル"},
    
    # CSV headers
    "csv_header_key": {"ru": "Ключ", "en": "Key", "ua": "Ключ", "ja": "キー"},
    "csv_header_value": {"ru": "Значение", "en": "Value", "ua": "Значення", "ja": "値"},
    "csv_header_status": {"ru": "Статус", "en": "Status", "ua": "Статус", "ja": "ステータス"},
    
    # Quality check messages
    "editor_quality_untranslated": {"ru": "❌ Строка {i}: '{k}' - не переведена", "en": "❌ Line {i}: '{k}' - not translated", "ua": "❌ Рядок {i}: '{k}' - не перекладено", "ja": "❌ 行 {i}: '{k}' - 未翻訳"},
    "editor_quality_extra_spaces": {"ru": "⚠️ Строка {i}: '{k}' - лишние пробелы", "en": "⚠️ Line {i}: '{k}' - extra spaces", "ua": "⚠️ Рядок {i}: '{k}' - зайві пробіли", "ja": "⚠️ 行 {i}: '{k}' - 余分なスペース"},
    "editor_quality_placeholder_mismatch": {"ru": "⚠️ Строка {i}: '{k}' - несоответствие плейсхолдеров", "en": "⚠️ Line {i}: '{k}' - placeholder mismatch", "ua": "⚠️ Рядок {i}: '{k}' - невідповідність плейсхолдерів", "ja": "⚠️ 行 {i}: '{k}' - プレースホルダーの不一致"},
    "editor_quality_missing_tags": {"ru": "⚠️ Строка {i}: '{k}' - отсутствуют теги", "en": "⚠️ Line {i}: '{k}' - missing tags", "ua": "⚠️ Рядок {i}: '{k}' - відсутні теги", "ja": "⚠️ 行 {i}: '{k}' - タグがありません"},
    "editor_quality_too_long": {"ru": "ℹ️ Строка {i}: '{k}' - перевод слишком длинный", "en": "ℹ️ Line {i}: '{k}' - translation too long", "ua": "ℹ️ Рядок {i}: '{k}' - переклад занадто довгий", "ja": "ℹ️ 行 {i}: '{k}' - 翻訳が長すぎます"},
    "editor_quality_caps_lock": {"ru": "ℹ️ Строка {i}: '{k}' - возможен Caps Lock", "en": "ℹ️ Line {i}: '{k}' - possible Caps Lock", "ua": "ℹ️ Рядок {i}: '{k}' - можливий Caps Lock", "ja": "ℹ️ 行 {i}: '{k}' - Caps Lockの可能性"},
    
    # Editor history buttons
    "editor_history_save_version": {"ru": "💾 Сохранить версию", "en": "💾 Save Version", "ua": "💾 Зберегти версію", "ja": "💾 バージョンを保存"},
    "editor_history_restore": {"ru": "↩️ Восстановить", "en": "↩️ Restore", "ua": "↩️ Відновити", "ja": "↩️ 復元"},
    
    # File selector
    "editor_browse": {"ru": "📂 Обзор...", "en": "📂 Browse...", "ua": "📂 Огляд...", "ja": "📂 参照..."},
    "editor_browse_from_mods": {"ru": "📁 Выбрать из модов", "en": "📁 Choose from Mods", "ua": "📁 Вибрати з модів", "ja": "📁 MODから選択"},
    "editor_recent_files": {"ru": "🕐 Последние:", "en": "🕐 Recent:", "ua": "🕐 Останні:", "ja": "🕐 最近:"},
    "editor_open_recent": {"ru": "🕐 Открыть", "en": "🕐 Open", "ua": "🕐 Відкрити", "ja": "🕐 開く"},
    "editor_open_editor": {"ru": "✏️ Открыть редактор", "en": "✏️ Open Editor", "ua": "✏️ Відкрити редактор", "ja": "✏️ エディターを開く"},
    "editor_refresh": {"ru": "🔄 Обновить", "en": "🔄 Refresh", "ua": "🔄 Оновити", "ja": "🔄 更新"},
    
    # Context menu
    "editor_ctx_open": {"ru": "✏️ Открыть в редакторе", "en": "✏️ Open in Editor", "ua": "✏️ Відкрити в редакторі", "ja": "✏️ エディターで開く"},
    "editor_ctx_copy_path": {"ru": "📋 Копировать путь", "en": "📋 Copy Path", "ua": "📋 Копіювати шлях", "ja": "📋 パスをコピー"},
    "editor_ctx_open_folder": {"ru": "📂 Открыть папку", "en": "📂 Open Folder", "ua": "📂 Відкрити папку", "ja": "📂 フォルダーを開く"},
    "editor_ctx_info": {"ru": "📊 Информация", "en": "📊 Information", "ua": "📊 Інформація", "ja": "📊 情報"},
    "editor_ctx_refresh_list": {"ru": "🔄 Обновить список", "en": "🔄 Refresh List", "ua": "🔄 Оновити список", "ja": "🔄 リストを更新"},
    
    # gui.py - dialogs and logs
    "gui_select_mods_folder": {"ru": "Выберите папку с модами", "en": "Select mods folder", "ua": "Виберіть папку з модами", "ja": "MODフォルダーを選択"},
    "gui_select_game_folder": {"ru": "Выберите папку с RimWorld", "en": "Select RimWorld folder", "ua": "Виберіть папку з RimWorld", "ja": "RimWorldフォルダーを選択"},
    "gui_debug_enabled": {"ru": "🔧 Debug-режим включён", "en": "🔧 Debug mode enabled", "ua": "🔧 Debug-режим увімкнено", "ja": "🔧 デバッグモード有効"},
    "gui_debug_disabled": {"ru": "🔧 Debug-режим выключен", "en": "🔧 Debug mode disabled", "ua": "🔧 Debug-режим вимкнено", "ja": "🔧 デバッグモード無効"},
    "gui_history_opened_folder": {"ru": "Открыта папка", "en": "Opened folder", "ua": "Відкрито папку", "ja": "フォルダーを開きました"},
    "gui_history_settings_saved": {"ru": "Настройки сохранены", "en": "Settings saved", "ua": "Налаштування збережено", "ja": "設定を保存しました"},
    "gui_history_duplicate_merge_start": {"ru": "Начало слияния дубликатов", "en": "Duplicate merge started", "ua": "Початок злиття дублікатів", "ja": "重複のマージを開始しました"},
    "gui_history_game_data_loading": {"ru": "Загрузка официальных данных игры...", "en": "Loading official game data...", "ua": "Завантаження офіційних даних гри...", "ja": "公式ゲームデータを読み込み中..."},
    
    # tab_manager.py
    "tab_manager_show_all_tabs": {"ru": "🔄 Показать все вкладки", "en": "🔄 Show all tabs", "ua": "🔄 Показати всі вкладки", "ja": "🔄 すべてのタブを表示"},
    
    # gui_dependencies.py
    "dependencies_find_mods": {"ru": "🔍 Найти", "en": "🔍 Find", "ua": "🔍 Знайти", "ja": "🔍 検索"},
    
    # Additional file dialogs
    "dialog_save_log": {"ru": "Сохранить лог", "en": "Save Log", "ua": "Зберегти лог", "ja": "ログを保存"},
    "dialog_export_csv": {"ru": "Экспорт в CSV", "en": "Export to CSV", "ua": "Експорт в CSV", "ja": "CSVにエクスポート"},
    "dialog_open_file": {"ru": "Открыть файл", "en": "Open File", "ua": "Відкрити файл", "ja": "ファイルを開く"},
    "dialog_save_file": {"ru": "Сохранить файл", "en": "Save File", "ua": "Зберегти файл", "ja": "ファイルを保存"},
}

def main():
    print("🔧 Добавление последних ~50 ключей...\n")
    languages = ["ru", "en", "ua", "ja"]

    for lang in languages:
        file_path = LOCALES_DIR / f"{lang}.json"
        if not file_path.exists():
            print(f"❌ Файл не найден: {file_path}")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        lang_code = list(data.keys())[0]
        translations = data[lang_code]

        added = 0
        for key, lang_data in NEW_KEYS.items():
            if key not in translations:
                translations[key] = lang_data[lang]
                added += 1

        data[lang_code] = translations
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ {lang}.json: добавлено {added} ключей (всего: {len(translations)})")

    print("\n✨ Готово!")

if __name__ == "__main__":
    main()
