# gui_handlers.py - Оптимизированные обработчики событий
import os
from collections.abc import Callable
from typing import Any

from gui.gui_i18n import tr


class VerificationHandler:
    """Оптимизированный обработчик событий верификации"""

    def __init__(
        self,
        log_callback: Callable,
        status_callback: Callable,
        progress_callback: Callable | None = None,
        result_callback: Callable | None = None,
        batch_result_callback: Callable | None = None,
        stop_progress_callback: Callable | None = None,
    ):
        self.log = log_callback
        self.set_status = status_callback
        self.set_progress = progress_callback
        self.stop_progress = stop_progress_callback
        self.result_callback = result_callback
        self.batch_result_callback = batch_result_callback  # ✅ НОВОЕ: для пакетной вставки
        self._log_buffer: list[str] = []
        self._last_progress_log = 0

    def on_progress(self, progress: int, total: int, message: str):
        """Обработка прогресса верификации (оптимизирована)"""
        self.set_status(f"Верификация: {progress}/{total} - {message}")

        # Логируем только каждые 10% или важные сообщения
        if self.set_progress:
            progress_value = int((progress / max(total, 1)) * 100)
            self.set_progress(progress_value)

            # Логируем только при изменении на 10% или более
            if progress_value - self._last_progress_log >= 10:
                self._last_progress_log = progress_value
                self.log(f"[{progress_value}%] {message}")

    def on_complete(self, result: Any):
        """Обработка завершения верификации"""
        self.set_status(tr("handler_status_ready", "Готов"))
        if self.set_progress:
            self.set_progress(100)

        try:
            total_errors = getattr(result, "total_errors", 0)
            total_conflicts = getattr(result, "total_conflicts", 0)
            total_warnings = getattr(result, "total_warnings", 0)
            total_mods = getattr(result, "total_mods", 0)
            translation_mods = getattr(result, "translation_mods", 0)
            regular_mods = getattr(result, "regular_mods", 0)
            results = getattr(result, "results", [])
            global_conflicts = getattr(result, "global_conflicts", [])

            is_valid = total_errors == 0 and total_conflicts == 0

            if hasattr(self, "show_toast"):
                if is_valid:
                    self.show_toast(
                        f"Верификация завершена! {total_mods} модов проверено", "success"
                    )
                else:
                    self.show_toast(
                        f"Найдено {total_errors} ошибок и {total_warnings} предупреждений",
                        "warning",
                    )

            if hasattr(self, "update_stats"):
                self.update_stats(
                    mods=total_mods,
                    errors=total_errors,
                    warnings=total_warnings,
                    last_action=tr("handler_stats_verification", "Верификация"),
                )

            # ✅ НОВОЕ: Собираем все сообщения в пакет для однопроходной вставки
            result_messages = []

            def add_msg(msg):
                result_messages.append(msg)

            # Заголовок
            add_msg("=" * 50)
            add_msg(tr("handler_results_verification_header", "РЕЗУЛЬТАТЫ ВЕРИФИКАЦИИ"))
            add_msg("=" * 50)
            add_msg(f"Всего модов: {total_mods}")
            add_msg(f"  Переводов: {translation_mods}")
            add_msg(f"  Обычных: {regular_mods}")
            add_msg(f"Ошибок: {total_errors}")
            add_msg(f"Предупреждений: {total_warnings}")
            add_msg(f"Конфликтов: {total_conflicts}")
            add_msg("=" * 50)

            if is_valid:
                self.log("✅ Верификация успешно завершена!")
                add_msg("✅ Верификация успешно завершена!")
            else:
                self.log("⚠️ Верификация завершена с проблемами")
                add_msg("⚠️ Верификация завершена с проблемами")
                add_msg("")

                # Детали по каждому моду с ошибками (✅ БЕЗ лимитов)
                if results:
                    mods_with_issues = [
                        m for m in results if getattr(m, "errors", []) or getattr(m, "warnings", [])
                    ]
                    if mods_with_issues:
                        add_msg(f"📁 Моды с проблемами ({len(mods_with_issues)}):")
                        for mod_result in mods_with_issues:  # ✅ Убран лимит [:20]
                            mod_name = getattr(mod_result, "mod_name", "Unknown")
                            mod_id = getattr(mod_result, "mod_id", "?")
                            errors = getattr(mod_result, "errors", [])
                            warnings_list = getattr(mod_result, "warnings", [])

                            add_msg(f"  ❌ {mod_name} ({mod_id})")
                            for error in errors:  # ✅ Убран лимит [:5]
                                add_msg(f"     • {error}")
                            for warning in warnings_list:  # ✅ Убран лимит [:3]
                                add_msg(f"     ⚠️ {warning}")

                # Глобальные конфликты (✅ БЕЗ лимита)
                if global_conflicts:
                    add_msg("")
                    add_msg("⚔️ Глобальные конфликты:")
                    for conflict in global_conflicts:  # ✅ Убран лимит [:10]
                        add_msg(f"  • {conflict}")

            # ✅ НОВОЕ: Пакетная вставка одним вызовом
            if self.batch_result_callback:
                self.batch_result_callback(result_messages)
            elif self.result_callback:
                # Fallback: по одному сообщению (старое поведение)
                for msg in result_messages:
                    self.result_callback(msg)

        except Exception as e:
            self.log(f"Ошибка обработки результатов: {e}")
            if self.result_callback:
                self.result_callback(f"Ошибка обработки результатов: {e}")
        finally:
            if self.stop_progress:
                self.stop_progress()

    def on_error(self, error: Exception):
        """Обработка ошибки верификации"""
        self.set_status(tr("handler_status_error", "Ошибка"))
        if self.set_progress:
            self.set_progress(0)
        if self.stop_progress:
            self.stop_progress()
        self.log(f"❌ Ошибка верификации: {error}")
        if self.result_callback:
            self.result_callback(f"❌ Ошибка верификации: {error}")


class TranslationHandler:
    """Оптимизированный обработчик событий перевода"""

    def __init__(
        self,
        log_callback: Callable,
        status_callback: Callable,
        progress_callback: Callable | None = None,
        stop_progress_callback: Callable | None = None,
        config: dict | None = None,
    ):
        self.log = log_callback
        self.set_status = status_callback
        self.set_progress = progress_callback
        self.stop_progress = stop_progress_callback
        self._config = config or {}
        self._last_progress_log = 0

    def _get_current_config(self) -> dict:
        """Возвращает текущий конфиг"""
        return self._config

    def set_config(self, config: dict) -> None:
        """Обновляет конфиг"""
        self._config = config

    def on_progress(self, progress: int, total: int, message: str):
        """Обработка прогресса перевода"""
        self.set_status(f"Перевод: {progress}/{total} - {message}")

        if self.set_progress:
            progress_value = int((progress / max(total, 1)) * 100)
            self.set_progress(progress_value)

            if progress_value - self._last_progress_log >= 10:
                self._last_progress_log = progress_value
                self.log(f"[{progress_value}%] {message}")

    def on_complete(self, result: Any):
        """Обработка завершения перевода"""
        self.set_status(tr("handler_status_ready", "Готов"))
        if self.set_progress:
            self.set_progress(100)
        
        try:
            success = getattr(result, "success", False)
            mods_processed = getattr(result, "mods_processed", 0)
            translations_count = getattr(result, "translations_count", 0)
            errors = getattr(result, "errors", [])
            warnings = getattr(result, "warnings", [])
            
            # ✅ НОВОЕ: Toast уведомление
            if hasattr(self, "show_toast"):
                if success:
                    self.show_toast(
                        f"Перевод завершён! {mods_processed} модов, {translations_count} записей",
                        "success",
                    )
                else:
                    self.show_toast(f"Перевод завершён с ошибками: {len(errors)} ошибок", "error")
            
            # ✅ НОВОЕ: Обновляем статусную панель
            if hasattr(self, "update_stats"):
                self.update_stats(
                    mods=mods_processed,
                    translated=translations_count,
                    errors=len(errors),
                    warnings=len(warnings),
                    last_action=tr("handler_stats_translation", "Перевод"),
                )
            
            # ✅ НОВОЕ: Подробная сводка с секциями
            self.log("\n" + "=" * 70)
            self.log("📊 РЕЗУЛЬТАТЫ ПЕРЕВОДА")
            self.log("=" * 70)
            self.log(f"   ✅ Успешно: {'Да' if success else 'Нет'}")
            self.log(f"   📦 Модов обработано: {mods_processed}")
            self.log(f"   📝 Переведено записей: {translations_count}")
            
            if errors:
                self.log(f"   ❌ Ошибок: {len(errors)}")
            if warnings:
                self.log(f"   ⚠️ Предупреждений: {len(warnings)}")
            
            self.log("=" * 70)
            
            # Итоговое сообщение
            self.log("")
            if success:
                self.log("✅ ПЕРЕВОД УСПЕШНО ЗАВЕРШЁН!")
                if mods_processed > 0:
                    self.log(
                        f"   Обработано {mods_processed} модов, {translations_count} записей переведено"
                    )
            else:
                self.log("⚠️ ПЕРЕВОД ЗАВЕРШЁН С ОШИБКАМИ")
                self.log("   Проверьте лог выше для деталей")
            
            self.log("=" * 70 + "\n")
            
            # ✅ НОВОЕ: Пост-обработка Morphy.py для славянских языков
            config = self._get_current_config()
            if config and config.get("use_morphy", False):
                target_lang = config.get("target_language", "")
                if target_lang.lower() in ["russian", "ukrainian", "ru", "uk"]:
                    self.log("🔤 Запуск Morphy.py для пост-обработки...")
                    try:
                        import subprocess
                        # Ищем папку Strings в целевом языке (переведённую)  
                        output_folder = config.get("output_folder", "")
                        if output_folder and os.path.exists(output_folder):
                            # Сканируем папку на наличие Strings/  
                            for root, dirs, files in os.walk(output_folder):
                                if os.path.basename(root) == "Strings":
                                    strings_folder = root
                                    
                                    lang_code = "ru" if "russian" in target_lang.lower() or target_lang.lower() == "ru" else "uk"
                                    
                                    # ✅ ПРАВИЛЬНО: обрабатываем переведённую папку Strings
                                    cmd = f'python utils/Morphy.py --strings "{strings_folder}" --batch --lang {lang_code}'
                                    self.log(f"   Команда: {cmd}")
                                    
                                    result = subprocess.run(
                                        cmd, shell=True, cwd=os.getcwd(),
                                        capture_output=True, text=True, encoding='utf-8', errors='replace'
                                    )
                                    
                                    # Логируем вывод Morphy.py
                                    if result.stdout:
                                        for line in result.stdout.strip().split('\n'):
                                            if line.strip():
                                                self.log(f"   [Morphy] {line.strip()}")
                                    if result.stderr:
                                        for line in result.stderr.strip().split('\n'):
                                            if line.strip():
                                                self.log(f"   [Morphy ERR] {line.strip()}")
                                    
                                    if result.returncode == 0:
                                        self.log("✅ Morphy.py успешно выполнен!")
                                        # Обновляем статус
                                        if hasattr(self, 'update_stats'):
                                            self.update_stats(last_action="Morphy пост-обработка")
                                    else:
                                        self.log(f"⚠️ Morphy.py завершился с кодом: {result.returncode}")
                                    break
                    except Exception as e:
                        self.log(f"⚠️ Ошибка запуска Morphy.py: {e}")
                else:
                    self.log(f"[DEBUG] Morphy skipped: target_lang '{target_lang}' not in Russian/Ukrainian")
            else:
                self.log(f"[DEBUG] Morphy skipped: use_morphy={config.get('use_morphy') if config else 'no config'}")
                
        except Exception as e:
            self.log(f"Ошибка обработки результатов: {e}")
        finally:
            if self.stop_progress:
                self.stop_progress()

    def on_error(self, error: Exception):
        """Обработка ошибки перевода"""
        self.set_status(tr("handler_status_error", "Ошибка"))
        if self.set_progress:
            self.set_progress(0)
        if self.stop_progress:
            self.stop_progress()
        self.log(f"❌ Ошибка перевода: {error}")


class DuplicateMergeHandler:
    """Обработчик событий слияния дубликатов"""

    def __init__(
        self,
        log_callback: Callable,
        status_callback: Callable,
        progress_callback: Callable | None = None,
        stop_progress_callback: Callable | None = None,
    ):
        self.log = log_callback
        self.set_status = status_callback
        self.set_progress = progress_callback
        self.stop_progress = stop_progress_callback

    def on_progress(self, progress: int, total: int, message: str):
        """Обработка прогресса слияния"""
        self.set_status(f"Слияние: {progress}/{total} - {message}")

        if self.set_progress:
            progress_value = int((progress / max(total, 1)) * 100)
            self.set_progress(progress_value)

    def on_complete(self, result: Any):
        """Обработка завершения слияния"""
        self.set_status(tr("handler_status_ready", "Готов"))
        if self.set_progress:
            self.set_progress(100)

        if result:
            self.log("✅ Слияние дубликатов завершено!")
        else:
            self.log("⚠️ Слияние завершено с ошибками")

        if self.stop_progress:
            self.stop_progress()

    def on_error(self, error: Exception):
        """Обработка ошибки слияния"""
        self.set_status(tr("handler_status_error", "Ошибка"))
        if self.set_progress:
            self.set_progress(0)
        if self.stop_progress:
            self.stop_progress()
        self.log(f"❌ Ошибка слияния: {error}")


class IntegrityCheckHandler:
    """Обработчик проверки целостности"""

    def __init__(
        self,
        log_callback: Callable,
        status_callback: Callable,
        progress_callback: Callable | None = None,
        parent_window=None,
        stop_progress_callback: Callable | None = None,
    ):
        self.log = log_callback
        self.set_status = status_callback
        self.set_progress = progress_callback
        self.parent_window = parent_window
        self.stop_progress = stop_progress_callback

    def on_start(self):
        self.set_status(tr("handler_integrity_checking", "Проверка целостности..."))
        if self.set_progress:
            self.set_progress(0)
        self.log("=" * 50)
        self.log(tr("handler_integrity_checking", "Проверка целостности..."))
        self.log("=" * 50)

    def on_progress(self, progress: int, total: int, message: str):
        """Обработка прогресса проверки целостности"""
        self.set_status(f"Целостность: {progress}/{total} - {message}")
        if self.set_progress:
            progress_value = int((progress / max(total, 1)) * 100)
            self.set_progress(progress_value)

    def on_complete(self, result: Any):
        """Обработка завершения проверки целостности"""
        self.set_status(tr("handler_status_ready", "Готов"))
        if self.set_progress:
            self.set_progress(100)

        # Получаем результаты из DTO
        success = getattr(result, "success", True)
        files_checked = getattr(result, "files_checked", 0)
        files_valid = getattr(result, "files_valid", 0)
        files_invalid = getattr(result, "files_invalid", 0)
        warnings = getattr(result, "warnings", 0)
        errors = getattr(result, "errors", [])
        details = getattr(result, "details", [])

        self.log(f"📊 Проверено файлов: {files_checked}")
        self.log(f"✅ Корректных: {files_valid}")
        self.log(f"❌ С ошибками: {files_invalid}")
        self.log(f"⚠️ Предупреждений: {warnings}")

        if errors:
            self.log("\n❌ Ошибки:")
            for error in errors:
                self.log(f"  - {error}")

        if details:
            self.log("\n📋 Подробности:")
            for detail in details:
                self.log(f"  {detail}")

        self.log("=" * 50)

        if success:
            self.log("✅ Проверка целостности пройдена успешно!")
        else:
            self.log("⚠️ Обнаружены проблемы целостности!")

        # ✅ НОВОЕ: Показываем отдельное окно с результатами
        if self.parent_window:
            try:
                from gui.dialogs.integrity_results_dialog import IntegrityResultsDialog

                IntegrityResultsDialog(
                    self.parent_window,
                    result,
                    log_messages=[
                        f"📊 Проверено файлов: {files_checked}",
                        f"✅ Корректных: {files_valid}",
                        f"❌ С ошибками: {files_invalid}",
                        f"⚠️ Предупреждений: {warnings}",
                        *errors,
                        *details,
                    ],
                )
            except Exception as e:
                self.log(f"⚠️ Не удалось открыть окно результатов: {e}")

        if self.stop_progress:
            self.stop_progress()

    def on_error(self, error: Exception):
        self.set_status(tr("handler_status_error", "Ошибка"))
        if self.set_progress:
            self.set_progress(0)
        if self.stop_progress:
            self.stop_progress()
        self.log(f"❌ Ошибка проверки целостности: {error}")
        import traceback

        self.log(traceback.format_exc())
