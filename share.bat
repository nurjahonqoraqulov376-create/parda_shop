@echo off
REM Saytni ommaviy (probniy) havola bilan ishga tushiradi.
REM Shu faylni ikki marta bosing - havola oynada chiqadi.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0share.ps1"
pause
