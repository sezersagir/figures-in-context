@echo off
rem Start Figures in Context by double-click. Opens the web app in the browser.
chcp 65001 >nul
cd /d "%~dp0"

py -3 --version >nul 2>&1
if %errorlevel%==0 (
    py -3 -m figures_in_context app
    goto end
)
python --version >nul 2>&1
if %errorlevel%==0 (
    python -m figures_in_context app
    goto end
)

echo.
echo Python was not found.
echo Install Python 3 from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during the installation.
echo Figures in Context needs no extra packages.

:end
echo.
pause
