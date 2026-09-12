@echo off
title ytkit
echo ============================== >> "%~dp0..\data\logs\ytkit-bat.log"
echo Start: %date% %time% >> "%~dp0..\data\logs\ytkit-bat.log"

set URL=%~1
set FORMAT=%~2

if "%URL%"=="" (
    echo.
    echo  ytkit - download audio, video or transcript from a YouTube URL.
    echo.
    set /p URL=Paste YouTube URL:
)

if "%FORMAT%"=="" (
    echo.
    echo  Format? [a]udio  [v]ideo  [t]ranscript   (default: audio)
    set /p FORMAT=Choice:
)

if /i "%FORMAT%"=="v" set FORMAT=video
if /i "%FORMAT%"=="video" set FORMAT=video
if /i "%FORMAT%"=="t" set FORMAT=transcript
if /i "%FORMAT%"=="transcript" set FORMAT=transcript
if /i "%FORMAT%"=="a" set FORMAT=audio
if "%FORMAT%"=="" set FORMAT=audio
if /i not "%FORMAT%"=="audio" if /i not "%FORMAT%"=="video" if /i not "%FORMAT%"=="transcript" set FORMAT=audio

echo.
echo  Downloading (%FORMAT%): %URL%
echo.

python "%~dp0..\src\ytkit.py" --url "%URL%" --format %FORMAT%

echo Exit code: %errorlevel% >> "%~dp0..\data\logs\ytkit-bat.log"
echo End: %date% %time% >> "%~dp0..\data\logs\ytkit-bat.log"

echo.
echo  Done. Log: data\logs\ytkit-bat.log
echo.
cmd /k
