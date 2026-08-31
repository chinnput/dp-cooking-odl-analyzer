@echo off
REM Windows Task Scheduler Runner for OneDrive to PI Sync Pipeline
REM Displays execution output in visible CMD window for monitoring
cd /d "%~dp0"

echo ======================================================================
echo Starting OneDrive / SharePoint to PI Sync Pipeline...
echo ======================================================================

python main_sync.py

echo.
echo ======================================================================
echo Sync finished at %DATE% %TIME%
echo ======================================================================
timeout /t 10
