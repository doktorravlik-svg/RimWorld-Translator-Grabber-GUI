#!/usr/bin/env python
"""
Точка запуска GUI.
Обходит конфликт gui.py <-> gui/ через importlib.
"""

import os
import sys
import importlib.util

# Переходим в директорию скрипта
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Загружаем gui.py как отдельный модуль
spec = importlib.util.spec_from_file_location("gui_main", "gui.py")
gui_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui_main)

# Запускаем
gui_main.main()
