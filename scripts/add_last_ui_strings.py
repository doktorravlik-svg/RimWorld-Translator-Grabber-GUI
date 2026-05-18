#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Добавление последних ~45 ключей для status/toast/history"""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"

NEW_KEYS = {
    # History entries (gui.py add_to_history)
    "gui_history_filters_saved": {"ru": "Настройки фильтров сохранены", "en": "Filters settings saved", "ua": "Налаштування фільтрів збережено", "ja": "フィルター設定が保存されました"},
    "gui_history_whitelist": {"ru": "Whitelist: {count} тегов", "en": "Whitelist: {count} tags", "ua": "Whitelist: {count} тегів", "ja": "ホワイトリスト: {count}タグ"},
    "gui_history_settings_loaded": {"ru": "Настройки загружены", "en": "Settings loaded", "ua": "Налаштування завантажено", "ja": "設定が読み込まれました"},
    "gui_history_verification": {"ru": "Верификация", "en": "Verification", "ua": "Верифікація", "ja": "検証"},
    "gui_history_full_check": {"ru": "Полная проверка", "en": "Full check", "ua": "Повна перевірка", "ja": "完全チェック"},
    "gui_history_translation": {"ru": "Перевод", "en": "Translation", "ua": "Переклад", "ja": "翻訳"},
    "gui_history_duplicate_merge": {"ru": "Слияние дубликатов", "en": "Duplicate merge", "ua": "Злиття дублікатів", "ja": "重複マージ"},
    "gui_history_integrity_check": {"ru": "Проверка целостности", "en": "Integrity check", "ua": "Перевірка цілісності", "ja": "整合性チェック"},
    "gui_history_game_data_load": {"ru": "Загрузка данных игры", "en": "Game data loading", "ua": "Завантаження даних гри", "ja": "ゲームデータ読み込み"},

    # Toast notifications (gui.py)
    "gui_toast_select_mods": {"ru": "Выберите папку с модами!", "en": "Select mods folder!", "ua": "Виберіть папку з модами!", "ja": "MODフォルダーを選択してください！"},
    "gui_toast_verification_started": {"ru": "Верификация запущена...", "en": "Verification started...", "ua": "Верифікація запущена...", "ja": "検証を開始しました..."},
    "gui_toast_select_output": {"ru": "Выберите папку вывода!", "en": "Select output folder!", "ua": "Виберіть папку виводу!", "ja": "出力フォルダーを選択してください！"},
    "gui_toast_translation_started": {"ru": "Перевод запущен: {source} → {target}", "en": "Translation started: {source} → {target}", "ua": "Переклад запущено: {source} → {target}", "ja": "翻訳を開始: {source} → {target}"},

    # Status bar (gui.py)
    "gui_status_data_not_found": {"ru": "Ошибка: данные не найдены", "en": "Error: data not found", "ua": "Помилка: дані не знайдено", "ja": "エラー: データが見つかりません"},
    "gui_status_loading_data": {"ru": "Загрузка данных...", "en": "Loading data...", "ua": "Завантаження даних...", "ja": "データ読み込み中..."},
    "gui_status_data_loaded": {"ru": "Данные загруены: {db} строк, {sym} символов", "en": "Data loaded: {db} lines, {sym} symbols", "ua": "Дані завантажено: {db} рядків, {sym} символів", "ja": "データ読み込み済み: {db}行、{sym}記号"},

    # Handlers status bar (gui_handlers.py)
    "handler_status_ready": {"ru": "Готов", "en": "Ready", "ua": "Готово", "ja": "準備完了"},
    "handler_status_error": {"ru": "Ошибка", "en": "Error", "ua": "Помилка", "ja": "エラー"},
    "handler_verification_progress": {"ru": "Верификация: {progress}/{total} - {message}", "en": "Verification: {progress}/{total} - {message}", "ua": "Верифікація: {progress}/{total} - {message}", "ja": "検証: {progress}/{total} - {message}"},
    "handler_translation_progress": {"ru": "Перевод: {progress}/{total} - {message}", "en": "Translation: {progress}/{total} - {message}", "ua": "Переклад: {progress}/{total} - {message}", "ja": "翻訳: {progress}/{total} - {message}"},
    "handler_merge_progress": {"ru": "Слияние: {progress}/{total} - {message}", "en": "Merge: {progress}/{total} - {message}", "ua": "Злиття: {progress}/{total} - {message}", "ja": "マージ: {progress}/{total} - {message}"},
    "handler_integrity_checking": {"ru": "Проверка целостности...", "en": "Checking integrity...", "ua": "Перевірка цілісності...", "ja": "整合性チェック中..."},

    # Handlers toast notifications
    "handler_toast_verification_complete": {"ru": "Верификация заверена! {total} модов проверено", "en": "Verification complete! {total} mods checked", "ua": "Верифікація завершена! {total} модів перевірено", "ja": "検証完了！{total}MODをチェック"},
    "handler_toast_verification_results": {"ru": "Найдено {errors} ошибок и {warnings} предупреждений", "en": "Found {errors} errors and {warnings} warnings", "ua": "Знайдено {errors} помилок і {warnings} попереджень", "ja": "{errors}エラーと{warnings}警告が見つかりました"},
    "handler_toast_translation_complete": {"ru": "Перевод заверён! {mods} модов, {translations} записей", "en": "Translation complete! {mods} mods, {translations} entries", "ua": "Переклад завершено! {mods} модів, {translations} записів", "ja": "翻訳完了！{mods}MOD、{translations}エントリー"},
    "handler_toast_translation_errors": {"ru": "Перевод заверён с ошибками: {count} ошибок", "en": "Translation complete with errors: {count} errors", "ua": "Переклад завершено з помилками: {count} помилок", "ja": "翻訳完了（エラーあり）: {count}エラー"},

    # Handlers stats panel
    "handler_stats_verification": {"ru": "Верификация", "en": "Verification", "ua": "Верифікація", "ja": "検証"},
    "handler_stats_translation": {"ru": "Перевод", "en": "Translation", "ua": "Переклад", "ja": "翻訳"},

    # Handlers results text
    "handler_results_verification_header": {"ru": "РЕЗУЛЬТАТЫ ВЕРИФИКАЦИИ", "en": "VERIFICATION RESULTS", "ua": "РЕЗУЛЬТАТИ ВЕРИФІКАЦІЇ", "ja": "検証結果"},
    "handler_results_translation_header": {"ru": "РЕЗУЛЬТАТЫ ПЕРЕВОДА", "en": "TRANSLATION RESULTS", "ua": "РЕЗУЛЬТАТИ ПЕРЕКЛАДУ", "ja": "翻訳結果"},
}

def main():
    print("🔧 Добавление последних ~45 ключей...\n")
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
