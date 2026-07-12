@echo off
title Restart ADB
color 0A

echo ==========================
echo    Restarting ADB...
echo ==========================

adb kill-server >nul 2>&1
adb start-server

echo.
echo ==========================
echo Connected Devices
echo ==========================

adb devices

echo.
echo Done!
pause