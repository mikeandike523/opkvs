@echo off
setlocal enabledelayedexpansion

:: Get the directory of the batch file
set SCRIPT_DIR=%~dp0

:: Make sure the PowerShell script exists
if not exist "%SCRIPT_DIR%install.ps1" (
    echo PowerShell script install.ps1 not found in the same directory as this batch file.
    exit /b
)

:: Run PowerShell with the necessary execution policy bypass and pass all arguments
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install.ps1" %*

endlocal
