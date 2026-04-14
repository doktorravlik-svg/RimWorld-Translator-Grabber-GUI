#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт добавления ключей для gui_translation_editor.py
"""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"

# Новые ключи для редактора
NEW_KEYS = {
    # MessageBox заголовки
    "editor_confirm_title": {"ru": "Подтверждение", "en": "Confirmation", "ua": "Підтвердження", "ja": "確認"},
    "editor_translate_empty_confirm": {"ru": "Найдено {count} пустых записей. Создать базовый перевод?", "en": "Found {count} empty entries. Create basic translation?", "ua": "Знайдено {count} порожніх записів. Створити базовий переклад?", "ja": "{count}件の空のレコードが見つかりました。基本翻訳を作成しますか？"},
    "editor_quality_check_ok": {"ru": "✅ Проверка качества", "en": "✅ Quality Check", "ua": "✅ Перевірка якості", "ja": "✅ 品質チェック"},
    "editor_quality_no_issues": {"ru": "Проблем не найдено!\nВсего записей: {total}", "en": "No issues found!\nTotal entries: {total}", "ua": "Проблем не знайдено!\nВсього записів: {total}", "ja": "問題は見つかりませんでした！\n合計エントリー数: {total}"},
    "editor_quality_check_warn": {"ru": "⚠️ Проверка качества", "en": "⚠️ Quality Check", "ua": "⚠️ Перевірка якості", "ja": "⚠️ 品質チェック"},
    "editor_quality_issues_report": {"ru": "Найдено проблем: {count}\n\n{issues}", "en": "Found issues: {count}\n\n{issues}", "ua": "Знайдено проблем: {count}\n\n{issues}", "ja": "見つかった問題: {count}\n\n{issues}"},
    "editor_spellcheck_title": {"ru": "🔤 Проверка орфографии", "en": "🔤 Spell Check", "ua": "🔤 Перевірка орфографії", "ja": "🔤 スペルチェック"},
    "editor_spellcheck_lang": {"ru": "Выберите язык проверки:", "en": "Select spell check language:", "ua": "Виберіть мову перевірки:", "ja": "スペルチェックの言語を選択："},
    "editor_spellcheck_no_dict": {"ru": "Установите: pip install pyspellchecker", "en": "Install: pip install pyspellchecker", "ua": "Встановіть: pip install pyspellchecker", "ja": "インストール: pip install pyspellchecker"},
    "editor_spellcheck_ok": {"ru": "✅ Орфография", "en": "✅ Spelling", "ua": "✅ Орфографія", "ja": "✅ スペル"},
    "editor_spellcheck_report": {"ru": "Найдено ошибок: {count}\n\n{errors}", "en": "Found errors: {count}\n\n{errors}", "ua": "Знайдено помилок: {count}\n\n{errors}", "ja": "見つかったエラー: {count}\n\n{errors}"},
    
    # Diff legend
    "editor_diff_deleted": {"ru": "🟥 Удалено", "en": "🟥 Deleted", "ua": "🟥 Видалено", "ja": "🟥 削除"},
    "editor_diff_modified": {"ru": "🟨 Изменено", "en": "🟨 Modified", "ua": "🟨 Змінено", "ja": "🟨 変更"},
    "editor_diff_added": {"ru": "🟩 Добавлено", "en": "🟩 Added", "ua": "🟩 Додано", "ja": "🟩 追加"},
    
    # Glossary columns
    "editor_glossary_term_col": {"ru": "Термин", "en": "Term", "ua": "Термін", "ja": "用語"},
    "editor_glossary_translation_col": {"ru": "Перевод", "en": "Translation", "ua": "Переклад", "ja": "翻訳"},
    "editor_glossary_category_col": {"ru": "Категория", "en": "Category", "ua": "Категорія", "ja": "カテゴリー"},
    "editor_glossary_description_col": {"ru": "Описание", "en": "Description", "ua": "Опис", "ja": "説明"},
    
    # History columns
    "editor_history_version_col": {"ru": "Версия", "en": "Version", "ua": "Версія", "ja": "バージョン"},
    "editor_history_entries_col": {"ru": "Записей", "en": "Entries", "ua": "Записів", "ja": "エントリー"},
    "editor_history_translated_col": {"ru": "Переведено", "en": "Translated", "ua": "Перекладено", "ja": "翻訳済み"},
    "editor_history_date_col": {"ru": "Дата", "en": "Date", "ua": "Дата", "ja": "日付"},
    
    # History buttons
    "editor_save_version_btn": {"ru": "💾 Сохранить версию", "en": "💾 Save Version", "ua": "💾 Зберегти версію", "ja": "💾 バージョンを保存"},
    "editor_restore_version_btn": {"ru": "↩️ Восстановить", "en": "↩️ Restore", "ua": "↩️ Відновити", "ja": "↩️ 復元"},
    
    # Suggestions columns
    "editor_suggestions_key_col": {"ru": "Ключ", "en": "Key", "ua": "Ключ", "ja": "キー"},
    "editor_suggestions_suggestion_col": {"ru": "Предложение", "en": "Suggestion", "ua": "Пропозиція", "ja": "提案"},
    "editor_suggestions_confidence_col": {"ru": "Уверенность", "en": "Confidence", "ua": "Уверенність", "ja": "信頼度"},
    "editor_suggestions_source_col": {"ru": "Источник", "en": "Source", "ua": "Джерело", "ja": "ソース"},
    "editor_suggestions_current_col": {"ru": "Текущее", "en": "Current", "ua": "Поточне", "ja": "現在"},
    
    # File selector buttons
    "editor_btn_browse": {"ru": "📂 Обзор...", "en": "📂 Browse...", "ua": "📂 Огляд...", "ja": "📂 参照..."},
    "editor_btn_choose_from_mods": {"ru": "📁 Выбрать из модов", "en": "📁 Choose from Mods", "ua": "📁 Вибрати з модів", "ja": "📁 MODから選択"},
    "editor_recent_files_label": {"ru": "🕐 Последние:", "en": "🕐 Recent:", "ua": "🕐 Останні:", "ja": "🕐 最近："},
    "editor_btn_open_recent": {"ru": "🕐 Открыть", "en": "🕐 Open", "ua": "🕐 Відкрити", "ja": "🕐 開く"},
    "editor_btn_open_editor": {"ru": "✏️ Открыть редактор", "en": "✏️ Open Editor", "ua": "✏️ Відкрити редактор", "ja": "✏️ エディターを開く"},
    "editor_btn_refresh": {"ru": "🔄 Обновить", "en": "🔄 Refresh", "ua": "🔄 Оновити", "ja": "🔄 更新"},
    
    # Legend
    "editor_legend_complete": {"ru": "✅ Полностью переведён", "en": "✅ Fully translated", "ua": "✅ Повністю перекладено", "ja": "✅ 完全に翻訳済み"},
    "editor_legend_partial": {"ru": "⚠️ Частичный перевод", "en": "⚠️ Partial translation", "ua": "⚠️ Частковий переклад", "ja": "⚠️ 部分的に翻訳済み"},
    "editor_legend_error": {"ru": "❌ Ошибка в файле", "en": "❌ File error", "ua": "❌ Файл помилки", "ja": "❌ ファイルエラー"},
    "editor_legend_empty": {"ru": "⬜ Не переведён", "en": "⬜ Not translated", "ua": "⬜ Не перекладено", "ja": "⬜ 未翻訳"},
    "editor_legend_missing": {"ru": "➖ Файл отсутствует", "en": "➖ File missing", "ua": "➖ Файл відсутній", "ja": "➖ ファイルなし"},
    
    # File list columns
    "editor_file_list_path_col": {"ru": "Путь", "en": "Path", "ua": "Шлях", "ja": "パス"},
    "editor_file_list_entries_col": {"ru": "Записей", "en": "Entries", "ua": "Записів", "ja": "エントリー"},
    "editor_file_list_status_col": {"ru": "Статус", "en": "Status", "ua": "Статус", "ja": "ステータス"},
    
    # Context menu
    "editor_ctx_open": {"ru": "✏️ Открыть в редакторе", "en": "✏️ Open in Editor", "ua": "✏️ Відкрити в редакторі", "ja": "✏️ エディターで開く"},
    "editor_ctx_copy_path": {"ru": "📋 Копировать путь", "en": "📋 Copy Path", "ua": "📋 Копіювати шлях", "ja": "📋 パスをコピー"},
    "editor_ctx_open_folder": {"ru": "📂 Открыть папку", "en": "📂 Open Folder", "ua": "📂 Відкрити папку", "ja": "📂 フォルダーを開く"},
    "editor_ctx_info": {"ru": "📊 Информация", "en": "📊 Information", "ua": "📊 Інформація", "ja": "📊 情報"},
    "editor_ctx_refresh_list": {"ru": "🔄 Обновить список", "en": "🔄 Refresh List", "ua": "🔄 Оновити список", "ja": "🔄 リストを更新"},
    
    # File info
    "editor_file_info_size": {"ru": "байт", "en": "bytes", "ua": "байт", "ja": "バイト"},
    "editor_file_info_modified": {"ru": "Изменён:", "en": "Modified:", "ua": "Змінено:", "ja": "更新："},
    "editor_file_info_path_label": {"ru": "Путь:", "en": "Path:", "ua": "Шлях:", "ja": "パス："},
    "editor_file_info_entries_label": {"ru": "Записей:", "en": "Entries:", "ua": "Записів:", "ja": "エントリー："},
    "editor_file_info_status_label": {"ru": "Статус:", "en": "Status:", "ua": "Статус:", "ja": "ステータス："},
}


def main():
    print("🔧 Добавление ключей для редактора...\n")

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
