@echo off
title ytkit
echo ============================== >> "%~dp0..\data\logs\ytkit-bat.log"
echo Start: %date% %time% >> "%~dp0..\data\logs\ytkit-bat.log"

set URL=%~1
set FORMAT=%~2

if not "%URL%"=="" goto :gotinput

echo.
echo #######################
echo        ytkit
echo #######################
echo.
echo   Download audio, video or transcript from a YouTube URL.
echo.
set "URL=x"
set /p "URL=  URL: "

echo.
echo   1. Audio (default)
echo   2. Video
echo   3. Transcript
echo.
set "CHOICE=x"
set /p "CHOICE=  Choose [1/2/3]: "

if "%CHOICE%"=="2" set FORMAT=video
if "%CHOICE%"=="3" set FORMAT=transcript

:gotinput
if /i "%FORMAT%"=="v" set FORMAT=video
if /i "%FORMAT%"=="video" set FORMAT=video
if /i "%FORMAT%"=="t" set FORMAT=transcript
if /i "%FORMAT%"=="transcript" set FORMAT=transcript
if "%FORMAT%"=="" set FORMAT=audio
if /i not "%FORMAT%"=="audio" if /i not "%FORMAT%"=="video" if /i not "%FORMAT%"=="transcript" set FORMAT=audio

echo.
echo   Starting %FORMAT% download - this can take a few seconds to connect...
echo.

python "%~dp0..\src\ytkit.py" --url "%URL%" --format %FORMAT%

echo Exit code: %errorlevel% >> "%~dp0..\data\logs\ytkit-bat.log"
echo End: %date% %time% >> "%~dp0..\data\logs\ytkit-bat.log"

echo.
echo   Done. Log: data\logs\ytkit-bat.log
echo.
cmd /k
