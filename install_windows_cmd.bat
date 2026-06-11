@echo off
setlocal
cd /d "%~dp0"

set PY_CMD=
py -3.12 --version >nul 2>&1
if %errorlevel%==0 set PY_CMD=py -3.12
if "%PY_CMD%"=="" (
  py -3.11 --version >nul 2>&1
  if %errorlevel%==0 set PY_CMD=py -3.11
)
if "%PY_CMD%"=="" set PY_CMD=py

echo Usando Python:
%PY_CMD% --version

echo.
echo Criando ambiente virtual...
%PY_CMD% -m venv .venv
if errorlevel 1 goto error

echo.
echo Atualizando pip...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto error

echo.
echo Instalando dependencias...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo Instalacao concluida.
echo Para abrir o app, execute: run_windows_cmd.bat
pause
exit /b 0
:error
echo.
echo Ocorreu um erro na instalacao.
echo Dica: prefira Python 3.12 ou 3.11 para este projeto.
pause
exit /b 1
