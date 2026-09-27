@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
title PladixAgentIA_CLI - PladixOficial

echo ========================================================================
echo    PladixAgentIA_CLI - PladixAgentIA_CLI
echo ========================================================================
echo    Desenvolvido por: PladixOficial
echo    Telegram: https://t.me/pladixoficial
echo ========================================================================
echo.

:: 1. Verificando Python
echo [*] Verificando instalacao do Python...

set "PY_CMD="

python --version >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :PYTHON_FOUND
)

py --version >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=py"
    goto :PYTHON_FOUND
)

:: Se nao achou, tenta winget
echo [!] Python nao foi encontrado no PATH do sistema.
echo [*] Tentando instalar o Python automaticamente via Winget...

winget install -e --id Python.Python.3.12 --scope currentuser --accept-package-agreements --accept-source-agreements
if %errorlevel% equ 0 (
    echo [OK] Python instalado com sucesso!
    echo [*] Por favor, feche e abra este arquivo novamente para carregar o PATH.
    pause
    exit /b 0
)

echo [ERRO] Nao foi possivel instalar o Python automaticamente.
echo [*] Baixe e instale o Python em: https://www.python.org/downloads/
echo     (Importante: marque a caixa "Add Python to PATH")
pause
exit /b 1

:PYTHON_FOUND
for /f "tokens=*" %%v in ('%PY_CMD% --version 2^>^&1') do set "PY_VER=%%v"
echo [OK] %PY_VER% detectado!
echo.

:: 2. Verificando / Instalando Dependencias
echo [*] Verificando dependencias do projeto (requirements.txt)...
%PY_CMD% -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo [AVISO] Tentando instalar pacotes individualmente...
    %PY_CMD% -m pip install numba numpy httpx rich prompt_toolkit
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao instalar dependencias necessarias.
        pause
        exit /b 1
    )
)
echo [OK] Dependencias instaladas e verificadas!
echo.

:: 3. Executando o PladixAgentIA_CLI
echo ========================================================================
echo [*] Iniciando PladixAgentIA_CLI...
echo ========================================================================
echo.

cd /d "%~dp0"
%PY_CMD% "%~dp0main.py"

if %errorlevel% neq 0 (
    echo.
    echo [!] O programa foi encerrado com codigo de erro %errorlevel%.
    pause
)

endlocal

