@echo off
chcp 65001 >nul
echo Запуск RimWorld Translator Grabber GUI...
cd /d "%~dp0"
if not exist "env\python\python.exe" (
    echo ОШИБКА! Виртуальное окружение не найдено.
    pause >nul
    exit /b 1
)
env\python\python.exe run_gui.py
if errorlevel 1 (
    echo.
    echo ОШИБКА! Нажмите любую клавишу...
    pause >nul
)