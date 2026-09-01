@echo off
TITLE Pulp Line 2 - OneDrive to PI Hourly Sync Service
cd /d "%~dp0"

echo ======================================================================
echo    Pulp Line 2 - OneDrive to PI Live Hourly Sync Service
echo ======================================================================
echo  This window will stay open and run automatically every 1 hour.
echo  To stop the sync service, simply close this window or press Ctrl+C.
echo ======================================================================
echo.

python main_sync.py --loop

pause
