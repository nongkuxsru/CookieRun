@echo off
mode con: cols=40 lines=10
title Clear Error Logs

set "ROOT_PATH=%~dp0"
set "LOG_PATH=%ROOT_PATH%logs\errors"

echo Clearing error logs...
echo.

if exist "%LOG_PATH%" (
    del /q "%LOG_PATH%\*.*" >nul 2>&1
    for /d %%i in ("%LOG_PATH%\*") do rd /s /q "%%i" >nul 2>&1

    echo Error logs cleared successfully.
) else (
    echo Error folder not found.
)

echo.
echo Closing in 3 seconds...
timeout /t 3 /nobreak >nul
exit