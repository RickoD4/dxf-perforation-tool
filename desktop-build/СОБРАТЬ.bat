@echo off
chcp 65001 >nul
title Сборка .exe
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python не найден в системе.
    echo Скачайте и установите его с сайта https://python.org
    echo При установке ОБЯЗАТЕЛЬНО поставьте галочку "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

python build.py %*
pause
