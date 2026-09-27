@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
title PladixAgentIA - GUI Engine

echo ========================================================================
echo    PladixAgentIA - Interface Grafica (GUI) v2.0
echo ========================================================================
echo    Desenvolvido por: PladixOficial
echo ========================================================================
echo.

set "PY_CMD="
python --version >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :START
)

py --version >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=py"
    goto :START
)

echo [ERRO] Python nao foi encontrado!
pause
exit /b 1

:START
%PY_CMD% -c "import pywebview, fastapi, uvicorn, websockets" >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Instalando dependencias da Interface Grafica...
    %PY_CMD% -m pip install pywebview fastapi uvicorn websockets jinja2
    echo [OK] Dependencias instaladas.
)

echo ========================================================================
echo [*] Iniciando PladixAgentIA GUI (Porta Dinamica Segura)...
echo ========================================================================
cd /d "%~dp0"
%PY_CMD% "deepseek_gui\gui_server.py"

if %errorlevel% neq 0 (
    echo.
    echo [!] Servidor encerrado com status %errorlevel%.
    pause
)
endlocal
