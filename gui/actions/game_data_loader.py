# gui/actions/game_data_loader.py
"""
Загрузка данных игры для RimWorld Translator Grabber.
"""

import os
import threading
from tkinter import filedialog, messagebox

from gui.gui_i18n import tr


class GameDataLoader:
    """
    Загрузчик официальных данных игры.

    Args:
        config: Словарь конфигурации
        log_callback: Функция логирования
        status_callback: Функция обновления статуса
        progress_callbacks: Объект с методами start/stop_progress
        save_callback: Функция сохранения конфига
        game_data_processor: Модуль game_data_processor
    """

    def __init__(
        self,
        config: dict,
        log_callback=None,
        status_callback=None,
        progress_callbacks=None,
        save_callback=None,
        game_data_processor=None,
    ):
        self.config = config
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.progress_callbacks = progress_callbacks
        self.save_callback = save_callback
        self.game_data_processor = game_data_processor

    def prompt_and_load(self, parent=None):
        """
        Запросить путь к игре и загрузить данные.

        Args:
            parent: Родительское окно для диалогов
        """
        game_path = filedialog.askdirectory(
            title=tr("game_loader_select_rimworld", "Выберите папку с RimWorld"), parent=parent
        )
        if not game_path:
            return

        # ✅ ИСПРАВЛЕНО: Спрашиваем язык для загрузки
        from tkinter.simpledialog import askstring

        lang = askstring(
            "Выбор языка",
            "Введите язык для загрузки справочника\n(по умолчанию Russian):",
            initialvalue=self.config.get("target_language", "Russian"),
            parent=parent,
        )

        if not lang:
            lang = "Russian"  # Fallback

        # Предварительная проверка: ищем папку Data
        data_path = self._find_game_data_path(game_path)

        if not data_path:
            self._show_data_folder_error(game_path)
            return

        # Если нашли в родительской папке, предлагаем использовать её
        if data_path != os.path.join(game_path, "Data"):
            result = messagebox.askyesno(
                "Папка Data найдена",
                f"В указанной папке нет Data, но найдена в:\n{data_path}\n\n"
                f"Использовать эту папку?",
                parent=parent,
            )
            if result:
                game_path = os.path.dirname(data_path)
            else:
                return

        thread = threading.Thread(target=self._perform_load, args=(game_path, lang))
        thread.daemon = True
        thread.start()

    def _find_game_data_path(self, user_path: str) -> str | None:
        """
        Ищет папку Data в указанной директории или выше.

        Проверяет:
        1. user_path/Data
        2. user_path/../Data
        3. user_path/../../Data
        4. user_path/../../../Data
        """
        variants = [
            os.path.join(user_path, "Data"),
            os.path.join(user_path, "..", "Data"),
            os.path.join(user_path, "..", "..", "Data"),
            os.path.join(user_path, "..", "..", "..", "Data"),
        ]

        for variant in variants:
            normalized = os.path.normpath(variant)
            if os.path.exists(normalized):
                core_path = os.path.join(normalized, "Core")
                if os.path.exists(core_path):
                    return normalized

        return None

    def _show_data_folder_error(self, game_path: str):
        """Показывает подробное сообщение об ошибке с подсказками"""
        if self.log_callback:
            self.log_callback(f"❌ Не удалось найти папку Data в: {game_path}")
            self.log_callback(f"   Ожидаемая структура: {game_path}/Data/Core/Languages/")

        suggestions = []

        if "RimWorldWin64" in game_path or "RimWorldWin64_Data" in game_path:
            suggestions.append(
                "⚠️ Вы указали папку с exe-файлом!\n"
                "   Нужно указать папку выше (где лежит RimWorldWin64.exe)"
            )

        parent_path = os.path.dirname(game_path)
        if os.path.exists(os.path.join(parent_path, "Data")):
            suggestions.append(
                f"✅ Папка Data найдена в: {parent_path}\n   Укажите эту папку вместо {game_path}"
            )

        message = (
            "Не удалось найти папку Data.\n\n"
            f"Проверьте путь:\n{game_path}\n\n"
            "Ожидаемая структура:\n"
            f"  {game_path}/Data/Core/Languages/Russian/\n\n"
        )

        if suggestions:
            message += "💡 Подсказки:\n" + "\n\n".join(suggestions)
        else:
            message += (
                "Возможно, вы указали:\n"
                "  • Папку с exe-файлом (RimWorldWin64)\n"
                "  • Папку с модом вместо папки игры\n"
                "  • Неправильный путь\n\n"
                "Нужно указать папку, где лежит RimWorldWin64.exe"
            )

        messagebox.showwarning(tr("editor_warning", "Предупреждение"), message)

    def _perform_load(self, game_path: str, lang: str = "Russian"):
        """Выполнение загрузки данных игры"""
        try:
            data_path = self._find_game_data_path(game_path)
            if not data_path:
                if self.log_callback:
                    self.log_callback(f"❌ Ошибка: папка Data не найдена в {game_path}")
                if self.status_callback:
                    self.status_callback("Ошибка: данные не найдены")
                self._show_data_folder_error(game_path)
                return

            # ✅ ИСПРАВЛЕНО: Используем выбранный язык
            manager = self.game_data_processor.GameReferenceManager(
                game_path=game_path,
                lang=lang,
            )

            if self.status_callback:
                self.status_callback("Загрузка данных...")
            if self.progress_callbacks:
                self.progress_callbacks.start()

            success = manager.load_all_official_data()

            if success:
                db_size = len(manager.reference_db)
                symbols_count = len(manager.special_symbols)
                
                # ✅ ИСПРАВЛЕНО: Сохраняем официальные переводы в базу данных
                try:
                    from translation_db import get_translation_db
                    db = get_translation_db(manager.lang)
                    if db:
                        added_glossary = 0
                        added_translations = 0
                        for key, val in manager.reference_db.items():
                            if key and val:
                                mod_name = manager.key_to_mod.get(key, "unknown")
                                db.add_glossary_term(key, val, category="auto", 
                                                   description=f"Официальный перевод из {manager.lang}", mod_name=mod_name)
                                added_glossary += 1
                                db.add_translation(
                                    key=key,
                                    original=key,
                                    translated=val,
                                    file_name="",
                                    mod_name=mod_name,
                                    source_lang="English",
                                    target_lang=manager.lang,
                                )
                                added_translations += 1
                        if self.log_callback:
                            self.log_callback(f"✅ Добавлено в глоссарий: {added_glossary} терминов из игры")
                            self.log_callback(f"✅ Добавлено в translations: {added_translations} записей из игры")
                except Exception as e:
                    if self.log_callback:
                        self.log_callback(f"⚠️ Ошибка сохранения в базу: {e}")
                
                if self.log_callback:
                    self.log_callback(f"Загружено {db_size} строк из официальных DLC")
                    self.log_callback(f"Найдено {symbols_count} специальных символов/тегов")

                self.config["game_path"] = game_path
                if self.save_callback:
                    self.save_callback()

                if self.status_callback:
                    self.status_callback(
                        f"Данные загруены: {db_size} строк, {symbols_count} символов"
                    )

                messagebox.showinfo(
                    "Успех",
                    f"Официальные данные загруены:\n"
                    f"- Строк: {db_size}\n"
                    f"- Спецсимволов: {symbols_count}",
                )
            else:
                if self.log_callback:
                    self.log_callback(f"❌ Не удалось загрузить данные из: {data_path}")
                if self.status_callback:
                    self.status_callback("Ошибка: данные не найдены")
                messagebox.showwarning(
                    "Предупреждение",
                    "Не удалось найти файлы данных.\n"
                    "Убедитесь, что игра установлена корректно.\n\n"
                    f"Проверен путь:\n{data_path}",
                )

        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Ошибка загрузки данных: {e}")
            if self.status_callback:
                self.status_callback(f"Ошибка: {e}")
            messagebox.showerror(
                tr("editor_error", "Ошибка"),
                tr("game_loader_load_error", "Не удалось загрузить данные игры:\n{error}").format(
                    error=e
                ),
            )
        finally:
            if self.progress_callbacks:
                self.progress_callbacks.stop()
