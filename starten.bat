@echo off
rem Figures in Context per Doppelklick starten. Oeffnet die Web-App im Browser.
chcp 65001 >nul
cd /d "%~dp0"

py -3 --version >nul 2>&1
if %errorlevel%==0 (
    py -3 -m figures_in_context app
    goto ende
)
python --version >nul 2>&1
if %errorlevel%==0 (
    python -m figures_in_context app
    goto ende
)

echo.
echo Python wurde nicht gefunden.
echo Installiere Python 3 von https://www.python.org/downloads/
echo und setze beim Installieren den Haken bei "Add python.exe to PATH".
echo Zusaetzliche Pakete braucht Figures in Context nicht.

:ende
echo.
pause
