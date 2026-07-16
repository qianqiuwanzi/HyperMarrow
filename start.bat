@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ╔══════════════════════════════════════════════╗
echo ║     智商藏不住 — 启动中...           ║
echo ╚══════════════════════════════════════════════╝
echo.
python start.py %*
pause
