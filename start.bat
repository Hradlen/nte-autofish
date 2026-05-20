@echo off
REM Авто-запрос прав админа.
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -WindowStyle Hidden -Command "Start-Process '%~f0' -Verb RunAs -WindowStyle Hidden"
    exit /b
)

cd /d "%~dp0"
REM pythonw.exe — запуск без видимой консоли. Логи и ошибки пишутся в app.log.
start "" "venv\Scripts\pythonw.exe" main.py
exit /b
