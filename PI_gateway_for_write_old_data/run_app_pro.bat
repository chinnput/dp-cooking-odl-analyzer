@echo off
echo Starting PI Connect High-Speed Gateway...
uvicorn app_pro.main:app --host 127.0.0.1 --port 5707 --workers 1
pause