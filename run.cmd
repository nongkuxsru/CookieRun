@echo off
title Run Python GUI

:: ตั้งขนาดหน้าต่าง CMD ให้เล็กที่สุดที่รองรับ
mode con: cols=20 lines=1

cd /d "%~dp0"

python gui_main.py

pause