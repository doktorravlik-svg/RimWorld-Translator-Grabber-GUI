#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Добавление ключей для зависимостей и вкладок"""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"

NEW_KEYS = {
    # Статистика зависимостей
    "deps_stat_total": {"ru": "Всего переводов", "en": "Total translations", "ua": "Всього перекладів", "ja": "翻訳合計"},
    "deps_stat_uptodate": {"ru": "Актуальных", "en": "Up to date", "ua": "Актуальних", "ja": "最新"},
    "deps_stat_outdated": {"ru": "Устаревших", "en": "Outdated", "ua": "Застарілих", "ja": "古い"},
    "deps_stat_version_mismatch": {"ru": "Несовпадение версий", "en": "Version mismatch", "ua": "Невідповідність версій", "ja": "バージョン不一致"},
    "deps_stat_missing_parent": {"ru": "Родитель не найден", "en": "Parent not found", "ua": "Батьківський не знайдено", "ja": "親が見つからない"},
    "deps_stat_custom": {"ru": "Пользовательских", "en": "Custom", "ua": "Користувацьких", "ja": "カスタム"},
    "deps_stat_standalone": {"ru": "Отдельных модов-переводов", "en": "Standalone translation mods", "ua": "Окремих модів-перекладів", "ja": "スタンドアロン翻訳MOD"},
    "deps_stat_embedded": {"ru": "Встроенных переводов", "en": "Embedded translations", "ua": "Вбудованих перекладів", "ja": "埋め込み翻訳"},
    
    # Отчёты зависимостей
    "deps_report_title": {"ru": "ОТЧЁТ О ЗАВИСИМОСТЯХ ПЕРЕВОДОВ RIMWORLD МОДОВ", "en": "RIMWORLD MOD TRANSLATION DEPENDENCY REPORT", "ua": "ЗВІТ ПРО ЗАЛЕЖНОСТІ ПЕРЕКЛАДІВ МОДІВ RIMWORLD", "ja": "RIMWORLD MOD翻訳依存関係レポート"},
    "deps_report_statistics": {"ru": "СТАТИСТИКА", "en": "STATISTICS", "ua": "СТАТИСТИКА", "ja": "統計"},
    "deps_report_deaggregation": {"ru": "ДЕЗАГРЕГАЦИЯ ПО ПЕРЕВОДАМ", "en": "TRANSLATION BREAKDOWN", "ua": "ДЕЗАГРЕГАЦІЯ ПО ПЕРЕКЛАДАМ", "ja": "翻訳内訳"},
    "deps_report_end": {"ru": "КОНЕЦ ОТЧЁТА", "en": "END OF REPORT", "ua": "КІНЕЦЬ ЗВІТУ", "ja": "レポート終了"},
    "deps_report_mods_folder": {"ru": "Папка модов", "en": "Mods folder", "ua": "Папка модів", "ja": "MODフォルダー"},
    "deps_report_translation": {"ru": "Перевод", "en": "Translation", "ua": "Переклад", "ja": "翻訳"},
    "deps_report_version": {"ru": "Версия", "en": "Version", "ua": "Версія", "ja": "バージョン"},
    "deps_report_type": {"ru": "Тип", "en": "Type", "ua": "Тип", "ja": "タイプ"},
    "deps_report_status": {"ru": "Статус", "en": "Status", "ua": "Статус", "ja": "ステータス"},
    "deps_report_parent_mod": {"ru": "Родительский мод", "en": "Parent mod", "ua": "Батьківський мод", "ja": "親MOD"},
    "deps_report_parent_version": {"ru": "Версия родителя", "en": "Parent version", "ua": "Версія батьківського", "ja": "親バージョン"},
    "deps_report_compatibility": {"ru": "Совместимость", "en": "Compatibility", "ua": "Сумісність", "ja": "互換性"},
    "deps_report_yes": {"ru": "Да", "en": "Yes", "ua": "Так", "ja": "はい"},
    "deps_report_no": {"ru": "Нет", "en": "No", "ua": "Ні", "ja": "いいえ"},
    "deps_report_issues": {"ru": "Проблемы", "en": "Issues", "ua": "Проблеми", "ja": "問題"},
    
    # Вкладки
    "translation_select_col": {"ru": "✓", "en": "✓", "ua": "✓", "ja": "✓"},
    "tab_duplicatess": {"ru": "🔄 Дубликаты", "en": "🔄 Duplicates", "ua": "🔄 Дублікати", "ja": "🔄 重複"},
}

def main():
    print("🔧 Добавление ключей зависимостей и вкладок...\n")
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
