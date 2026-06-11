@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Ambiente virtual nao encontrado. Execute install_windows_cmd.bat primeiro.
  pause
  exit /b 1
)
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import streamlit, supabase, folium, streamlit_folium, httpx, qrcode, PIL; print('dependencias ok')"
pause
