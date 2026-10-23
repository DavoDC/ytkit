@echo off
title ytkit
echo ============================== >> "%~dp0..\data\logs\ytkit-bat.log"
echo Start: %date% %time% >> "%~dp0..\data\logs\ytkit-bat.log"

set "URL=%~1"
set "FORMAT=%~2"

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
echo   4. Info (caption, stats, comments)
echo   5. Frames
echo.
set "CHOICE=x"
set /p "CHOICE=  Choose [1-5]: "

if "%CHOICE%"=="2" set FORMAT=video
if "%CHOICE%"=="3" set FORMAT=transcript
if "%CHOICE%"=="4" set FORMAT=info
if "%CHOICE%"=="5" set FORMAT=frames

:gotinput
if /i "%FORMAT%"=="v" set FORMAT=video
if /i "%FORMAT%"=="t" set FORMAT=transcript
if /i "%FORMAT%"=="i" set FORMAT=info
if /i "%FORMAT%"=="f" set FORMAT=frames

rem Instagram reel: ytkit.py cuts the URL down to /reel/ID; here just default to video (reels have no subtitles)
echo "%URL%"| findstr /i "instagram.com" >nul
if errorlevel 1 goto :fmtdone
if "%FORMAT%"=="" set FORMAT=video
if /i "%FORMAT%"=="audio" set FORMAT=video
if /i "%FORMAT%"=="transcript" echo   Instagram reels have no subtitles - downloading video instead.
if /i "%FORMAT%"=="transcript" set FORMAT=video
:fmtdone

if "%FORMAT%"=="" set FORMAT=audio
if /i not "%FORMAT%"=="audio" if /i not "%FORMAT%"=="video" if /i not "%FORMAT%"=="transcript" if /i not "%FORMAT%"=="info" if /i not "%FORMAT%"=="frames" set FORMAT=audio

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
