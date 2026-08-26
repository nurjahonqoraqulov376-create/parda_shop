@echo off
cd /d "%~dp0"
.venv\Scripts\activate.bat
python manage.py runserver
pause
