@echo off
REM Celery Management Script for Sistema de Polinización y Germinación (Windows)
REM This script provides utilities for managing Celery workers, beat, and monitoring

setlocal enabledelayedexpansion

REM Configuration
set PROJECT_NAME=sistema_polinizacion
set CELERY_APP=sistema_polinizacion
set LOG_DIR=logs
set PID_DIR=pids

REM Ensure directories exist
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%PID_DIR%" mkdir "%PID_DIR%"

REM Function to print colored output (simplified for Windows)
:print_status
echo [INFO] %~1
goto :eof

:print_warning
echo [WARNING] %~1
goto :eof

:print_error
echo [ERROR] %~1
goto :eof

:print_header
echo === %~1 ===
goto :eof

REM Main script logic
if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="status" goto status
if "%1"=="logs" goto logs
if "%1"=="purge" goto purge
if "%1"=="test" goto test
goto help

:start
if "%2"=="" set service=all
if not "%2"=="" set service=%2

if "%service%"=="worker" goto start_worker
if "%service%"=="beat" goto start_beat
if "%service%"=="flower" goto start_flower
if "%service%"=="all" goto start_all
call :print_error "Unknown service: %service%"
exit /b 1

:start_worker
set queue=%3
if "%queue%"=="" set queue=default
set concurrency=%4
if "%concurrency%"=="" set concurrency=4

call :print_status "Starting Celery worker for queue '%queue%'..."
start "Celery Worker %queue%" cmd /c "celery -A %CELERY_APP% worker --loglevel=info --concurrency=%concurrency% --queues=%queue% > %LOG_DIR%\celery_worker_%queue%.log 2>&1"
call :print_status "Celery worker for queue '%queue%' started"
goto :eof

:start_beat
call :print_status "Starting Celery beat..."
start "Celery Beat" cmd /c "celery -A %CELERY_APP% beat --loglevel=info > %LOG_DIR%\celery_beat.log 2>&1"
call :print_status "Celery beat started"
goto :eof

:start_flower
set port=%3
if "%port%"=="" set port=5555

call :print_status "Starting Celery flower on port %port%..."
start "Celery Flower" cmd /c "celery -A %CELERY_APP% flower --port=%port% > %LOG_DIR%\celery_flower.log 2>&1"
call :print_status "Celery flower started on http://localhost:%port%"
goto :eof

:start_all
call :start_worker default 4
call :start_worker alerts 2
call :start_worker reports 2
call :start_worker system 1
call :start_beat
call :start_flower
goto :eof

:stop
call :print_warning "Manual stop required on Windows. Please close the Celery windows or use Ctrl+C"
goto :eof

:restart
call :print_header "Restarting All Celery Services"
call :print_warning "Please manually close existing Celery windows, then press any key to start new ones..."
pause
call :start_all
goto :eof

:status
call :print_header "Celery Services Status"
call :print_status "Checking Celery cluster status..."
celery -A %CELERY_APP% inspect active 2>nul || call :print_warning "No active workers found"
goto :eof

:logs
set service=%2
if "%service%"=="" set service=worker_default
set logfile=%LOG_DIR%\celery_%service%.log

if exist "%logfile%" (
    type "%logfile%"
) else (
    call :print_error "Log file not found: %logfile%"
    call :print_status "Available log files:"
    dir /b "%LOG_DIR%\celery_*.log" 2>nul || call :print_warning "No log files found"
)
goto :eof

:purge
call :print_warning "This will purge ALL tasks from ALL queues!"
set /p confirm="Are you sure? (yes/no): "
if "%confirm%"=="yes" (
    call :print_status "Purging all queues..."
    celery -A %CELERY_APP% purge -f
    call :print_status "All queues purged"
) else (
    call :print_status "Purge cancelled"
)
goto :eof

:test
call :print_status "Testing Celery configuration..."
python manage.py celery_status --action=test
goto :eof

:help
call :print_header "Celery Manager - Sistema de Polinización y Germinación (Windows)"
echo Usage: %0 {start^|stop^|restart^|status^|logs^|purge^|test} [service] [options]
echo.
echo Commands:
echo   start [service]     Start Celery service(s)
echo     - worker [queue] [concurrency]  Start worker for specific queue
echo     - beat                          Start beat scheduler
echo     - flower [port]                 Start flower monitoring
echo     - all                           Start all services
echo.
echo   stop [service]      Stop Celery service(s) (manual on Windows)
echo   restart             Restart all services
echo   status              Show status of all services
echo   logs [service]      Show logs for service (default: worker_default)
echo   purge               Purge all queues (removes all pending tasks)
echo   test                Test Celery configuration
echo.
echo Examples:
echo   %0 start worker alerts 2    # Start alerts worker with 2 processes
echo   %0 logs beat                 # Show beat logs
echo   %0 status                    # Show all services status
echo.
echo Note: On Windows, services run in separate command windows.
echo       Use Ctrl+C in each window to stop services manually.
goto :eof