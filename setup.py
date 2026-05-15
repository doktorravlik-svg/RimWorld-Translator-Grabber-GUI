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
    # Зависимости (актуальные на 2026-04)
    install_requires=[
        "ttkbootstrap>=1.20.2",  # Последняя от 2026-03-08
        "ttkbootstrap-icons>=4.0.0",  # Иконки для GUI
        "deep-translator>=1.11.4",  # Стабильная
        "platformdirs>=4.9.4",  # Актуальная
        "pillow>=12.1.1",  # Актуальная
        "pyspellchecker>=0.9.0",  # Актуальная от 2026-03-07
        "tkinterdnd2>=0.4.3",  # Drag & Drop для редактора
    ],
    # Дополнительные зависимости
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "flake8>=6.0",
            "black>=23.0",
        ],
        "gui": [
            "ttkbootstrap>=1.20.2",
            "ttkbootstrap-icons>=4.0.0",
            "tkinterdnd2>=0.4.3",
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
