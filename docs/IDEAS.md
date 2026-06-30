# ytkit - Ideas

## UI / Future

### Lightweight download UI (PRIORITY: medium)

Build a lightweight GUI on top of yt-dlp to replace the old Java YTD.

Options explored:
- **Python + tkinter** - zero extra deps, works offline, desktop app feel
- **Python + PyQt/PySide** - more polished, heavier
- **Python webapp (Flask/FastAPI + browser UI)** - accessible from any device on LAN, no install, easiest to extend

Leaning toward webapp UI: paste URL, pick format, click download, progress shown in browser. Simple. No Electron bloat. Could run as a local server launched from a .bat.

Notes:
- Check if something equivalent already exists (open-source yt-dlp web UIs exist - yt-dlp-web, metube, etc.) before building from scratch
- If building: Python backend wrapping yt-dlp subprocess, minimal HTML frontend
- Must use ffkit for ffmpeg (same binary, no duplication)
- The "ytkit" name allows for this evolution without rename

### Playlist / batch download support
- Accept a playlist URL, download all tracks as MP3
- Optional: filter by date range or title pattern

### Download history log
- Persist a JSON log of every download (URL, title, format, timestamp)
- Enables "have I already got this?" checks
