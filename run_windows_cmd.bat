@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Ambiente virtual nao encontrado. Execute install_windows_cmd.bat primeiro.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m streamlit run app.py
