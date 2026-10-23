@echo off
title ytkit
set "LOG=%~dp0..\data\logs\ytkit-bat.log"
echo ============================== >> "%LOG%"
echo Start: %date% %time% >> "%LOG%"

set "URL=%~1"
set "FORMAT=%~2"

if not "%URL%"=="" goto :run

echo.
echo #######################
echo        ytkit
echo #######################
echo.
echo   Download from a YouTube or Instagram reel URL.
echo.
set "URL=x"
set /p "URL=  URL: "
echo.
echo   1. Audio (default; video for Instagram)  2. Video  3. Transcript  4. Info  5. Frames
set "FORMAT="
set /p "FORMAT=  Choose [1-5]: "

:run
echo.
echo   Starting - this can take a few seconds to connect...
echo.
python "%~dp0..\src\ytkit.py" --url "%URL%" --format "%FORMAT%"

echo Exit code: %errorlevel% >> "%LOG%"
echo End: %date% %time% >> "%LOG%"
echo.
echo   Done. Run details: data\logs\ytkit.log
echo.
cmd /k
