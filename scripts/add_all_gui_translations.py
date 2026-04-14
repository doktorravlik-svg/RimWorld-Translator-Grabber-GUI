#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Добавление ~75 ключей для gui.py и папки gui/"""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"

NEW_KEYS = {
    # gui.py - messagebox и заголовки
    "gui_import_error": {"ru": "Ошибка импорта", "en": "Import Error", "ua": "Помилка імпорту", "ja": "インポートエラー"},
    "gui_root_title": {"ru": "RimWorld Translator Grabber V2+", "en": "RimWorld Translator Grabber V2+", "ua": "RimWorld Translator Grabber V2+", "ja": "RimWorld Translator Grabber V2+"},
    "gui_settings_saved": {"ru": "Настройки сохранены", "en": "Settings saved", "ua": "Налаштування збережено", "ja": "設定が保存されました"},
    "gui_success": {"ru": "Успех", "en": "Success", "ua": "Успіх", "ja": "成功"},
    "gui_warning": {"ru": "Предупреждение", "en": "Warning", "ua": "Попередження", "ja": "警告"},
    "gui_error": {"ru": "Ошибка", "en": "Error", "ua": "Помилка", "ja": "エラー"},
    "gui_no_mods_folder_warning": {"ru": "Выберите папку с модами", "en": "Please select mods folder", "ua": "Виберіть папку з модами", "ja": "MODフォルダーを選択してください"},
    "gui_data_load_success": {"ru": "Официальные данные загружены", "en": "Official data loaded", "ua": "Офіційні дані завантажено", "ja": "公式データが読み込まれました"},
    "gui_data_load_warning": {"ru": "Не удалось найти файлы данных", "en": "Could not find data files", "ua": "Не вдалося знайти файли даних", "ja": "データファイルが見つかりませんでした"},
    "gui_data_load_error": {"ru": "Не удалось загрузить данные игры", "en": "Failed to load game data", "ua": "Не вдалося завантажити дані гри", "ja": "ゲームデータの読み込みに失敗しました"},
    "gui_data_folder_found": {"ru": "Папка Data найдена", "en": "Data folder found", "ua": "Папку Data знайдено", "ja": "Dataフォルダーが見つかりました"},
    "gui_data_folder_not_found": {"ru": "Не удалось найти папку Data", "en": "Could not find Data folder", "ua": "Не вдалося знайти папку Data", "ja": "Dataフォルダーが見つかりませんでした"},
    "gui_data_folder_prompt": {"ru": "В указанной папке нет Data. Использовать стандартное расположение?", "en": "Data folder not found in specified location. Use default?", "ua": "В указаній папці немає Data. Використовувати стандартне розташування?", "ja": "指定された場所にDataフォルダーがありません。デフォルトを使用しますか？"},
    
    # gui_file_colors.py - статусы файлов
    "filecolor_complete": {"ru": "Полностью переведён", "en": "Fully translated", "ua": "Повністю перекладено", "ja": "完全に翻訳済み"},
    "filecolor_partial": {"ru": "Частичный перевод", "en": "Partial translation", "ua": "Частковий переклад", "ja": "部分的に翻訳済み"},
    "filecolor_error": {"ru": "Ошибка в файле", "en": "File error", "ua": "Помилка у файлі", "ja": "ファイルエラー"},
    "filecolor_empty": {"ru": "Не переведён", "en": "Not translated", "ua": "Не перекладено", "ja": "未翻訳"},
    "filecolor_missing": {"ru": "Файл отсутствует", "en": "File missing", "ua": "Файл відсутній", "ja": "ファイルなし"},
    
    # tab_manager.py - context menu вкладок
    "tab_ctx_hide": {"ru": "Скрыть '{tab}'", "en": "Hide '{tab}'", "ua": "Сховати '{tab}'", "ja": "'{tab}'を非表示"},
    "tab_ctx_show_all": {"ru": "Показать все вкладки", "en": "Show all tabs", "ua": "Показати всі вкладки", "ja": "すべてのタブを表示"},
    "tab_menu_show_hidden": {"ru": "✅ {tab} (скрыта)", "en": "✅ {tab} (hidden)", "ua": "✅ {tab} (схована)", "ja": "✅ {tab} (非表示)"},
    "tab_menu_hide_visible": {"ru": "   {tab}", "en": "   {tab}", "ua": "   {tab}", "ja": "   {tab}"},
    
    # gui_tab_translation.py
    "translation_cancel_confirm": {"ru": "Вы уверены, что хотите отменить перевод?", "en": "Are you sure you want to cancel translation?", "ua": "Ви впевнені, що хочете скасувати переклад?", "ja": "翻訳をキャンセルしてもよろしいですか？"},
    "translation_cancel_title": {"ru": "Отмена перевода", "en": "Cancel Translation", "ua": "Скасування перекладу", "ja": "翻訳のキャンセル"},
    
    # gui_dependencies.py
    "deps_confirm_mods_folder": {"ru": "Вы выбрали папку, которая не существует. Создать её?", "en": "Selected folder doesn't exist. Create it?", "ua": "Вибрана папка не існує. Створити її?", "ja": "選択されたフォルダは存在しません。作成しますか？"},
    "deps_select_mods_first": {"ru": "Сначала выберите папку Mods", "en": "Select Mods folder first", "ua": "Спочатку виберіть папку Mods", "ja": "最初にModsフォルダーを選択してください"},
    "deps_folder_not_exist_error": {"ru": "Папка не существует", "en": "Folder doesn't exist", "ua": "Папка не існує", "ja": "フォルダーは存在しません"},
    "deps_mods_found_ok": {"ru": "Папка Mods найдена", "en": "Mods folder found", "ua": "Папку Mods знайдено", "ja": "Modsフォルダーが見つかりました"},
    "deps_mods_not_found_msg": {"ru": "Папка Mods не найдена в стандартных расположениях", "en": "Mods folder not found in default locations", "ua": "Папку Mods не знайдено в стандартних розташуваннях", "ja": "Modsフォルダーがデフォルトの場所に見つかりません"},
    "deps_select_mods_warning": {"ru": "Выберите папку с модами", "en": "Please select mods folder", "ua": "Виберіть папку з модами", "ja": "MODフォルダーを選択してください"},
    "deps_mods_not_exist_error": {"ru": "Папки с модами не существуют", "en": "Mods folders don't exist", "ua": "Папки з модами не існують", "ja": "MODフォルダーは存在しません"},
    "deps_analysis_error_msg": {"ru": "Ошибка анализа зависимостей", "en": "Dependency analysis error", "ua": "Помилка аналізу залежностей", "ja": "依存関係分析エラー"},
    "deps_confirm_title": {"ru": "Подтверждение", "en": "Confirmation", "ua": "Підтвердження", "ja": "確認"},
    
    # gui_filters_tab.py
    "filters_config_load_error": {"ru": "Не удалось загрузить конфигурацию фильтров", "en": "Failed to load filters config", "ua": "Не вдалося завантажити конфігурацію фільтрів", "ja": "フィルター設定の読み込みに失敗しました"},
    "filters_saved_ok": {"ru": "Настройки фильтров сохранены!", "en": "Filters settings saved!", "ua": "Налаштування фільтрів збережено!", "ja": "フィルター設定が保存されました！"},
    "filters_save_error": {"ru": "Не удалось сохранить конфигурацию", "en": "Failed to save config", "ua": "Не вдалося зберегти конфігурацію", "ja": "設定の保存に失敗しました"},
    "filters_tag_exists_info": {"ru": "Тег уже есть в списке", "en": "Tag already in list", "ua": "Тег вже є в списку", "ja": "タグは既にリストにあります"},
    "filters_reset_confirm": {"ru": "Сбросить все настройки фильтров к значениям по умолчанию?", "en": "Reset all filters settings to defaults?", "ua": "Скинути всі налаштування фільтрів до значень за замовчуванням?", "ja": "すべてのフィルター設定をデフォルトにリセットしますか？"},
    "filters_reset_ok": {"ru": "Настройки сброшены к значениям по умолчанию", "en": "Settings reset to defaults", "ua": "Налаштування скинуто до значень за замовчуванням", "ja": "設定がデフォルトにリセットされました"},
    "filters_open_config_error": {"ru": "Не удалось открыть файл", "en": "Failed to open file", "ua": "Не вдалося відкрити файл", "ja": "ファイルを開けませんでした"},
    "filters_config_not_found_warning": {"ru": "Файл конфигурации не найден", "en": "Config file not found", "ua": "Файл конфігурації не знайдено", "ja": "設定ファイルが見つかりません"},
    
    # gui_translation_editor.py
    "editor_select_entry_warning": {"ru": "Выберите запись для удаления", "en": "Select entry to delete", "ua": "Виберіть запис для видалення", "ja": "削除するエントリーを選択してください"},
    "editor_delete_confirm": {"ru": "Удалить запись?", "en": "Delete entry?", "ua": "Видалити запис?", "ja": "エントリーを削除しますか？"},
    "editor_save_ok": {"ru": "Файл сохранён", "en": "File saved", "ua": "Файл збережено", "ja": "ファイルが保存されました"},
    "editor_save_error": {"ru": "Ошибка сохранения", "en": "Save error", "ua": "Помилка збереження", "ja": "保存エラー"},
    "editor_unsaved_changes": {"ru": "Несохранённые изменения", "en": "Unsaved changes", "ua": "Незбережені зміни", "ja": "未保存の変更"},
    "editor_unsaved_prompt": {"ru": "Сохранить перед закрытием?", "en": "Save before closing?", "ua": "Зберегти перед закриттям?", "ja": "閉じる前に保存しますか？"},
    "editor_translate_empty_confirm": {"ru": "Найдено {count} пустых записей. Создать базовый перевод?", "en": "Found {count} empty entries. Create basic translation?", "ua": "Знайдено {count} порожніх записів. Створити базовий переклад?", "ja": "{count}件の空のレコードが見つかりました。基本翻訳を作成しますか？"},
    "editor_mass_edit_select_prompt": {"ru": "Выберите записи для массового редактирования", "en": "Select entries for mass editing", "ua": "Виберіть записи для масового редагування", "ja": "一括編集するエントリーを選択してください"},
    "editor_info": {"ru": "Инфо", "en": "Info", "ua": "Інфо", "ja": "情報"},
    "editor_no_empty_entries": {"ru": "Нет пустых записей для перевода", "en": "No empty entries to translate", "ua": "Немає порожніх записів для перекладу", "ja": "翻訳する空のレコードはありません"},
    
    # gui_tab_settings.py
    "settings_ok": {"ru": "OK", "en": "OK", "ua": "OK", "ja": "OK"},
    "settings_fonts_reset_ok": {"ru": "Шрифты сброшены.", "en": "Fonts reset.", "ua": "Шрифти скинуто.", "ja": "フォントがリセットされました。"},
    "settings_error": {"ru": "Ошибка", "en": "Error", "ua": "Помилка", "ja": "エラー"},
    "settings_fonts_reset_error": {"ru": "Не удалось сбросить шрифты", "en": "Failed to reset fonts", "ua": "Не вдалося скинути шрифти", "ja": "フォントのリセットに失敗しました"},
    "settings_colors_reset_ok": {"ru": "Цвета сброшены.", "en": "Colors reset.", "ua": "Кольори скинуто.", "ja": "色がリセットされました。"},
    "settings_colors_reset_error": {"ru": "Не удалось сбросить цвета", "en": "Failed to reset colors", "ua": "Не вдалося скинути кольори", "ja": "色のリセットに失敗しました"},
    "settings_reset_confirm": {"ru": "Сбросить все настройки к значениям по умолчанию?", "en": "Reset all settings to defaults?", "ua": "Скинути всі налаштування до значень за замовчуванням?", "ja": "すべての設定をデフォルトにリセットしますか？"},
    "settings_reset_ok": {"ru": "Настройки сброшены", "en": "Settings reset", "ua": "Налаштування скинуто", "ja": "設定がリセットされました"},
    
    # gui_components.py - LogPanel
    "logpanel_save_title": {"ru": "Сохранить лог", "en": "Save log", "ua": "Зберегти лог", "ja": "ログを保存"},
    "logpanel_save_ok": {"ru": "Лог сохранён в {path}", "en": "Log saved to {path}", "ua": "Лог збережено в {path}", "ja": "ログが{path}に保存されました"},
    "logpanel_save_error": {"ru": "Ошибка сохранения лога", "en": "Failed to save log", "ua": "Помилка збереження логу", "ja": "ログの保存に失敗しました"},
    "logpanel_search_not_found": {"ru": "Текст не найден", "en": "Text not found", "ua": "Текст не знайдено", "ja": "テキストが見つかりません"},
    
    # debug_log_dialog.py
    "debug_log_clear_confirm": {"ru": "Вы уверены, что хотите очистить лог?", "en": "Are you sure you want to clear the log?", "ua": "Ви впевнені, що хочете очистити лог?", "ja": "ログをクリアしてもよろしいですか？"},
    "debug_log_save_ok": {"ru": "Лог сохранён", "en": "Log saved", "ua": "Лог збережено", "ja": "ログが保存されました"},
    "debug_log_save_error": {"ru": "Ошибка сохранения", "en": "Save error", "ua": "Помилка збереження", "ja": "保存エラー"},
    "debug_log_clear_title": {"ru": "Очистить лог", "en": "Clear log", "ua": "Очистити лог", "ja": "ログをクリア"},
    
    # gui_tab_verification.py
    "verification_no_results": {"ru": "Нет результатов для экспорта", "en": "No results to export", "ua": "Немає результатів для експорту", "ja": "エクスポートする結果がありません"},
    "verification_export_ok": {"ru": "Отчёт сохранён", "en": "Report saved", "ua": "Звіт збережено", "ja": "レポートが保存されました"},
    "verification_export_error": {"ru": "Ошибка сохранения отчёта", "en": "Failed to save report", "ua": "Помилка збереження звіту", "ja": "レポートの保存に失敗しました"},
    
    # gui_tab_duplicates.py
    "duplicates_no_mods_warning": {"ru": "Выберите существующую папку с модами", "en": "Select existing mods folder", "ua": "Виберіть існуючу папку з модами", "ja": "既存のMODフォルダーを選択してください"},
    "duplicates_no_selection_warning": {"ru": "Выберите хотя бы одну группу дубликатов", "en": "Select at least one duplicate group", "ua": "Виберіть хоча б одну групу дублікатів", "ja": "少なくとも1つの重複グループを選択してください"},
    "duplicates_no_paths_warning": {"ru": "Выберите папки модов и вывода", "en": "Select mods and output folders", "ua": "Виберіть папки модів та виводу", "ja": "MODフォルダーと出力フォルダーを選択してください"},
    
    # gui_mods_tab.py
    "mods_save_success": {"ru": "Сохранено {count} активных модов", "en": "Saved {count} active mods", "ua": "Збережено {count} активних модів", "ja": "{count}個のアクティブMODが保存されました"},
    "mods_save_error": {"ru": "Не удалось сохранить конфигурацию", "en": "Failed to save config", "ua": "Не вдалося зберегти конфігурацію", "ja": "設定の保存に失敗しました"},
    "mods_folder_not_found_warning": {"ru": "Папка мода не найдена", "en": "Mod folder not found", "ua": "Папка моду не знайдено", "ja": "MODフォルダーが見つかりません"},
    
    # game_data_loader.py
    "game_loader_data_found_prompt": {"ru": "В указанной папке нет Data. Использовать стандартное расположение?", "en": "Data folder not found. Use default location?", "ua": "В указаній папці немає Data. Використовувати стандартне розташування?", "ja": "指定された場所にDataフォルダーがありません。デフォルトを使用しますか？"},
    "game_loader_load_success": {"ru": "Официальные данные загружены", "en": "Official data loaded", "ua": "Офіційні дані завантажено", "ja": "公式データが読み込まれました"},
    "game_loader_load_warning": {"ru": "Не удалось найти файлы данных", "en": "Could not find data files", "ua": "Не вдалося знайти файли даних", "ja": "データファイルが見つかりませんでした"},
}

def main():
    print("🔧 Добавление ~75 ключей для gui...\n")
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
