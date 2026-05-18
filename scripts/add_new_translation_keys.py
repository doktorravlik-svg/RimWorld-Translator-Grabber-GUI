#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт добавления новых ключей переводов во все файлы locales.
"""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"

# Новые ключи для добавления
NEW_KEYS = {
    # Редактор - панель инструментов
    "editor_toolbar_file": {
        "ru": "📁 Файл",
        "en": "📁 File",
        "ua": "📁 Файл",
        "ja": "📁 ファイル",
    },
    "editor_toolbar_edit": {
        "ru": "✍️ Ред.",
        "en": "✍️ Edit",
        "ua": "✍️ Ред.",
        "ja": "✍️ 編集",
    },
    "editor_toolbar_ops": {
        "ru": "🔧 Опер.",
        "en": "🔧 Ops",
        "ua": "🔧 Опер.",
        "ja": "🔧 操作",
    },
    "editor_toolbar_check": {
        "ru": "✅ Проверка",
        "en": "✅ Check",
        "ua": "✅ Перевірка",
        "ja": "✅ 確認",
    },
    "editor_toolbar_tools": {
        "ru": "🛠️ Инстр.",
        "en": "🛠️ Tools",
        "ua": "🛠️ Інстр.",
        "ja": "🛠️ ツール",
    },
    # Массовое редактирование
    "editor_mass_apply": {
        "ru": "✅ Применить",
        "en": "✅ Apply",
        "ua": "✅ Застосувати",
        "ja": "✅ 適用",
    },
    "editor_mass_clear": {
        "ru": "🗑️ Очистить выбранные",
        "en": "🗑️ Clear selected",
        "ua": "🗑️ Очистити вибрані",
        "ja": "🗑️ 選択をクリア",
    },
    "editor_mass_cancel": {
        "ru": "❌ Отмена",
        "en": "❌ Cancel",
        "ua": "❌ Скасувати",
        "ja": "❌ キャンセル",
    },
    # Components
    "log_search_next_btn": {"ru": "➡️", "en": "➡️", "ua": "➡️", "ja": "➡️"},
    "mods_select_col": {"ru": "✓", "en": "✓", "ua": "✓", "ja": "✓"},
    # Статусы модов
    "translated_status": {
        "ru": "Переведён",
        "en": "Translated",
        "ua": "Перекладено",
        "ja": "翻訳済み",
    },
    "partial_status": {
        "ru": "Частично",
        "en": "Partial",
        "ua": "Частково",
        "ja": "部分的",
    },
    "no_translations": {
        "ru": "Нет переводов",
        "en": "No translations",
        "ua": "Немає перекладів",
        "ja": "翻訳なし",
    },
    # Shortcuts - заголовки групп
    "shortcuts_group_file": {
        "ru": "📁 Файл",
        "en": "📁 File",
        "ua": "📁 Файл",
        "ja": "📁 ファイル",
    },
    "shortcuts_group_tools": {
        "ru": "🔍 Инструменты",
        "en": "🔍 Tools",
        "ua": "🔍 Інструменти",
        "ja": "🔍 ツール",
    },
    "shortcuts_group_tabs": {
        "ru": "📑 Вкладки",
        "en": "📑 Tabs",
        "ua": "📑 Вкладки",
        "ja": "📑 タブ",
    },
    "shortcuts_group_editor": {
        "ru": "✏️ Редактор",
        "en": "✏️ Editor",
        "ua": "✏️ Редактор",
        "ja": "✏️ エディター",
    },
    "shortcuts_group_debug": {
        "ru": "🔧 Отладка",
        "en": "🔧 Debug",
        "ua": "🔧 Налагодження",
        "ja": "🔧 デバッグ",
    },
    # About - возможности
    "about_feature_1": {
        "ru": "🌐 Автоматический перевод модов через Google Translate",
        "en": "🌐 Automatic mod translation via Google Translate",
        "ua": "🌐 Автоматичний переклад модів через Google Translate",
        "ja": "🌐 Google翻訳によるMOD自動翻訳",
    },
    "about_feature_2": {
        "ru": "✅ Верификация модов — проверка зависимостей и конфликтов",
        "en": "✅ Mod verification — dependency and conflict checks",
        "ua": "✅ Верифікація модів — перевірка залежностей та конфліктів",
        "ja": "✅ MODの検証 — 依存関係と競合のチェック",
    },
    "about_feature_3": {
        "ru": "🔄 Поиск и слияние дубликатов переводов",
        "en": "🔄 Find and merge duplicate translations",
        "ua": "🔄 Пошук та злиття дублікатів перекладів",
        "ja": "🔄 重複翻訳の検索と統合",
    },
    "about_feature_4": {
        "ru": "✏️ Полноценный редактор с Undo/Redo, поиском и заменой",
        "en": "✏️ Full-featured editor with Undo/Redo, find and replace",
        "ua": "✏️ Повноцінний редактор з Undo/Redo, пошуком та заміною",
        "ja": "✏️ 元に戻す/やり直し、検索と置換を備えた本格エディター",
    },
    "about_feature_5": {
        "ru": "🔤 Проверка орфографии для 5 языков",
        "en": "🔤 Spell checking for 5 languages",
        "ua": "🔤 Перевірка орфографії для 5 мов",
        "ja": "🔤 5言語のスペルチェック",
    },
    "about_feature_6": {
        "ru": "📖 Глоссарий терминов RimWorld (60+ терминов)",
        "en": "📖 RimWorld terms glossary (60+ terms)",
        "ua": "📖 Глосарій термінів RimWorld (60+ термінів)",
        "ja": "📖 RimWorld用語集（60以上の用語）",
    },
    "about_feature_7": {
        "ru": "📊 Diff-сравнение с оригиналом (посимвольная подсветка)",
        "en": "📊 Diff comparison with original (character-level highlighting)",
        "ua": "📊 Diff-порівняння з оригіналом (підсвічування на рівні символів)",
        "ja": "📊 原文とのDiff比較（文字単位ハイライト）",
    },
    "about_feature_8": {
        "ru": "📦 Управление модами — включение/отключение",
        "en": "📦 Mod management — enable/disable",
        "ua": "📦 Управління модами — увімкнення/вимкнення",
        "ja": "📦 MOD管理 — 有効化/無効化",
    },
    "about_feature_9": {
        "ru": "📝 Фильтры тегов — настройка извлекаемых тегов XML",
        "en": "📝 Tag filters — configure extracted XML tags",
        "ua": "📝 Фільтри тегів — налаштування XML тегів для вилучення",
        "ja": "📝 タグフィルター — 抽出するXMLタグの設定",
    },
    "about_feature_10": {
        "ru": "🔗 Анализ дерева зависимостей переводов",
        "en": "🔗 Translation dependency tree analysis",
        "ua": "🔗 Аналіз дерева залежностей перекладів",
        "ja": "🔗 翻訳依存関係ツリーの分析",
    },
    "about_feature_11": {
        "ru": "🎨 8 тем оформления с адаптивными иконками",
        "en": "🎨 8 themes with adaptive icons",
        "ua": "🎨 8 тем оформлення з адаптивними іконками",
        "ja": "🎨 8つのテーマとアダプティブアイコン",
    },
    "about_feature_12": {
        "ru": "🌍 6 языков интерфейса (RU, EN, DE, PL, JA, UA)",
        "en": "🌍 6 interface languages (RU, EN, DE, PL, JA, UA)",
        "ua": "🌍 6 мов інтерфейсу (RU, EN, DE, PL, JA, UA)",
        "ja": "🌍 6つのインターフェース言語（RU、EN、DE、PL、JA、UA）",
    },
    "about_feature_13": {
        "ru": "💾 Автосохранение и резервные копии",
        "en": "💾 Auto-save and backups",
        "ua": "💾 Автозбереження та резервні копії",
        "ja": "💾 自動保存とバックアップ",
    },
    "about_feature_14": {
        "ru": "🔧 Debug-режим с логированием",
        "en": "🔧 Debug mode with logging",
        "ua": "🔧 Debug-режим з логуванням",
        "ja": "🔧 ロギング付きデバッグモード",
    },
}


def main():
    print("🔧 Добавление новых ключей переводов...\n")

    languages = ["ru", "en", "ua", "ja"]

    for lang in languages:
        file_path = LOCALES_DIR / f"{lang}.json"
        if not file_path.exists():
            print(f"❌ Файл не найден: {file_path}")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Извлекаем переводы
        lang_code = list(data.keys())[0]
        translations = data[lang_code]

        # Добавляем новые ключи
        added = 0
        for key, lang_data in NEW_KEYS.items():
            if key not in translations:
                translations[key] = lang_data[lang]
                added += 1

        # Сохраняем
        data[lang_code] = translations
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ {lang}.json: добавлено {added} новых ключей (всего: {len(translations)})")

    print("\n✨ Готово!")


if __name__ == "__main__":
    main()
