@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo  Building "PD Bot Game - Cookie run" (.exe)
echo ==============================================

set ICON_ARG=
if exist assets\icon.ico set ICON_ARG=--icon assets\icon.ico

python -m PyInstaller --noconfirm --clean --windowed --name "PD_Bot_Game_CookieRun" %ICON_ARG% gui_main.py

if errorlevel 1 (
  echo.
  echo Build failed - see the errors above.
  pause
  exit /b 1
)

set DIST_DIR=dist\PD_Bot_Game_CookieRun

echo.
echo Copying config, templates, and output folders next to the .exe...
xcopy /E /I /Y config "%DIST_DIR%\config" >nul
xcopy /E /I /Y templates "%DIST_DIR%\templates" >nul
if not exist "%DIST_DIR%\data_output" mkdir "%DIST_DIR%\data_output"
if not exist "%DIST_DIR%\logs\errors" mkdir "%DIST_DIR%\logs\errors"

echo.
echo Done! Your app is ready at: %DIST_DIR%\PD_Bot_Game_CookieRun.exe
echo You can copy the whole "%DIST_DIR%" folder anywhere to distribute it.
pause
