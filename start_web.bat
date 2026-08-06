@echo off
setlocal EnableExtensions

rem Fixed ports for the dchan development web application.
set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8000"
set "FRONTEND_HOST=localhost"
set "FRONTEND_PORT=5173"
set "HEALTH_URL=http://%BACKEND_HOST%:%BACKEND_PORT%/health"
set "VITE_API_URL=http://%BACKEND_HOST%:%BACKEND_PORT%"
set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

if /i "%~1"=="backend" goto backend
if /i "%~1"=="frontend" goto frontend

echo ========================================
echo dchan Web launcher
echo ========================================
echo.

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found on PATH.
    echo Install Node.js and make sure npm is available.
    echo.
    pause
    exit /b 1
)

call :resolve_python
if errorlevel 1 (
    echo [ERROR] Python was not found.
    echo Create .venv, install uv, or make py/python available on PATH.
    echo.
    pause
    exit /b 1
)

echo Python: %PYTHON_CMD%
%PYTHON_CMD% -c "import fastapi, numpy, pandas, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Required Python packages are not available.
    echo Run: %INSTALL_CMD%
    echo.
    pause
    exit /b 1
)

echo Starting dchan backend at http://%BACKEND_HOST%:%BACKEND_PORT% ...
start "dchan backend" /D "%~dp0" cmd.exe /k ""%~f0" backend"

echo Waiting for FastAPI to become ready...
call :wait_for_backend
if errorlevel 1 (
    echo.
    echo [ERROR] dchan FastAPI did not become ready within 60 seconds.
    echo Check the dchan backend window for the traceback or port error.
    echo The React frontend was not started.
    echo.
    pause
    exit /b 1
)

echo FastAPI is ready.
echo Starting dchan frontend at http://%FRONTEND_HOST%:%FRONTEND_PORT% ...
start "dchan frontend" /D "%~dp0frontend" cmd.exe /k ""%~f0" frontend"

echo.
echo Startup windows were opened.
echo Frontend: http://%FRONTEND_HOST%:%FRONTEND_PORT%
echo Backend : http://%BACKEND_HOST%:%BACKEND_PORT%
echo Health  : %HEALTH_URL%
echo.
echo Press any key to close only this launcher window.
pause >nul
exit /b 0

:resolve_python
set "PYTHON_CMD="
set "INSTALL_CMD="

if exist "%VENV_PYTHON%" (
    set PYTHON_CMD="%VENV_PYTHON%"
    set INSTALL_CMD="%VENV_PYTHON%" -m pip install -e .
    exit /b 0
)

where uv >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=uv run python"
    set "INSTALL_CMD=uv sync"
    exit /b 0
)

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    set "INSTALL_CMD=py -3 -m pip install -e ."
    exit /b 0
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    set "INSTALL_CMD=python -m pip install -e ."
    exit /b 0
)

exit /b 1

:wait_for_backend
for /L %%I in (1,1,60) do (
    powershell.exe -NoProfile -Command "try { $response = Invoke-WebRequest -UseBasicParsing -Uri '%HEALTH_URL%' -TimeoutSec 2; if ($response.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
    if not errorlevel 1 exit /b 0
    timeout /t 1 /nobreak >nul
)
exit /b 1

:backend
cd /d "%~dp0"
echo ========================================
echo dchan FastAPI backend
echo ========================================
echo.

call :resolve_python
if errorlevel 1 (
    echo [ERROR] Python was not found.
    pause
    exit /b 1
)

echo Using Python command:
echo %PYTHON_CMD%
echo.
%PYTHON_CMD% -m uvicorn application.main:app --reload --host %BACKEND_HOST% --port %BACKEND_PORT%

set "SERVER_EXIT=%ERRORLEVEL%"
echo.
echo [ERROR] dchan backend stopped. Exit code: %SERVER_EXIT%
echo Check the error message above. This window will remain open.
pause
exit /b %SERVER_EXIT%

:frontend
cd /d "%~dp0frontend"
echo ========================================
echo dchan React frontend
echo ========================================
echo.

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found on PATH.
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo node_modules was not found. Running npm install...
    call npm install
    if errorlevel 1 (
        echo.
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

call npm run dev -- --host %FRONTEND_HOST% --port %FRONTEND_PORT% --strictPort
set "FRONTEND_EXIT=%ERRORLEVEL%"
echo.
echo [ERROR] dchan frontend stopped. Exit code: %FRONTEND_EXIT%
echo Check the error message above. This window will remain open.
pause
exit /b %FRONTEND_EXIT%
