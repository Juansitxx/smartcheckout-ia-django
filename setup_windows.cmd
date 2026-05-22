@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
".venv\Scripts\python.exe" manage.py makemigrations
".venv\Scripts\python.exe" manage.py migrate
".venv\Scripts\python.exe" manage.py seed_products
echo.
echo Setup finalizado. Ejecuta runserver_windows.cmd
