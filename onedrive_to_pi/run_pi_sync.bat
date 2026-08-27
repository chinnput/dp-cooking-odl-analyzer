@echo off
REM Windows Task Scheduler Runner for OneDrive to PI Sync Pipeline
cd /d "%~dp0"
python main_sync.py >> sync_log.log 2>&1
