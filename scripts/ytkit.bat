@echo off
title ytkit
set "LOG=%~dp0..\data\logs\ytkit-bat.log"
echo ============================== >> "%LOG%"
echo Start: %date% %time% >> "%LOG%"

powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0ytkit-menu.ps1" -Url "%~1" -Format "%~2"

echo Exit code: %errorlevel% >> "%LOG%"
echo End: %date% %time% >> "%LOG%"
echo.
echo   Done. Run details: data\logs\ytkit.log
echo.
cmd /k
