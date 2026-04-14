#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт автоматического исправления переводов в gui_translation_editor.py
"""

import re

FILE_PATH = "f:\\Games\\Rimprog\\new_folder\\gui\\tabs\\gui_translation_editor.py"

# Исправления: (старый текст, новый текст с self.tr())
FIXES = [
    # MessageBox заголовки
    ('messagebox.showinfo(\n                tr("editor_translation_saved", "Перевод сохранён"),\n                f"Сохранено {len(self.entries)} записей"\n            )',
     'messagebox.showinfo(\n                self.tr("editor_translation_saved", "Перевод сохранён"),\n                self.tr("editor_translation_saved_msg", "Сохранено {count} записей").format(count=len(self.entries))\n            )'),
    
    # Проверка качества - заголовки
    ('messagebox.showinfo("✅ Проверка качества", report)',
     'messagebox.showinfo(self.tr("editor_quality_check_ok", "✅ Проверка качества"), report)'),
    ('messagebox.showwarning("⚠️ Проверка качества", report)',
     'messagebox.showwarning(self.tr("editor_quality_check_warn", "⚠️ Проверка качества"), report)'),
    
    # Орфография - заголовки
    ('messagebox.showwarning("🔤 Орфография", report)',
     'messagebox.showwarning(self.tr("editor_spellcheck_title", "🔤 Орфография"), report)'),
    
    # Выбор языка для проверки
    ('dlg.title("Выбор языка")',
     'dlg.title(self.tr("editor_spellcheck_title", "Выбор языка"))'),
    
    # Diff legend
    ('ttk.Label(legend_frame, text="🟥 Удалено", font=("Segoe UI", 9))',
     'ttk.Label(legend_frame, text=self.tr("editor_diff_deleted", "🟥 Удалено"), font=("Segoe UI", 9))'),
    ('ttk.Label(legend_frame, text="🟨 Изменено", font=("Segoe UI", 9))',
     'ttk.Label(legend_frame, text=self.tr("editor_diff_modified", "🟨 Изменено"), font=("Segoe UI", 9))'),
    ('ttk.Label(legend_frame, text="🟩 Добавлено", font=("Segoe UI", 9))',
     'ttk.Label(legend_frame, text=self.tr("editor_diff_added", "🟩 Добавлено"), font=("Segoe UI", 9))'),
    
    # Glossary columns
    ('self.glossary_tree.heading("term", text="Термин")',
     'self.glossary_tree.heading("term", text=self.tr("editor_glossary_term_col", "Термин"))'),
    ('self.glossary_tree.heading("translation", text="Перевод")',
     'self.glossary_tree.heading("translation", text=self.tr("editor_glossary_translation_col", "Перевод"))'),
    ('self.glossary_tree.heading("category", text="Категория")',
     'self.glossary_tree.heading("category", text=self.tr("editor_glossary_category_col", "Категория"))'),
    ('self.glossary_tree.heading("description", text="Описание")',
     'self.glossary_tree.heading("description", text=self.tr("editor_glossary_description_col", "Описание"))'),
    
    # History columns
    ('self.history_tree.heading("version", text="Версия")',
     'self.history_tree.heading("version", text=self.tr("editor_history_version_col", "Версия"))'),
    ('self.history_tree.heading("entries", text="Записей")',
     'self.history_tree.heading("entries", text=self.tr("editor_history_entries_col", "Записей"))'),
    ('self.history_tree.heading("translated", text="Переведено")',
     'self.history_tree.heading("translated", text=self.tr("editor_history_translated_col", "Переведено"))'),
    ('self.history_tree.heading("date", text="Дата")',
     'self.history_tree.heading("date", text=self.tr("editor_history_date_col", "Дата"))'),
    
    # History buttons
    ('ttk.Button(btn_frame, text="💾 Сохранить версию", command=save_version)',
     'ttk.Button(btn_frame, text=self.tr("editor_save_version_btn", "💾 Сохранить версию"), command=save_version)'),
    ('ttk.Button(btn_frame, text="↩️ Восстановить", command=restore_version)',
     'ttk.Button(btn_frame, text=self.tr("editor_restore_version_btn", "↩️ Восстановить"), command=restore_version)'),
    
    # Suggestions columns
    ('self.suggestions_tree.heading("key", text="Ключ")',
     'self.suggestions_tree.heading("key", text=self.tr("editor_suggestions_key_col", "Ключ"))'),
    ('self.suggestions_tree.heading("suggestion", text="Предложение")',
     'self.suggestions_tree.heading("suggestion", text=self.tr("editor_suggestions_suggestion_col", "Предложение"))'),
    ('self.suggestions_tree.heading("confidence", text="Уверенность")',
     'self.suggestions_tree.heading("confidence", text=self.tr("editor_suggestions_confidence_col", "Уверенность"))'),
    ('self.suggestions_tree.heading("source", text="Источник")',
     'self.suggestions_tree.heading("source", text=self.tr("editor_suggestions_source_col", "Источник"))'),
    ('self.suggestions_tree.heading("current", text="Текущее")',
     'self.suggestions_tree.heading("current", text=self.tr("editor_suggestions_current_col", "Текущее"))'),
    
    # File selector
    ('ttk.Button(left_frame, text="📂 Обзор...", command=self.browse_file)',
     'ttk.Button(left_frame, text=self.tr("editor_btn_browse", "📂 Обзор..."), command=self.browse_file)'),
    ('ttk.Button(left_frame, text="📁 Выбрать из модов", command=self.choose_from_mods)',
     'ttk.Button(left_frame, text=self.tr("editor_btn_choose_from_mods", "📁 Выбрать из модов"), command=self.choose_from_mods)'),
    ('ttk.Label(right_frame, text="🕐 Последние:")',
     'ttk.Label(right_frame, text=self.tr("editor_recent_files_label", "🕐 Последние:"))'),
    ('ttk.Button(right_frame, text="🕐 Открыть", command=self.open_recent)',
     'ttk.Button(right_frame, text=self.tr("editor_btn_open_recent", "🕐 Открыть"), command=self.open_recent)'),
    ('ttk.Button(btn_frame, text="✏️ Открыть редактор", command=self.open_editor)',
     'ttk.Button(btn_frame, text=self.tr("editor_btn_open_editor", "✏️ Открыть редактор"), command=self.open_editor)'),
    ('ttk.Button(btn_frame, text="🔄 Обновить", command=self.refresh_list)',
     'ttk.Button(btn_frame, text=self.tr("editor_btn_refresh", "🔄 Обновить"), command=self.refresh_list)'),
    
    # Legend
    ('ttk.Label(legend_frame, text="✅ Полностью переведён")',
     'ttk.Label(legend_frame, text=self.tr("editor_legend_complete", "✅ Полностью переведён"))'),
    ('ttk.Label(legend_frame, text="⚠️ Частичный перевод")',
     'ttk.Label(legend_frame, text=self.tr("editor_legend_partial", "⚠️ Частичный перевод"))'),
    ('ttk.Label(legend_frame, text="❌ Ошибка в файле")',
     'ttk.Label(legend_frame, text=self.tr("editor_legend_error", "❌ Ошибка в файле"))'),
    ('ttk.Label(legend_frame, text="⬜ Не переведён")',
     'ttk.Label(legend_frame, text=self.tr("editor_legend_empty", "⬜ Не переведён"))'),
    ('ttk.Label(legend_frame, text="➖ Файл отсутствует")',
     'ttk.Label(legend_frame, text=self.tr("editor_legend_missing", "➖ Файл отсутствует"))'),
    
    # File list columns
    ('self.file_tree.heading("path", text="Путь")',
     'self.file_tree.heading("path", text=self.tr("editor_file_list_path_col", "Путь"))'),
    ('self.file_tree.heading("entries", text="Записей")',
     'self.file_tree.heading("entries", text=self.tr("editor_file_list_entries_col", "Записей"))'),
    ('self.file_tree.heading("status", text="Статус")',
     'self.file_tree.heading("status", text=self.tr("editor_file_list_status_col", "Статус"))'),
    
    # Context menu
    ('ctx_menu.add_command(label="✏️ Открыть в редакторе", command=open_in_editor)',
     'ctx_menu.add_command(label=self.tr("editor_ctx_open", "✏️ Открыть в редакторе"), command=open_in_editor)'),
    ('ctx_menu.add_command(label="📋 Копировать путь", command=copy_path)',
     'ctx_menu.add_command(label=self.tr("editor_ctx_copy_path", "📋 Копировать путь"), command=copy_path)'),
    ('ctx_menu.add_command(label="📂 Открыть папку", command=open_folder)',
     'ctx_menu.add_command(label=self.tr("editor_ctx_open_folder", "📂 Открыть папку"), command=open_folder)'),
    ('ctx_menu.add_command(label="📊 Информация", command=show_info)',
     'ctx_menu.add_command(label=self.tr("editor_ctx_info", "📊 Информация"), command=show_info)'),
    ('ctx_menu.add_command(label="🔄 Обновить список", command=refresh)',
     'ctx_menu.add_command(label=self.tr("editor_ctx_refresh_list", "🔄 Обновить список"), command=refresh)'),
]


def main():
    print("🔧 Чтение файла...")
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    applied = 0
    
    print("🔧 Применение исправлений...")
    for old, new in FIXES:
        if old in content:
            content = content.replace(old, new)
            applied += 1
            print(f"  ✅ Исправлено: {old[:50]}...")
        else:
            print(f"  ⚠️ Не найдено: {old[:50]}...")
    
    if content != original:
        print(f"\n🔧 Сохранение файла ({applied} исправлений)...")
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ Файл сохранён!")
    else:
        print("\n⚠️ Исправления не применены")


if __name__ == "__main__":
    main()
