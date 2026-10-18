#!/usr/bin/env python
"""
RimWorld Translator Grabber - setup.py
Установка и настройка проекта
"""

import os

from setuptools import find_packages, setup


# Чтение README
def read_readme():
    """Чтение содержимого README.md"""
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, encoding="utf-8") as f:
            return f.read()
    return ""


# Чтение версии
def get_version():
    """Получение версии из __init__.py"""
    init_path = os.path.join(os.path.dirname(__file__), "__init__.py")
    if os.path.exists(init_path):
        with open(init_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip("\"'")
    return "2.1.0"


setup(
    name="rimworld-translator-grabber",
    version=get_version(),
    author="RimWorld Translator Team",
    author_email="rimworld-translator@users.noreply.github.com",
    description="Инструмент для перевода и верификации модов RimWorld",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/rimworld-translator/rimworld-translator-grabber",
    # Классификаторы
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Text Processing :: Linguistic",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Operating System :: OS Independent",
    ],
    # Ключевые слова
    keywords="rimworld translation mod localization xml",
    # Пакеты
    packages=find_packages(exclude=["tests", "tests.*"]),
    # Минимальная версия Python
    python_requires=">=3.10",
    # Зависимости (синхронизировано с requirements.txt, актуально на 2026-10)
    install_requires=[
        "ttkbootstrap>=2.2.3",  # GUI-фреймворк
        "ttkbootstrap-icons>=4.0.0",  # Иконки для GUI
        "tkinterdnd2>=0.4.3",  # Drag & Drop для редактора
        "pillow>=12.1.1",  # Графика для ttkbootstrap/иконок
        "deep-translator>=1.11.4",  # Движки перевода
        "platformdirs>=4.13.0",  # Системные пути
        "pyspellchecker>=0.9.1",  # Проверка орфографии
        "rapidfuzz>=3.14.6",  # Нечёткое сравнение
        "loguru>=0.7.3",  # Логирование
        "requests>=2.34.2",  # HTTP
        "ahocorasick-rs>=1.0.3",  # Быстрый поиск паттернов
        "pydantic>=2.0",  # pydantic_core для verification/brain/core
        "pycrfsuite>=0.9.7",  # CRF-модель
        "lxml>=6.1.1",  # XML
        "pyperclip>=1.11.0",  # Буфер обмена
    ],
    # Дополнительные зависимости
    extras_require={
        "dev": [
            "pytest>=9.1.1",
            "pytest-cov>=7.1.0",
            "flake8>=6.0",
            "black>=23.0",
        ],
        "gui": [
            "ttkbootstrap>=2.2.3",
            "ttkbootstrap-icons>=4.0.0",
            "tkinterdnd2>=0.4.3",
        ],
        "morph": [
            "pymorphy3>=2.0.6",
            "pymorphy3-dicts-uk>=2.4.1",
            "pymorphy3-dicts-ru>=2.4.4",
        ],
        "nlp": [
            "spacy>=3.0.0",
            "ufal.udpipe>=1.4.0.1",
        ],
    },
    # Точки входа
    entry_points={
        "console_scripts": [
            "rimworld-translate=main:main",
            "rimworld-gui=gui:main",
        ],
    },
    # Данные пакетов - включаем все необходимые файлы
    include_package_data=True,
    package_data={
        "": [
            "*.json",  # translations.json, gui_config.json, filters_config.json
            "*.md",  # README.md, CHANGELOG.md, DOCUMENTATION_RU.md
            "*.txt",  # requirements.txt, debug.log
            "*.db",  # translations.db (если есть)
        ],
        # Явное включение подпакетов GUI
        "gui": [
            "*.json",  # gui_config.json
        ],
        "gui.tabs": [
            "*.json",  # конфиги вкладок
        ],
        "gui.dialogs": [
            "*.json",  # конфиги диалогов
        ],
        "gui.core": [
            "*.json",
        ],
        "gui.components": [
            "*.json",
        ],
        "gui.styling": [
            "*.json",
        ],
        "gui.handlers": [
            "*.json",
        ],
        "gui.actions": [
            "*.json",
        ],
        "config": [
            "*.json",  # language_constants.json, mods_config.json
        ],
        "language": [
            "*.json",  # языковые правила
        ],
        "helpers": [
            "*.json",
        ],
    },
    # Файлы для исключения
    exclude_package_data={
        "": ["__pycache__", "*.pyc", "*.pyo"],
    },
    # Лицензия
    license="MIT",
    license_files=["LICENSE"],
    # URL документации
    project_urls={
        "Documentation": "https://github.com/rimworld-translator/rimworld-translator-grabber/docs",
        "Source": "https://github.com/rimworld-translator/rimworld-translator-grabber",
        "Tracker": "https://github.com/rimworld-translator/rimworld-translator-grabber/issues",
    },
)
