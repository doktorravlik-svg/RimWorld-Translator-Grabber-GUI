# verification/conflict_detector.py
"""
Модуль обнаружения конфликтов переводов RimWorld.
"""

import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum


class ConflictType(Enum):
    DUPLICATE_KEY = "duplicate_key"
    MISSING_PARENT = "missing_parent"
    VERSION_MISMATCH = "version_mismatch"
    TRANSLATION_MISSING = "translation_missing"
    TRANSLATION_CONFLICT = "translation_conflict"


class ConflictSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ResolutionStrategy(Enum):
    USE_FIRST = "use_first"
    USE_LAST = "use_last"
    USE_LONGEST = "use_longest"
    USE_NEWEST = "use_newest"
    MANUAL = "manual"


@dataclass
class ConflictInfo:
    conflict_type: ConflictType
    key_or_file: str
    mod_a: str
    mod_b: str
    severity: ConflictSeverity
    description: str
    resolution: str | None = None
    affected_keys: list[str] = field(default_factory=list)
    file_paths: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"[{self.conflict_type.value}] {self.description}"


@dataclass
class TranslationEntry:
    key: str
    value: str
    mod_id: str
    mod_name: str
    file_path: str
    language: str
    def_name: str | None = None


class ConflictDetector:
    """Класс для обнаружения конфликтов между переводами модов RimWorld."""

    def __init__(self, mods_path: str, logger: logging.Logger | None = None):
        self.mods_path = mods_path
        self.logger = logger
        self._mods_cache: dict[str, dict] = {}
        self._translations: dict[str, list[TranslationEntry]] = defaultdict(list)
        self._key_to_mods: dict[str, set[str]] = defaultdict(set)

    def load_mods(self) -> dict[str, dict]:
        """Загружает информацию обо всех модах"""
        from scanner.mod_scanner import find_about_xml, parse_about_xml

        if not os.path.exists(self.mods_path):
            if self.logger:
                self.logger.error(f"Путь к модам не существует: {self.mods_path}")
            return {}

        for item in os.listdir(self.mods_path):
            mod_path = os.path.join(self.mods_path, item)
            if not os.path.isdir(mod_path):
                continue

            about_path = find_about_xml(mod_path)
            if not about_path:
                continue

            about_data = parse_about_xml(about_path)
            mod_id = about_data.get("mod_id")

            if not mod_id:
                continue

            languages = about_data.get("supported_languages", [])
            self._mods_cache[mod_id] = {
                "mod_id": mod_id,
                "mod_name": about_data.get("name", "Unknown"),
                "mod_path": mod_path,
                "version": about_data.get("version"),
                "is_translation": self._is_translation_mod(about_data),
                "parent_mod_id": about_data.get("target_mod_id"),
                "languages": languages,
            }

        if self.logger:
            self.logger.info(f"Загружено {len(self._mods_cache)} модов")

        return self._mods_cache

    def load_translations(self, language: str = None) -> dict[str, list[TranslationEntry]]:
        """Загружает все переводы из модов."""
        from .xml_parser import XMLParser

        self._translations.clear()
        self._key_to_mods.clear()
        parser = XMLParser(self.logger)

        for mod_id, mod_info in self._mods_cache.items():
            mod_path = mod_info["mod_path"]
            langs_path = os.path.join(mod_path, "Languages")

            if not os.path.exists(langs_path):
                continue

            languages_to_scan = [language] if language else self._get_mod_languages(mod_path)

            for lang in languages_to_scan:
                lang_dir = os.path.join(langs_path, lang)
                if not os.path.exists(lang_dir):
                    continue

                # Keyed файлы
                keyed_dir = os.path.join(lang_dir, "Keyed")
                if os.path.exists(keyed_dir):
                    for root, _, files in os.walk(keyed_dir):
                        for fname in files:
                            if fname.endswith(".xml"):
                                fpath = os.path.join(root, fname)
                                self._parse_keyed_file(
                                    fpath, mod_id, mod_info["mod_name"], lang, parser
                                )

                # DefInjected файлы
                def_injected_dir = os.path.join(lang_dir, "DefInjected")
                if os.path.exists(def_injected_dir):
                    for root, _, files in os.walk(def_injected_dir):
                        for fname in files:
                            if fname.endswith(".xml"):
                                fpath = os.path.join(root, fname)
                                self._parse_def_injected_file(
                                    fpath, mod_id, mod_info["mod_name"], lang, parser
                                )

        if self.logger:
            total_entries = sum(len(entries) for entries in self._translations.values())
            self.logger.info(f"Загружено {total_entries} записей переводов")

        return self._translations

    def _parse_keyed_file(
        self, file_path: str, mod_id: str, mod_name: str, language: str, parser
    ) -> None:
        result = parser.parse(file_path)
        if not result.success or not result.entries:
            return

        for key, value in result.entries.items():
            entry = TranslationEntry(
                key=key,
                value=value,
                mod_id=mod_id,
                mod_name=mod_name,
                file_path=file_path,
                language=language,
            )
            self._translations[key].append(entry)
            self._key_to_mods[key].add(mod_id)

    def _parse_def_injected_file(
        self, file_path: str, mod_id: str, mod_name: str, language: str, parser
    ) -> None:
        result = parser.parse(file_path)
        if not result.success or not result.entries:
            return

        def_name = self._extract_def_name(file_path)
        for key, value in result.entries.items():
            entry = TranslationEntry(
                key=key,
                value=value,
                mod_id=mod_id,
                mod_name=mod_name,
                file_path=file_path,
                language=language,
                def_name=def_name,
            )
            self._translations[key].append(entry)
            self._key_to_mods[key].add(mod_id)

    def _extract_def_name(self, file_path: str) -> str:
        parts = file_path.split(os.sep)
        for i, part in enumerate(parts):
            if part == "DefInjected" and i + 1 < len(parts):
                return parts[i + 1]
        return "Unknown"

    def _get_mod_languages(self, mod_path: str) -> list[str]:
        langs_path = os.path.join(mod_path, "Languages")
        if not os.path.exists(langs_path):
            return []
        return [d for d in os.listdir(langs_path) if os.path.isdir(os.path.join(langs_path, d))]

    def find_duplicate_keys(self, case_sensitive: bool = True) -> list[ConflictInfo]:
        """Находит дубликаты ключей переводов."""
        conflicts = []
        for key, entries in self._translations.items():
            if len(entries) <= 1:
                continue

            value_groups = defaultdict(list)
            for entry in entries:
                value = entry.value if case_sensitive else entry.value.lower()
                value_groups[value].append(entry)

            if len(value_groups) > 1:
                mods = list(set(e.mod_id for e in entries))
                mod_names = list(set(e.mod_name for e in entries))

                conflict = ConflictInfo(
                    conflict_type=ConflictType.DUPLICATE_KEY,
                    key_or_file=key,
                    mod_a=mods[0] if mods else "",
                    mod_b=mods[1] if len(mods) > 1 else "",
                    severity=ConflictSeverity.WARNING,
                    description=f"Ключ '{key}' имеет разные значения в модах: {', '.join(mod_names)}",
                    affected_keys=[key],
                    file_paths=[e.file_path for e in entries],
                )
                conflicts.append(conflict)

        return conflicts

    def find_translation_conflicts(self, language: str = None) -> list[ConflictInfo]:
        """Находит конфликты переводов между модами."""
        conflicts = []
        for mod_id, mod_info in self._mods_cache.items():
            if mod_info["is_translation"] and mod_info["parent_mod_id"]:
                parent_id = mod_info["parent_mod_id"]
                if parent_id not in self._mods_cache:
                    conflict = ConflictInfo(
                        conflict_type=ConflictType.MISSING_PARENT,
                        key_or_file=mod_id,
                        mod_a=mod_id,
                        mod_b=parent_id,
                        severity=ConflictSeverity.ERROR,
                        description=f"Переводной мод '{mod_info['mod_name']}' ссылается на несуществующий родительский мод '{parent_id}'",
                        resolution="Установите родительский мод",
                    )
                    conflicts.append(conflict)
        return conflicts

    def detect_all_conflicts(self) -> list[ConflictInfo]:
        """Обнаруживает все типы конфликтов."""
        all_conflicts = []
        all_conflicts.extend(self.find_duplicate_keys())
        all_conflicts.extend(self.find_translation_conflicts())

        if self.logger:
            self.logger.info(f"Обнаружено конфликтов: {len(all_conflicts)}")
        return all_conflicts

    def get_stats(self) -> dict[str, int]:
        return {
            "total_keys": len(self._translations),
            "total_entries": sum(len(entries) for entries in self._translations.values()),
        }

    def _is_translation_mod(self, about_data: dict) -> bool:
        """Определение является ли мод переводом (использует единый модуль классификации)"""
        from utils.mod_classifier import is_translation_mod

        return is_translation_mod(about_data)


def detect_translation_conflicts(
    mods_path: str, logger: logging.Logger | None = None
) -> list[ConflictInfo]:
    detector = ConflictDetector(mods_path, logger)
    detector.load_mods()
    detector.load_translations()
    return detector.detect_all_conflicts()


def find_duplicate_keys(
    mods_path: str, case_sensitive: bool = True, logger: logging.Logger | None = None
) -> list[ConflictInfo]:
    detector = ConflictDetector(mods_path, logger)
    detector.load_mods()
    detector.load_translations()
    return detector.find_duplicate_keys(case_sensitive)
