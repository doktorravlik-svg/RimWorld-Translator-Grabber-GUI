#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт массового исправления переводов в gui/ файлах
"""

import os
import re

# ✅ ИСПРАВЛЕНО: Динамическое определение корня проекта
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUI_DIR = os.path.join(BASE, "gui")

def fix_file(filename, replacements):
    """Исправить файл заменив хардкод на tr()"""
    filepath = os.path.join(BASE, filename)
    if not os.path.exists(filepath):
        print(f"❌ Не найден: {filename}")
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    applied = 0

    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            applied += 1
            print(f"  ✅ {old[:60]}...")

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ {filename}: {applied} исправлений\n")
        return applied
    else:
        print(f"⚠️ {filename}: нет изменений\n")
        return 0

def main():
    print("🔧 Массовое исправление gui/ файлов...\n")
    total = 0

    # 1. gui_file_colors.py
    total += fix_file("gui\\components\\gui_file_colors.py", [
        ('"Полностью переведён"', 'tr("filecolor_complete", "Полностью переведён")'),
        ('"Частичный перевод"', 'tr("filecolor_partial", "Частичный перевод")'),
        ('"Ошибка в файле"', 'tr("filecolor_error", "Ошибка в файле")'),
        ('"Не переведён"', 'tr("filecolor_empty", "Не переведён")'),
        ('"Файл отсутствует"', 'tr("filecolor_missing", "Файл отсутствует")'),
    ])

    # 2. gui_tab_translation.py
    total += fix_file("gui\\tabs\\gui_tab_translation.py", [
        ('messagebox.askyesno("Отмена перевода", "Вы уверены, что хотите отменить перевод?")',
         'messagebox.askyesno(tr("translation_cancel_title", "Отмена перевода"), tr("translation_cancel_confirm", "Вы уверены, что хотите отменить перевод?"))'),
    ])

    # 3. gui_tab_verification.py
    total += fix_file("gui\\tabs\\gui_tab_verification.py", [
        ('messagebox.showwarning("Предупреждение", "Нет результатов для экспорта")',
         'from gui.gui_i18n import tr\n            messagebox.showwarning(tr("gui_warning", "Предупреждение"), tr("verification_no_results", "Нет результатов для экспорта"))'),
        ('messagebox.showinfo("Успех", "Отчёт сохранён")',
         'messagebox.showinfo(tr("gui_success", "Успех"), tr("verification_export_ok", "Отчёт сохранён"))'),
        ('messagebox.showerror("Ошибка", "Ошибка сохранения отчёта")',
         'messagebox.showerror(tr("gui_error", "Ошибка"), tr("verification_export_error", "Ошибка сохранения отчёта"))'),
    ])

    # 4. gui_tab_duplicates.py
    total += fix_file("gui\\tabs\\gui_tab_duplicates.py", [
        ('messagebox.showwarning("Предупреждение", "Выберите существующую папку с модами")',
         'from gui.gui_i18n import tr\n            messagebox.showwarning(tr("gui_warning", "Предупреждение"), tr("duplicates_no_mods_warning", "Выберите существующую папку с модами"))'),
        ('messagebox.showwarning("Предупреждение", "Выберите хотя бы одну группу дубликатов")',
         'messagebox.showwarning(tr("gui_warning", "Предупреждение"), tr("duplicates_no_selection_warning", "Выберите хотя бы одну группу дубликатов"))'),
        ('messagebox.showwarning("Предупреждение", "Выберите папки модов и вывода")',
         'messagebox.showwarning(tr("gui_warning", "Предупреждение"), tr("duplicates_no_paths_warning", "Выберите папки модов и вывода"))'),
    ])

    # 5. gui_tab_settings.py
    total += fix_file("gui\\tabs\\gui_tab_settings.py", [
        ('messagebox.showinfo("OK", "Шрифты сброшены.")',
         'messagebox.showinfo(tr("settings_ok", "OK"), tr("settings_fonts_reset_ok", "Шрифты сброшены."))'),
        ('messagebox.showerror("Error", str(e))',
         'messagebox.showerror(tr("settings_error", "Ошибка"), str(e))'),
        ('messagebox.showinfo("OK", "Цвета сброшены.")',
         'messagebox.showinfo(tr("settings_ok", "OK"), tr("settings_colors_reset_ok", "Цвета сброшены."))'),
        ('messagebox.showerror("Ошибка", str(e))',
         'messagebox.showerror(tr("settings_error", "Ошибка"), str(e))'),
        ('messagebox.askyesno("Подтверждение", "Сбросить все настройки к значениям по умолчанию?")',
         'messagebox.askyesno(tr("settings_reset_confirm", "Подтверждение"), tr("settings_reset_confirm", "Сбросить все настройки к значениям по умолчанию?"))'),
        ('messagebox.showinfo("Успех", "Настройки сброшены")',
         'messagebox.showinfo(tr("gui_success", "Успех"), tr("settings_reset_ok", "Настройки сброшены"))'),
    ])

    # 6. gui_components.py
    total += fix_file("gui\\components\\gui_components.py", [
        ('messagebox.showinfo("Сохранить лог"',
         'from gui.gui_i18n import tr\n            messagebox.showinfo(tr("logpanel_save_title", "Сохранить лог")'),
        ('messagebox.showinfo("Успех"',
         'messagebox.showinfo(tr("gui_success", "Успех")'),
        ('messagebox.showerror("Ошибка"',
         'messagebox.showerror(tr("gui_error", "Ошибка")'),
        ('messagebox.showinfo("Поиск"',
         'messagebox.showinfo(tr("logpanel_search_not_found", "Поиск")'),
    ])

    print(f"\n✨ Всего исправлено: {total}")

if __name__ == "__main__":
    main()
