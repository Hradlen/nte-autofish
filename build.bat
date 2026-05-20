@echo off
REM Сборка NTE Fish в .exe через PyInstaller.
REM Результат: dist\NTE_Fish\NTE_Fish.exe

cd /d "%~dp0"

REM Очистка старых билдов
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

REM Сборка
call venv\Scripts\activate.bat
pyinstaller nte_fish.spec --noconfirm
if errorlevel 1 goto :failed

REM Копируем templates рядом с .exe (для user-writable доступа).
if exist "templates" xcopy /e /i /y "templates" "dist\NTE_Fish\templates" >nul

REM Удаляем intermediate build/ — там лежит лишний .exe который не работает.
if exist "build" rmdir /s /q "build"

echo.
echo ============================================================
echo  Готово!
echo  Запускай: dist\NTE_Fish\NTE_Fish.exe
echo ============================================================
echo.

REM Открываем папку с готовым билдом
start "" "dist\NTE_Fish"
exit /b 0

:failed
echo.
echo ============================================================
echo  СБОРКА УПАЛА — смотри ошибки выше
echo ============================================================
pause
exit /b 1
