@echo off
chcp 65001
echo ===================================================
echo 🦅 Antigravity Sentinel Mode (Full Auto)
echo ===================================================
echo.
echo Starting AI News Bot in Sentinel Mode...
echo Interval: Every 4 Hours
echo Actions: News Collection -> PDF Generation -> X Posting
echo.
echo [NOTE] Keep this window OPEN to keep the bot running.
echo.

cd /d "C:\Users\tadah\Desktop\Antigravity\ai-news-bot"

".venv\Scripts\python.exe" sentinel_loop.py

pause
