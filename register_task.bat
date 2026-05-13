@echo off
setlocal

set "TASK_NAME=CarTrack Vehicle Notification Job"
set "START_TIME=08:00"
set "PROJECT_DIR=%~dp0"
set "PY_EXE=%~dp0venv\Scripts\python.exe"

if not exist "%PY_EXE%" (
    set "PY_EXE=python"
)

set "SCRIPT_PATH=%PROJECT_DIR%vehicle_notification_job.py"
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] vehicle_notification_job.py not found.
    exit /b 1
)

echo [INFO] Registering/updating task: %TASK_NAME%
schtasks /Create /TN "%TASK_NAME%" /SC DAILY /ST %START_TIME% /TR "\"%PY_EXE%\" \"%SCRIPT_PATH%\"" /F
if errorlevel 1 (
    echo [ERROR] Failed to register task.
    exit /b 1
)

echo [OK] Task registered.
schtasks /Query /TN "%TASK_NAME%" /V /FO LIST

endlocal
