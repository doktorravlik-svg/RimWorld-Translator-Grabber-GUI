@echo off
chcp 65001 >nul
echo Запуск RimWorld Translator Grabber GUI...
cd /d "%~dp0"
F:\CTk_Project_2026\Python314\python.exe run_gui.py
if errorlevel 1 (
    echo.
    echo ОШИБКА! Нажмите любую клавишу...
    pause >nul
)