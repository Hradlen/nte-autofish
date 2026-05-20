@echo off
REM Создаёт venv и ставит зависимости. Запусти один раз.

cd /d "%~dp0"

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Done. Run start.bat to launch the bot.
pause
