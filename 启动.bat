@echo off
chcp 65001 > nul
echo 正在启动 ClickScheduler...
cd /d "%~dp0"
python main.py
pause
